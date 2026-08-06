# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Kitchen ticket transport + orchestration.

pos_prime/restaurant/escpos.py builds ticket bytes; this module decides
which Restaurant Printer(s) a Restaurant Order should go to, lays out the
actual ticket (grouped by destination, then combo instance, then loose
items — no prices, the kitchen doesn't need them), sends it over a plain
TCP socket (ESC/POS network printers listen on port 9100 and never reply,
so this only ever writes), and durably records the outcome on the order.

A printer failure must never revert or block a sale — see the
enqueue_after_commit=True call site in pos_prime/api/restaurant.py and the
docstring on print_comanda() below for how that invariant is kept even when
this is invoked inline (dev benches with no RQ worker).
"""

import socket

import frappe

from pos_prime.restaurant.escpos import EscposBuilder


def _get_printers_for_order(order):
	names = frappe.get_all(
		"Restaurant Printer",
		filters={"disabled": 0, "pos_profile": ["in", ["", order.pos_profile]]},
		pluck="name",
	)
	return [frappe.get_doc("Restaurant Printer", name) for name in names]


def _destinations_for_printer(printer, order):
	present = []
	if order.has_dine_in:
		present.append("Mesa")
	if order.has_takeaway:
		present.append("Para llevar")

	if printer.print_destinations == "Mesa Only":
		return [d for d in present if d == "Mesa"]
	if printer.print_destinations == "Para llevar Only":
		return [d for d in present if d == "Para llevar"]
	return present


def _fmt_qty(qty):
	qty = qty or 1
	return str(int(qty)) if float(qty).is_integer() else f"{qty:g}"


def _write_loose_item(b, item):
	b.bold(f"{_fmt_qty(item.qty)}x {item.item_name}")
	if item.notes:
		b.text(f"  * {item.notes}")
	if item.modifiers_summary:
		b.text(f"  + {item.modifiers_summary}")


def _write_combo_component(b, item):
	label = item.combo_slot_label or item.item_name
	b.text(f"  - {label}: {item.item_name}")
	if item.notes:
		b.text(f"    * {item.notes}")
	if item.modifiers_summary:
		b.text(f"    + {item.modifiers_summary}")


def _build_ticket_bytes(order, printer, destinations, settings):
	b = EscposBuilder(printer.codepage, printer.escpos_codepage_id, printer.chars_per_line or 32)

	b.align("center")
	b.bold(order.pos_invoice or order.name)
	b.text(frappe.utils.now_datetime().strftime("%d/%m/%Y %H:%M"))
	b.align("left")

	combos_by_uid = {c.combo_uid: c for c in order.combos}
	dest_labels = {
		"Mesa": settings.label_dine_in or "MESA",
		"Para llevar": settings.label_takeaway or "PARA LLEVAR",
	}

	for destination in destinations:
		dest_items = [i for i in order.items if i.destination == destination]
		if not dest_items:
			continue

		b.divider("=")
		b.align("center")
		b.header(dest_labels.get(destination, destination))
		b.align("left")

		printed_combo_uids = set()
		for item in dest_items:
			if not item.combo_uid or item.combo_uid in printed_combo_uids:
				continue
			printed_combo_uids.add(item.combo_uid)
			combo_row = combos_by_uid.get(item.combo_uid)
			combo_items = [i for i in dest_items if i.combo_uid == item.combo_uid]
			label = (
				f"{combo_row.combo_name or combo_row.combo} #{combo_row.instance_no}"
				if combo_row
				else item.combo_uid
			)
			b.bold(label)
			for component in combo_items:
				_write_combo_component(b, component)
			if combo_row and combo_row.notes:
				b.text(f"  * {combo_row.notes}")
			b.feed(1)

		for item in dest_items:
			if not item.combo_uid:
				_write_loose_item(b, item)

		b.feed(1)

	b.feed(3)
	if printer.cut_paper:
		b.cut()
	if printer.cash_drawer_pulse:
		b.pulse_drawer()
	return b.build()


def _send_bytes(printer, data):
	with socket.create_connection(
		(printer.host, printer.port or 9100), timeout=printer.timeout_seconds or 5
	) as sock:
		for _ in range(max(1, printer.copies or 1)):
			sock.sendall(data)


def print_comanda(restaurant_order):
	"""Print the kitchen ticket for one Restaurant Order to every matching
	Restaurant Printer, and durably record the outcome on the order via
	comanda_status / comanda_printed_at / comanda_error.

	Called two ways:
	  - Enqueued with enqueue_after_commit=True right after the sale (the
	    normal path) — runs fully decoupled from the request, so nothing
	    it does can affect the sale that already committed.
	  - Inline, for dev benches with no RQ worker, or from reprint_comanda.
	    The caller (pos_prime.api.restaurant.create_restaurant_sale) always
	    wraps the inline call in try/except regardless of fail_silently,
	    because "never block or revert a sale" must hold unconditionally —
	    not just when the admin has also asked for quiet failures.

	Re-raises once, at the very end, only when Restaurant Settings.
	fail_silently is off — purely so a background job shows as failed and
	an admin notices. By that point comanda_status/comanda_error are
	already saved, so callers that swallow the exception (reprint_comanda)
	lose nothing by doing so.
	"""
	order = frappe.get_doc("Restaurant Order", restaurant_order)
	settings = frappe.get_cached_doc("Restaurant Settings")
	printers = _get_printers_for_order(order)

	if not printers:
		order.db_set("comanda_status", "Not Required", update_modified=False)
		return

	errors = []
	sent_to_any = False
	for printer in printers:
		destinations = _destinations_for_printer(printer, order)
		if not destinations:
			continue
		try:
			data = _build_ticket_bytes(order, printer, destinations, settings)
			_send_bytes(printer, data)
			sent_to_any = True
		except Exception as e:
			errors.append(f"{printer.printer_name}: {e}")
			frappe.log_error(
				title=f"Comanda print failed: {printer.printer_name}",
				message=frappe.get_traceback(),
			)

	if not sent_to_any and not errors:
		# Every matching printer's print_destinations excluded every
		# destination actually present (e.g. a "Mesa Only" printer on a
		# takeaway-only order) — nothing was owed a ticket, not a failure.
		order.db_set("comanda_status", "Not Required", update_modified=False)
		return

	if errors:
		order.db_set("comanda_status", "Failed", update_modified=False)
		order.db_set("comanda_error", "\n".join(errors)[:4000], update_modified=False)
	else:
		order.db_set("comanda_status", "Printed", update_modified=False)
		order.db_set("comanda_printed_at", frappe.utils.now_datetime(), update_modified=False)

	if errors and not settings.fail_silently:
		raise frappe.ValidationError("; ".join(errors))


def send_test_ticket(printer_name):
	"""Synchronous, user-initiated printer test — errors are meant to
	surface immediately to whoever clicked "Test Printer", so unlike
	print_comanda() this does not catch or log anything itself."""
	printer = frappe.get_doc("Restaurant Printer", printer_name)

	b = EscposBuilder(printer.codepage, printer.escpos_codepage_id, printer.chars_per_line or 32)
	b.align("center")
	b.header("PRUEBA")
	b.align("left")
	b.text(f"Impresora: {printer.printer_name}")
	b.text(f"{printer.host}:{printer.port}")
	b.text(frappe.utils.now_datetime().strftime("%d/%m/%Y %H:%M:%S"))
	b.divider()
	b.text("Si puede leer esto, la conexion")
	b.text("con esta impresora funciona.")
	b.feed(3)
	if printer.cut_paper:
		b.cut()

	_send_bytes(printer, b.build())
