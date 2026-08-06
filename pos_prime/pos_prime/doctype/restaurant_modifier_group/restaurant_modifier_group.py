# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RestaurantModifierGroup(Document):
	def validate(self):
		if not self.modifiers:
			frappe.throw(_("Add at least one modifier to the group."))
