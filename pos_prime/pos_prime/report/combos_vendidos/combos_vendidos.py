# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Combos sold, optionally bucketed by day or month.

Reads Restaurant Order Combo (one row per combo instance sold) joined to
its submitted parent Restaurant Order — never Sales Invoice, since a
combo only exists as a concept in this module; POS Invoice only sees its
component lines. See pos_prime/api/restaurant.py::_build_restaurant_order.
"""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	period_label = {"Daily": _("Date"), "Monthly": _("Month")}.get(filters.get("period"), _("Period"))
	return [
		{"label": period_label, "fieldname": "period", "fieldtype": "Data", "width": 120},
		{
			"label": _("Combo"),
			"fieldname": "combo",
			"fieldtype": "Link",
			"options": "Restaurant Combo",
			"width": 180,
		},
		{"label": _("Instances Sold"), "fieldname": "instances", "fieldtype": "Int", "width": 130},
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
	if filters.get("combo"):
		conditions.append("roc.combo = %(combo)s")
		values["combo"] = filters["combo"]

	period = filters.get("period")
	if period == "Daily":
		period_select, group_by = "ro.posting_date as period", "ro.posting_date, roc.combo"
	elif period == "Monthly":
		period_select = "date_format(ro.posting_date, '%%Y-%%m') as period"
		group_by = "date_format(ro.posting_date, '%%Y-%%m'), roc.combo"
	else:
		period_select, group_by = "%(range_label)s as period", "roc.combo"
		values["range_label"] = _("All")

	query = f"""
		select
			{period_select},
			roc.combo as combo,
			count(*) as instances,
			sum(roc.combo_price) as revenue
		from `tabRestaurant Order Combo` roc
		inner join `tabRestaurant Order` ro on ro.name = roc.parent
		where {" and ".join(conditions)}
		group by {group_by}
		order by period desc, revenue desc
	"""
	return frappe.db.sql(query, values, as_dict=True)
