# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""doc_events handlers wired from pos_prime/hooks.py."""

import frappe


def cancel_linked_restaurant_order(doc, method=None):
	"""POS Invoice: on_cancel — cancel the Restaurant Order it produced, if any.

	Guarded with has_field() since this fires for every POS Invoice cancel,
	including on sites/versions where the restaurant module's custom field
	hasn't been migrated yet.
	"""
	if not frappe.get_meta("POS Invoice").has_field("pos_prime_restaurant_order"):
		return

	order_name = doc.get("pos_prime_restaurant_order")
	if not order_name:
		return

	order = frappe.get_doc("Restaurant Order", order_name)
	if order.docstatus == 1:
		order.cancel()
