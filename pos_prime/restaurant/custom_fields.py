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
			"fieldname": "pos_prime_combo_slot_idx",
			"fieldtype": "Int",
			"label": "Combo Slot Index",
			"insert_after": "pos_prime_combo",
			"hidden": 1,
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
		{
			# Instance-wide combo note ("todo para llevar en cajas separadas"),
			# replicated onto every component line by the frontend
			# (cartStore.updateComboNotes) so it survives hold/resume
			# regardless of which line the server reads it from. Distinct
			# from pos_prime_notes, which is per component.
			"fieldname": "pos_prime_combo_notes",
			"fieldtype": "Small Text",
			"label": "Combo Note",
			"insert_after": "pos_prime_modifiers",
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
		{
			# Till receipt print status — parallel to Restaurant Order's
			# comanda_status, but lives on POS Invoice since a receipt is
			# tied to the invoice itself, not to a Restaurant Order (which
			# doesn't exist for non-restaurant sales). Written via db_set
			# after submit, same as comanda_status; allow_on_submit is set
			# anyway so a plain .save() from Desk wouldn't be blocked either.
			"fieldname": "pos_prime_receipt_status",
			"fieldtype": "Select",
			"label": "Receipt Print Status",
			"options": "Not Printed\nPrinted\nFailed\nNot Required",
			"insert_after": "pos_prime_restaurant_order",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
			"allow_on_submit": 1,
		},
		{
			"fieldname": "pos_prime_receipt_printed_at",
			"fieldtype": "Datetime",
			"label": "Receipt Printed At",
			"insert_after": "pos_prime_receipt_status",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
			"allow_on_submit": 1,
		},
		{
			"fieldname": "pos_prime_receipt_error",
			"fieldtype": "Small Text",
			"label": "Receipt Print Error",
			"insert_after": "pos_prime_receipt_printed_at",
			"read_only": 1,
			"print_hide": 1,
			"no_copy": 1,
			"allow_on_submit": 1,
		},
	],
	"POS Opening Entry": [
		{
			# The dishes explicitly enabled for sale today, for Item Groups
			# configured under Restaurant Settings' "Daily Menu" section. Rides
			# along on the shift's own opening entry — there's no other
			# document whose lifecycle matches "for the duration of this
			# shift" the way this one does (same reasoning as the POS Invoice
			# Item fields above, just for a different document).
			"fieldname": "pos_prime_available_items",
			"fieldtype": "Table MultiSelect",
			"options": "Restaurant Opening Entry Item",
			"label": "Available Dishes Today",
			"insert_after": "balance_details",
			"no_copy": 1,
		},
	],
}


def create_restaurant_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(RESTAURANT_CUSTOM_FIELDS, ignore_validate=True)
