# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""How much of each item's sales came from combos vs sold on its own.

Reads Restaurant Order Item joined to its submitted parent Restaurant
Order — combo_uid is only tracked here, never on Sales Invoice.
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
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{"label": _("Sold Individually"), "fieldname": "sold_individually", "fieldtype": "Float", "width": 130},
		{"label": _("Sold In Combo"), "fieldname": "sold_in_combo", "fieldtype": "Float", "width": 120},
		{"label": _("Total Qty"), "fieldname": "total_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Total Revenue"), "fieldname": "total_revenue", "fieldtype": "Currency", "width": 140},
	]


def get_data(filters):
	conditions = ["ro.docstatus = 1"]
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
	if filters.get("item_code"):
		conditions.append("roi.item_code = %(item_code)s")
		values["item_code"] = filters["item_code"]

	query = f"""
		select
			roi.item_code as item_code,
			roi.item_name as item_name,
			sum(case when roi.combo_uid = '' or roi.combo_uid is null then roi.qty else 0 end) as sold_individually,
			sum(case when roi.combo_uid != '' and roi.combo_uid is not null then roi.qty else 0 end) as sold_in_combo,
			sum(roi.qty) as total_qty,
			sum(roi.amount) as total_revenue
		from `tabRestaurant Order Item` roi
		inner join `tabRestaurant Order` ro on ro.name = roi.parent
		where {" and ".join(conditions)}
		group by roi.item_code, roi.item_name
		order by total_revenue desc
	"""
	return frappe.db.sql(query, values, as_dict=True)
