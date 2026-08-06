# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RestaurantOrder(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Restaurant Order must have at least one item."))
		self.has_dine_in = 1 if any(i.destination == "Mesa" for i in self.items) else 0
		self.has_takeaway = 1 if any(i.destination == "Para llevar" for i in self.items) else 0
