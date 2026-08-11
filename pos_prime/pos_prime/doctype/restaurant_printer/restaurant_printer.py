# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe.model.document import Document

# Which doctype a role's ticket is built from — the kitchen ticket reads the
# Restaurant Order (no prices), the till receipt reads the POS Invoice that
# is the source of truth for what was charged.
DOCTYPE_FOR_ROLE = {
	"Comanda (Cocina)": "Restaurant Order",
	"Recibo (Caja)": "POS Invoice",
}


class RestaurantPrinter(Document):
	def validate(self):
		self.validate_print_format()

	def validate_print_format(self):
		"""Catch a mis-wired Print Format here rather than at print time: a
		ticket is built after the sale has already committed, where the only
		way to report the problem is a Failed status nobody is watching."""
		if not self.print_format:
			return

		fmt = frappe.db.get_value(
			"Print Format", self.print_format, ["raw_printing", "doc_type"], as_dict=True
		)
		if not fmt.raw_printing:
			frappe.throw(
				f'Print Format "{self.print_format}" does not have Raw Printing enabled, '
				"so it renders HTML rather than the ESC/POS commands a ticket printer needs."
			)

		expected = DOCTYPE_FOR_ROLE.get(self.printer_role)
		if expected and fmt.doc_type != expected:
			frappe.throw(
				f'Print Format "{self.print_format}" is for {fmt.doc_type}, but a '
				f"{self.printer_role} printer prints from {expected}."
			)
