# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from pos_prime.restaurant.pricing import ABSORPTION, MIXED, PROPORTIONAL


class RestaurantCombo(Document):
	def validate(self):
		if not self.slots:
			frappe.throw(_("Add at least one component slot (e.g. Sopa, Segundo, Refresco)."))
		self.validate_discount_orders()

	def effective_pricing_method(self):
		"""Blank on the combo means "use the site default" — resolved here so
		validation and pricing agree on what this combo actually does."""
		return (
			self.pricing_method
			or frappe.db.get_single_value("Restaurant Settings", "default_combo_pricing_method")
			or PROPORTIONAL
		)

	def validate_discount_orders(self):
		"""Catch a combo that can't price itself at save time. Doing it here
		rather than at checkout matters: the split runs while a customer is
		waiting to pay, where the only thing a cashier can do about a bad
		configuration is give up on the sale."""
		orders = [slot.discount_order or 0 for slot in self.slots]

		absorbing = [order for order in orders if order >= 1]
		if len(absorbing) != len(set(absorbing)):
			frappe.throw(
				_("Two slots share the same Discount Order, so the order they absorb the discount in would be ambiguous.")
			)

		method = self.effective_pricing_method()
		if method in (ABSORPTION, MIXED) and not absorbing:
			frappe.throw(
				_('Pricing method "{0}" needs at least one slot with a Discount Order of 1 or more to absorb the discount.').format(
					method
				)
			)
