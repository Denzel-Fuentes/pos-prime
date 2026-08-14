# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from pos_prime.restaurant.pricing import ABSORPTION, MIXED, PROPORTIONAL

# Indexed by date.weekday() — Monday is 0, matching Python's convention.
WEEKDAY_FIELDS = (
	"available_monday",
	"available_tuesday",
	"available_wednesday",
	"available_thursday",
	"available_friday",
	"available_saturday",
	"available_sunday",
)


class RestaurantCombo(Document):
	def validate(self):
		if not self.slots:
			frappe.throw(_("Add at least one component slot (e.g. Sopa, Segundo, Refresco)."))
		self.validate_slot_sources()
		self.validate_discount_orders()

	def is_available_on(self, weekday):
		"""Whether this combo is offered on the given date.weekday().

		No day ticked means "every day" — that's what every combo saved
		before this field existed looks like, so the weekend/weekday split
		is opt-in and nothing silently disappears from the grid."""
		flags = [int(self.get(field) or 0) for field in WEEKDAY_FIELDS]
		if not any(flags):
			return True
		return bool(flags[weekday])

	def items_for_slot(self, slot):
		"""Item codes listed individually for one slot under slot_items.

		The rows hang off the combo rather than the slot because Frappe
		doesn't persist a child table nested inside a grid row, so they're
		matched back by slot_label (which validate_slot_sources keeps
		pointing at a real slot)."""
		return [row.item for row in (self.slot_items or []) if row.slot_label == slot.slot_label]

	def validate_slot_sources(self):
		"""A slot draws from an Item Group, from individually named items, or
		both — but one with neither can never be filled, and would only
		surface as an empty picker at the till."""
		labels = {slot.slot_label for slot in self.slots}
		for row in self.slot_items or []:
			if row.slot_label not in labels:
				frappe.throw(
					_('Individual item {0} points at slot "{1}", which this combo does not have.').format(
						row.item, row.slot_label
					)
				)

		for slot in self.slots:
			if not slot.item_group and not self.items_for_slot(slot):
				frappe.throw(
					_('Slot "{0}" needs either an Item Group or at least one individual Item.').format(
						slot.slot_label or slot.idx
					)
				)

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
