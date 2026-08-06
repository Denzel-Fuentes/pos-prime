# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Custom fields for the restaurant module.

POS Prime's drafts are real POS Invoice documents with docstatus=0
(see pos_prime/api/drafts.py), and the Restaurant Order for a sale doesn't
exist until payment. So per-line destination/notes/combo linkage has to
survive on the POS Invoice Item itself, or holding an order with a combo
and resuming it would silently lose that data. This is the app's one
deliberate, scoped exception to "zero custom fields" — see CLAUDE.md.

All fields are prefixed pos_prime_ and no_copy so they never leak into
an unrelated document via "Duplicate".
"""

RESTAURANT_CUSTOM_FIELDS = {
	"POS Invoice Item": [
		{
			"fieldname": "pos_prime_line_uid",
			"fieldtype": "Data",
			"label": "Line UID",
			"insert_after": "project",
			"hidden": 1,
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_destination",
			"fieldtype": "Select",
			"label": "Destination",
			"options": "\nMesa\nPara llevar",
			"insert_after": "pos_prime_line_uid",
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_notes",
			"fieldtype": "Small Text",
			"label": "Kitchen Note",
			"insert_after": "pos_prime_destination",
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_combo_uid",
			"fieldtype": "Data",
			"label": "Combo UID",
			"insert_after": "pos_prime_notes",
			"hidden": 1,
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_combo",
			"fieldtype": "Link",
			"options": "Restaurant Combo",
			"label": "Combo",
			"insert_after": "pos_prime_combo_uid",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_combo_label",
			"fieldtype": "Data",
			"label": "Combo Instance",
			"insert_after": "pos_prime_combo",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "pos_prime_modifiers",
			"fieldtype": "Small Text",
			"label": "Modifiers",
			"insert_after": "pos_prime_combo_label",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
		},
	],
	"POS Invoice": [
		{
			"fieldname": "pos_prime_restaurant_order",
			"fieldtype": "Link",
			"options": "Restaurant Order",
			"label": "Restaurant Order",
			"insert_after": "against_income_account",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
			"allow_on_submit": 1,
		},
	],
}


def create_restaurant_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(RESTAURANT_CUSTOM_FIELDS, ignore_validate=True)
