# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RestaurantCombo(Document):
	def validate(self):
		if not self.slots:
			frappe.throw(_("Add at least one component slot (e.g. Sopa, Segundo, Refresco)."))
