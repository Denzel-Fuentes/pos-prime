# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Ticket transport + orchestration — kitchen comanda and till receipt.

pos_prime/restaurant/escpos.py builds the kitchen ticket bytes (grouped by
destination, then combo instance, then loose items — no prices, the
kitchen doesn't need them) and pos_prime/restaurant/receipt_ticket.py
builds the customer receipt bytes from the POS Invoice. This module picks
which Restaurant Printer(s) a job goes to and delivers the bytes one of
two ways (see _deliver):

  - TCP Directo: a plain socket straight from wherever Frappe runs to the
    printer's host:port (ESC/POS network printers listen on port 9100 and
    never reply, so this only ever writes). Only works when Frappe has
    direct network access to the printer — i.e. an on-prem bench on the
    same LAN.
  - Puente Android: for a cloud-hosted Frappe that can't reach a printer
    sitting behind the store's router/NAT. The ticket (ESC/POS bytes,
    base64) is published via frappe.publish_realtime to the Frappe User
    configured as the printer's bridge_user — Frappe's own realtime layer
    (Socket.IO, already served as wss://<site> over 443) already scopes
    delivery to that user's live sessions, so no bespoke pairing/token
    system is needed here. An Android app (built separately, outside this
    repo) logs in as that User, listens for the "pos_prime_print_job"
    event, and relays the decoded bytes over a local TCP connection to
    the host:port in the payload. This is fire-and-forget: there is no
    delivery ack from the phone, so "Printed" for a bridge job only means
    "handed off to realtime," not "confirmed printed on paper." If the
    bridge device is offline the job is lost, same as today's Failed
    kitchen tickets — the fix is the same manual reprint path.

A printer failure must never revert or block a sale — see the
enqueue_after_commit=True call sites in pos_prime/api/restaurant.py and the
docstring on print_comanda() below for how that invariant is kept even when
this is invoked inline (dev benches with no RQ worker).
"""

import base64
import socket

import frappe

from pos_prime.restaurant.escpos import EscposBuilder
from pos_prime.restaurant.ticket_options import shows
from pos_prime.restaurant.ticket_template import comanda_context, render


def _get_printers(pos_profile, role):
	names = frappe.get_all(
		"Restaurant Printer",
		filters={"disabled": 0, "pos_profile": ["in", ["", pos_profile]], "printer_role": role},
		pluck="name",
	)
	return [frappe.get_doc("Restaurant Printer", name) for name in names]


def _get_printers_for_order(order):
	return _get_printers(order.pos_profile, "Comanda (Cocina)")


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


def _write_loose_item(b, item, show_modifiers=True):
	b.bold(f"{_fmt_qty(item.qty)}x {item.item_name}")
	if item.notes:
		b.text(f"  * {item.notes}")
	if show_modifiers and item.modifiers_summary:
		b.text(f"  + {item.modifiers_summary}")


def _write_combo_component(b, item, show_modifiers=True):
	label = item.combo_slot_label or item.item_name
	b.text(f"  - {label}: {item.item_name}")
	if item.notes:
		b.text(f"    * {item.notes}")
	if show_modifiers and item.modifiers_summary:
		b.text(f"    + {item.modifiers_summary}")


def build_from_template(printer, context):
	"""Wrap a Print Format's rendered output in the printer's own frame —
	init/codepage prologue, feed/cut/drawer epilogue. See
	pos_prime/restaurant/ticket_template.py for who owns what."""
	b = EscposBuilder(printer.codepage, printer.escpos_codepage_id, printer.chars_per_line or 32)
	b.raw(render(printer.print_format, context))
	b.feed(3)
	if printer.cut_paper:
		b.cut()
	if printer.cash_drawer_pulse:
		b.pulse_drawer()
	return b.build()


def _build_ticket_bytes(order, printer, destinations, settings):
	if printer.print_format:
		return build_from_template(
			printer, comanda_context(order, printer, destinations, settings)
		)

	b = EscposBuilder(printer.codepage, printer.escpos_codepage_id, printer.chars_per_line or 32)

	show_modifiers = shows(settings, "comanda_show_modifiers")

	b.align("center")
	if shows(settings, "comanda_show_order_no"):
		b.bold(order.pos_invoice or order.name)
	if shows(settings, "comanda_show_time"):
		b.text(frappe.utils.now_datetime().strftime("%d/%m/%Y %H:%M"))
	if shows(settings, "comanda_show_customer") and order.customer:
		b.text(frappe.get_cached_value("Customer", order.customer, "customer_name") or order.customer)
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
				_write_combo_component(b, component, show_modifiers)
			if combo_row and combo_row.notes:
				b.text(f"  * {combo_row.notes}")
			b.feed(1)

		for item in dest_items:
			if not item.combo_uid:
				_write_loose_item(b, item, show_modifiers)

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


def _send_via_bridge(printer, data, job_type, reference):
	if not printer.bridge_user:
		frappe.throw(
			f'Restaurant Printer "{printer.printer_name}" is set to Puente Android but has no Bridge User configured.'
		)
	frappe.publish_realtime(
		event="pos_prime_print_job",
		message={
			"printer": printer.name,
			"host": printer.host,
			"port": printer.port or 9100,
			"copies": max(1, printer.copies or 1),
			"data_base64": base64.b64encode(data).decode(),
			"job_type": job_type,
			"reference": reference,
		},
		user=printer.bridge_user,
		after_commit=True,
	)


def _deliver(printer, data, job_type, reference):
	"""Dispatch one ticket's bytes to a Restaurant Printer per its
	delivery_mode. See the module docstring for what each mode does and
	the tradeoffs of Puente Android (fire-and-forget, no delivery ack)."""
	if printer.delivery_mode == "Puente Android":
		_send_via_bridge(printer, data, job_type, reference)
	else:
		_send_bytes(printer, data)


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
			_deliver(printer, data, job_type="comanda", reference=order.name)
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


def print_receipt(pos_invoice):
	"""Print the till receipt for one POS Invoice to every matching
	Restaurant Printer (printer_role="Recibo (Caja)"), and durably record
	the outcome via pos_prime_receipt_status / _printed_at / _error.

	Same calling conventions and same "never block or revert a sale"
	guarantee as print_comanda() above — see its docstring.
	"""
	from pos_prime.restaurant.receipt_ticket import build_receipt_bytes

	invoice = frappe.get_doc("POS Invoice", pos_invoice)
	settings = frappe.get_cached_doc("Restaurant Settings")
	printers = _get_printers(invoice.pos_profile, "Recibo (Caja)")

	if not printers:
		invoice.db_set("pos_prime_receipt_status", "Not Required", update_modified=False)
		return

	errors = []
	sent_to_any = False
	for printer in printers:
		try:
			data = build_receipt_bytes(invoice, printer, settings)
			_deliver(printer, data, job_type="receipt", reference=invoice.name)
			sent_to_any = True
		except Exception as e:
			errors.append(f"{printer.printer_name}: {e}")
			frappe.log_error(
				title=f"Receipt print failed: {printer.printer_name}",
				message=frappe.get_traceback(),
			)

	if not sent_to_any and not errors:
		invoice.db_set("pos_prime_receipt_status", "Not Required", update_modified=False)
		return

	if errors:
		invoice.db_set("pos_prime_receipt_status", "Failed", update_modified=False)
		invoice.db_set("pos_prime_receipt_error", "\n".join(errors)[:4000], update_modified=False)
	else:
		invoice.db_set("pos_prime_receipt_status", "Printed", update_modified=False)
		invoice.db_set("pos_prime_receipt_printed_at", frappe.utils.now_datetime(), update_modified=False)

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

	_deliver(printer, b.build(), job_type="test", reference=printer.name)
