# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Which exact combination of components (e.g. which Sopa+Segundo+Refresco
trio) is most popular within one combo.

Requires a Combo filter rather than trying to show every combo at once:
each combo can have a different number/labeling of slots, so the column
set is only well-defined once a specific combo is chosen. Groups
Restaurant Order Item rows by combo_uid (every component of one combo
instance shares it) into a single "which items filled which slots" key
per instance, then counts how often each distinct key occurs — this is
only possible because combo_uid + combo_slot_idx are stored per line;
see pos_prime/api/restaurant.py::_build_restaurant_order.
"""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("combo"):
		frappe.msgprint(_("Select a Combo to see its most popular component combinations."))
		return [], []

	slots = frappe.get_all(
		"Restaurant Combo Slot",
		filters={"parent": filters.combo},
		fields=["idx", "slot_label"],
		order_by="idx asc",
	)
	if not slots:
		frappe.throw(_("{0} has no slots defined.").format(filters.combo))

	columns = get_columns(slots)
	data = get_data(filters, slots)
	return columns, data


def get_columns(slots):
	columns = [
		{"label": slot.slot_label, "fieldname": f"slot_{slot.idx - 1}", "fieldtype": "Data", "width": 160}
		for slot in slots
	]
	columns.append({"label": _("Times Sold"), "fieldname": "count", "fieldtype": "Int", "width": 110})
	columns.append({"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 130})
	return columns


def get_data(filters, slots):
	conditions = ["ro.docstatus = 1", "roc.combo = %(combo)s"]
	values = {"combo": filters.combo}
	if filters.get("from_date"):
		conditions.append("ro.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("ro.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	rows = frappe.db.sql(
		f"""
			select
				roi.combo_uid as combo_uid,
				roi.combo_slot_idx as slot_idx,
				roi.item_name as item_name,
				roc.combo_price as combo_price
			from `tabRestaurant Order Item` roi
			inner join `tabRestaurant Order` ro on ro.name = roi.parent
			inner join `tabRestaurant Order Combo` roc
				on roc.parent = roi.parent and roc.combo_uid = roi.combo_uid
			where {" and ".join(conditions)}
		""",
		values,
		as_dict=True,
	)

	# One entry per combo instance: {slot_idx: item_name}, plus its price.
	instances = {}
	for row in rows:
		inst = instances.setdefault(row.combo_uid, {"price": row.combo_price, "items": {}})
		inst["items"][row.slot_idx] = row.item_name

	combinations = {}
	for inst in instances.values():
		key = tuple(inst["items"].get(slot.idx - 1, "") for slot in slots)
		bucket = combinations.setdefault(key, {"count": 0, "revenue": 0})
		bucket["count"] += 1
		bucket["revenue"] += inst["price"]

	data = []
	for key, agg in combinations.items():
		row = {f"slot_{i}": value for i, value in enumerate(key)}
		row["count"] = agg["count"]
		row["revenue"] = agg["revenue"]
		data.append(row)

	data.sort(key=lambda r: r["count"], reverse=True)
	return data
