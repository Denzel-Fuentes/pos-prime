# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Seeds the two editable ticket Print Formats.

These are created as ordinary (non-standard) Print Format records, not as
files under the app's module folder, precisely so they stay editable from the
Desk — a standard print format is read-only outside developer mode, which
would defeat the point of moving the layout out of Python.

Seeding is create-if-missing and never overwrites: once an admin has edited a
ticket, a later migrate must not silently revert it. Delete the record and
re-run to get the shipped layout back.

The templates below reproduce the built-in layouts (pos_prime/restaurant/
printing.py and receipt_ticket.py), including the same Restaurant Settings
checks via shows(), so pointing a printer at one changes nothing until it's
edited. See ticket_template.py for the context and helpers available.
"""

import frappe

COMANDA_FORMAT = "POS Prime Comanda (ESC/POS)"
RECEIPT_FORMAT = "POS Prime Recibo (ESC/POS)"

COMANDA_TEMPLATE = """\
{{ CENTER }}{% if shows('comanda_show_order_no') %}{{ BOLD }}{{ order.pos_invoice or order.name }}{{ NOBOLD }}
{% endif %}{% if shows('comanda_show_time') %}{{ now }}
{% endif %}{% if shows('comanda_show_customer') and customer_name %}{{ customer_name }}
{% endif %}{{ LEFT }}{% for block in blocks %}{{ sep('=') }}
{{ CENTER }}{{ BIG }}{{ BOLD }}{{ block.label }}{{ NOBOLD }}{{ NOBIG }}
{{ LEFT }}{% for combo in block.combos %}{{ BOLD }}{{ combo.label }}{{ NOBOLD }}
{% for component in combo.components %}  - {{ component.combo_slot_label or component.item_name }}: {{ component.item_name }}
{% if component.notes %}    * {{ component.notes }}
{% endif %}{% if shows('comanda_show_modifiers') and component.modifiers_summary %}    + {{ component.modifiers_summary }}
{% endif %}{% endfor %}{% if combo.notes %}  * {{ combo.notes }}
{% endif %}
{% endfor %}{% for item in block.loose_items %}{{ BOLD }}{{ qty(item.qty) }}x {{ item.item_name }}{{ NOBOLD }}
{% if item.notes %}  * {{ item.notes }}
{% endif %}{% if shows('comanda_show_modifiers') and item.modifiers_summary %}  + {{ item.modifiers_summary }}
{% endif %}{% endfor %}
{% endfor %}"""

RECEIPT_TEMPLATE = """\
{{ CENTER }}{{ BIG }}{{ BOLD }}{{ invoice.company }}{{ NOBOLD }}{{ NOBIG }}
{% if shows('receipt_show_invoice_info') %}{{ invoice.name }}
{{ posting_datetime }}
{% endif %}{{ LEFT }}{{ sep() }}
{% if shows('receipt_show_customer') and invoice.customer_name and invoice.customer_name != 'Cliente Casual' %}Cliente: {{ invoice.customer_name }}
{{ sep() }}
{% endif %}{#- `lines` collapses each combo into one row. Swap the loop for
   `invoice.items` to bill every component separately, or uncomment the inner
   loop below to keep the single price but still list what came in the combo. -#}
{% for line in lines %}{{ row(qty(line.qty) ~ 'x ' ~ line.label, money(line.amount)) }}
{% if line.is_combo %}{# {% for component in line.components %}   - {{ component.item_name }}
{% endfor %} #}{% endif %}{% endfor %}{{ sep() }}
{% if invoice.discount_amount %}{{ row('Descuento', '-' ~ money(invoice.discount_amount)) }}
{% endif %}{% if shows('receipt_show_taxes') %}{% for tax in invoice.taxes %}{{ row(tax.description, money(tax.tax_amount)) }}
{% endfor %}{% endif %}{{ RIGHT }}{{ BIG }}{{ BOLD }}TOTAL {{ money(invoice.grand_total) }}{{ NOBOLD }}{{ NOBIG }}
{{ LEFT }}{{ sep() }}
{% if shows('receipt_show_payments') %}{% for payment in invoice.payments %}{% if payment.amount %}{{ row(payment.mode_of_payment, money(payment.amount)) }}
{% endif %}{% endfor %}{% if invoice.change_amount %}{{ row('Vuelto', money(invoice.change_amount)) }}
{% endif %}{% endif %}
{{ CENTER }}{{ settings.receipt_footer or 'Gracias por su compra' }}"""

FORMATS = (
	(COMANDA_FORMAT, "Restaurant Order", COMANDA_TEMPLATE),
	(RECEIPT_FORMAT, "POS Invoice", RECEIPT_TEMPLATE),
)


def create_ticket_print_formats():
	created = []
	for name, doctype, template in FORMATS:
		if frappe.db.exists("Print Format", name):
			continue
		doc = frappe.new_doc("Print Format")
		doc.name = name
		doc.doc_type = doctype
		doc.module = "POS Prime"
		doc.standard = "No"
		doc.print_format_type = "Jinja"
		doc.raw_printing = 1
		doc.raw_commands = template
		doc.insert(ignore_permissions=True)
		created.append(name)
	return created
