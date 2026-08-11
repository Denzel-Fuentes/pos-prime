# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Ticket layout driven by a Print Format instead of Python.

When a Restaurant Printer points at a Print Format with Raw Printing on,
printing.py renders that format's Raw Commands (Jinja) and sends the result
through EscposBuilder.raw() instead of running the built-in layout. Delivery,
status bookkeeping and the "never block a sale" guarantee are unchanged — only
the bytes in the middle come from somewhere else.

The template owns the ticket's *content*. The printer still owns the frame:
EscposBuilder emits the init + codepage prologue before the template's output
(without it, accents come out as garbage on the first ticket after power-on)
and the feed/cut/drawer epilogue after it, so `cut_paper`, `cash_drawer_pulse`
and `copies` keep working the same for templated and built-in tickets alike.

Templates get control-code constants and a couple of layout helpers rather
than raw escapes, so a readable line is `{{ row('1x Sopa', 'BOB 5.00') }}`
and not a wall of \\x1b. Hand-typed escapes still work — see EscposBuilder.raw.
"""

import frappe

from pos_prime.restaurant.ticket_options import shows

ESC = "\x1b"
GS = "\x1d"


def _helpers(chars_per_line, currency=None):
	def row(left, right=""):
		"""One line with `left` flush left and `right` flush right. When they
		don't fit together, `right` drops to its own right-aligned line rather
		than being truncated — a price must never be cut off."""
		left, right = str(left), str(right)
		gap = chars_per_line - len(left) - len(right)
		if gap < 1:
			return f"{left}\n{right.rjust(chars_per_line)}"
		return left + " " * gap + right

	def money(value):
		return frappe.utils.fmt_money(value or 0, currency=currency)

	def qty(value):
		value = value or 1
		return str(int(value)) if float(value).is_integer() else f"{value:g}"

	return {
		"LEFT": ESC + "a\x00",
		"CENTER": ESC + "a\x01",
		"RIGHT": ESC + "a\x02",
		"BOLD": ESC + "E\x01",
		"NOBOLD": ESC + "E\x00",
		"BIG": GS + "!\x11",
		"NOBIG": GS + "!\x00",
		"chars_per_line": chars_per_line,
		"sep": lambda char="-": char * chars_per_line,
		"row": row,
		"money": money,
		"qty": qty,
	}


def comanda_context(order, printer, destinations, settings):
	"""Kitchen ticket context. `blocks` is the same destination → combos →
	loose items grouping the built-in layout walks, precomputed so a template
	never has to re-derive combo instances from flat item rows."""
	combos_by_uid = {c.combo_uid: c for c in order.combos}
	dest_labels = {
		"Mesa": settings.label_dine_in or "MESA",
		"Para llevar": settings.label_takeaway or "PARA LLEVAR",
	}

	blocks = []
	for destination in destinations:
		dest_items = [i for i in order.items if i.destination == destination]
		if not dest_items:
			continue

		combos = []
		seen = set()
		for item in dest_items:
			if not item.combo_uid or item.combo_uid in seen:
				continue
			seen.add(item.combo_uid)
			combo_row = combos_by_uid.get(item.combo_uid)
			combos.append(
				{
					"uid": item.combo_uid,
					"label": (
						f"{combo_row.combo_name or combo_row.combo} #{combo_row.instance_no}"
						if combo_row
						else item.combo_uid
					),
					"notes": combo_row.notes if combo_row else None,
					"components": [i for i in dest_items if i.combo_uid == item.combo_uid],
				}
			)

		blocks.append(
			{
				"destination": destination,
				"label": dest_labels.get(destination, destination),
				"combos": combos,
				# Not "items": Jinja resolves attribute access on a dict to
				# its methods first, so `block.items` would hand the template
				# dict.items instead of these rows.
				"loose_items": [i for i in dest_items if not i.combo_uid],
			}
		)

	context = {
		"doc": order,
		"order": order,
		"printer": printer,
		"settings": settings,
		"blocks": blocks,
		"now": frappe.utils.now_datetime().strftime("%d/%m/%Y %H:%M"),
		"customer_name": (
			frappe.get_cached_value("Customer", order.customer, "customer_name") or order.customer
			if order.customer
			else None
		),
		"shows": lambda fieldname: shows(settings, fieldname),
	}
	context.update(_helpers(printer.chars_per_line or 32, order.currency))
	return context


def _combo_display_name(item):
	"""What a combo should be called on a customer-facing receipt: the
	Restaurant Combo's print label, falling back to the per-line label the
	sale stored ("COMPLETO #1 · Sopa" → "COMPLETO #1") if the combo record
	is gone."""
	if item.get("pos_prime_combo"):
		combo = frappe.get_cached_value(
			"Restaurant Combo", item.pos_prime_combo, ["print_label", "combo_name"], as_dict=True
		)
		if combo:
			return combo.print_label or combo.combo_name
	label = item.get("pos_prime_combo_label") or ""
	return label.split(" · ")[0] or item.item_name


def _receipt_lines(invoice):
	"""Invoice rows collapsed for the customer: every component of one combo
	instance becomes a single line carrying the combo's name, its quantity
	and the sum of the split amounts — the split (see pricing.py) is an
	accounting detail, not something a customer asked for. Loose items pass
	through untouched, and invoice order is preserved: a combo lands where
	its first component was.

	Every entry has the same keys, so a template can print `lines` without
	branching; `is_combo` and `components` are there for when it wants to.
	"""
	lines = []
	seen = set()
	for item in invoice.items:
		uid = item.get("pos_prime_combo_uid")
		if not uid:
			lines.append(
				{
					"is_combo": False,
					"label": item.item_name,
					"qty": item.qty,
					"amount": item.amount,
					"item": item,
					"components": [],
					"notes": None,
				}
			)
			continue

		if uid in seen:
			continue
		seen.add(uid)

		components = [i for i in invoice.items if i.get("pos_prime_combo_uid") == uid]
		lines.append(
			{
				"is_combo": True,
				"label": _combo_display_name(item),
				# Every component of an instance carries the instance's own
				# quantity, so this is the combo's qty — not a sum.
				"qty": components[0].qty,
				"amount": sum(c.amount or 0 for c in components),
				"item": item,
				"components": components,
				"notes": item.get("pos_prime_combo_notes"),
			}
		)
	return lines


def receipt_context(invoice, printer, settings):
	context = {
		"doc": invoice,
		"invoice": invoice,
		"lines": _receipt_lines(invoice),
		"printer": printer,
		"settings": settings,
		"posting_datetime": frappe.utils.get_datetime(
			f"{invoice.posting_date} {invoice.posting_time}"
		).strftime("%d/%m/%Y %H:%M"),
		"shows": lambda fieldname: shows(settings, fieldname),
	}
	context.update(_helpers(printer.chars_per_line or 32, invoice.currency))
	return context


def render(print_format, context):
	"""Jinja-render one Print Format's Raw Commands. Raises rather than
	falling back to the built-in layout: a template that silently stopped
	being used would be far harder to notice than a Failed ticket, and the
	sale is already committed by the time any of this runs."""
	raw_commands = frappe.db.get_value("Print Format", print_format, "raw_commands")
	if not raw_commands or not raw_commands.strip():
		frappe.throw(f'Print Format "{print_format}" has no Raw Commands to print.')
	return frappe.render_template(raw_commands, context)
