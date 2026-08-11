# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Till receipt (customer-facing) ticket layout.

Parallel to pos_prime/restaurant/printing.py's kitchen-ticket layout, but
built from a POS Invoice instead of a Restaurant Order — unlike the
comanda, the receipt has prices, so it reads straight from the invoice
that's the source of truth for what the customer was actually charged.
Uses the same EscposBuilder primitives as the comanda (see escpos.py) so
there's only one place that knows how to encode ESC/POS bytes.
"""

import frappe

from pos_prime.restaurant.ticket_options import shows


def _fmt_qty(qty):
	qty = qty or 1
	return str(int(qty)) if float(qty).is_integer() else f"{qty:g}"


def build_receipt_bytes(invoice, printer, settings):
	from pos_prime.restaurant.escpos import EscposBuilder
	from pos_prime.restaurant.printing import build_from_template
	from pos_prime.restaurant.ticket_template import receipt_context

	if printer.print_format:
		return build_from_template(printer, receipt_context(invoice, printer, settings))

	b = EscposBuilder(printer.codepage, printer.escpos_codepage_id, printer.chars_per_line or 32)
	fmt = frappe.utils.fmt_money

	b.align("center")
	b.header(invoice.company or "")
	if shows(settings, "receipt_show_invoice_info"):
		b.text(invoice.name)
		b.text(
			frappe.utils.get_datetime(f"{invoice.posting_date} {invoice.posting_time}").strftime(
				"%d/%m/%Y %H:%M"
			)
		)
	b.align("left")
	b.divider()

	# The divider rides along with the line it separates, so turning the
	# customer off doesn't leave two rules stacked on top of each other.
	if (
		shows(settings, "receipt_show_customer")
		and invoice.customer_name
		and invoice.customer_name != "Cliente Casual"
	):
		b.text(f"Cliente: {invoice.customer_name}")
		b.divider()

	for item in invoice.items:
		b.text(f"{_fmt_qty(item.qty)}x {item.item_name}")
		b.align("right")
		b.text(fmt(item.amount, currency=invoice.currency))
		b.align("left")

	b.divider()

	if invoice.get("discount_amount"):
		b.text(f"Descuento: -{fmt(invoice.discount_amount, currency=invoice.currency)}")

	if shows(settings, "receipt_show_taxes"):
		for tax in invoice.get("taxes") or []:
			b.text(f"{tax.description}: {fmt(tax.tax_amount, currency=invoice.currency)}")

	b.align("right")
	b.header(f"TOTAL {fmt(invoice.grand_total, currency=invoice.currency)}")
	b.align("left")
	b.divider()

	if shows(settings, "receipt_show_payments"):
		for payment in invoice.get("payments") or []:
			if payment.amount:
				b.text(f"{payment.mode_of_payment}: {fmt(payment.amount, currency=invoice.currency)}")
		if invoice.get("change_amount"):
			b.text(f"Vuelto: {fmt(invoice.change_amount, currency=invoice.currency)}")

	b.feed(1)
	b.align("center")
	b.text(settings.get("receipt_footer") or "Gracias por su compra")
	b.feed(3)

	if printer.cut_paper:
		b.cut()
	if printer.cash_drawer_pulse:
		b.pulse_drawer()
	return b.build()
