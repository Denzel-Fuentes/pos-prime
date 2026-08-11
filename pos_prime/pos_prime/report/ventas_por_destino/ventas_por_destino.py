# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Revenue by destination (dine-in vs takeaway) per day.

Reads Restaurant Order Item joined to its submitted parent Restaurant
Order — never Sales Invoice, since destination is a pos_prime_* field
that doesn't survive POS Closing Entry consolidation.
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
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Destination"), "fieldname": "destination", "fieldtype": "Data", "width": 120},
		{"label": _("Orders"), "fieldname": "orders", "fieldtype": "Int", "width": 90},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 130},
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

	query = f"""
		select
			ro.posting_date as posting_date,
			roi.destination as destination,
			count(distinct ro.name) as orders,
			sum(roi.qty) as qty,
			sum(roi.amount) as revenue
		from `tabRestaurant Order Item` roi
		inner join `tabRestaurant Order` ro on ro.name = roi.parent
		where {" and ".join(conditions)}
		group by ro.posting_date, roi.destination
		order by ro.posting_date desc
	"""
	return frappe.db.sql(query, values, as_dict=True)
