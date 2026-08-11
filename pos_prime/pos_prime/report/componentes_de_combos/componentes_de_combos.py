# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Which individual items get chosen for each combo slot, and how often.

Reads Restaurant Order Item/Combo joined to their submitted parent
Restaurant Order — combo_uid + combo_slot_label are only tracked here.
"""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Combo"), "fieldname": "combo", "fieldtype": "Link", "options": "Restaurant Combo", "width": 160},
		{"label": _("Slot"), "fieldname": "slot_label", "fieldtype": "Data", "width": 120},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{"label": _("Times Chosen"), "fieldname": "times_chosen", "fieldtype": "Int", "width": 110},
		{"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = ["ro.docstatus = 1", "roi.combo_uid != ''"]
	values = {}
	if filters.get("from_date"):
		conditions.append("ro.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("ro.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("company"):
		conditions.append("ro.company = %(company)s")
		values["company"] = filters["company"]

	query = f"""
		select
			roc.combo as combo,
			roi.combo_slot_label as slot_label,
			roi.item_code as item_code,
			roi.item_name as item_name,
			count(*) as times_chosen,
			sum(roi.amount) as revenue
		from `tabRestaurant Order Item` roi
		inner join `tabRestaurant Order` ro on ro.name = roi.parent
		inner join `tabRestaurant Order Combo` roc
			on roc.parent = roi.parent and roc.combo_uid = roi.combo_uid
		where {" and ".join(conditions)}
		group by roc.combo, roi.combo_slot_label, roi.item_code
		order by times_chosen desc
	"""
	return frappe.db.sql(query, values, as_dict=True)
