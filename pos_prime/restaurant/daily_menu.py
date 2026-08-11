# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Daily dish availability — the "platos del dia" gate.

Restaurant Settings can flag a handful of Item Groups (e.g. Segundos, Sopas,
Refrescos) as requiring an explicit daily selection: dishes in those groups
are only sellable once the cashier has picked them at shift-open time (see
pos_prime.api.pos_session.create_opening_entry, which writes the picks onto
the new POS Opening Entry's pos_prime_available_items field). Item Groups not
listed here are completely unaffected and always fully available, same as
before this feature existed.

This module is imported lazily (inside the function body) from
pos_prime/api/items.py rather than at module load time, so the base item
catalog stays restaurant-agnostic when the feature is off and there's no
circular import back from the base API layer into the restaurant layer —
pos_prime/api/restaurant.py already imports the other way (from items.py),
establishing that direction.
"""

import frappe

from pos_prime.api.items import _get_group_and_children


def get_daily_menu_gate(pos_profile):
	"""Returns (gated_item_groups, allowed_item_codes_today) as sets, or
	None if the gate isn't active — restaurant mode is off, no Item Groups
	are configured under Restaurant Settings' Daily Menu section, or there's
	no open POS Opening Entry yet for this user/profile (nothing to gate
	against before a shift exists).

	gated_item_groups is already expanded through child groups (matching
	the combo-slot / POS Profile item-group filtering pattern elsewhere in
	this app), so callers can do a plain "item_group IN" check.
	"""
	if not frappe.db.get_single_value("Restaurant Settings", "enable_restaurant_mode"):
		return None

	configured_groups = [
		r.item_group
		for r in frappe.get_all(
			"Restaurant Daily Menu Item Group",
			filters={"parent": "Restaurant Settings"},
			fields=["item_group"],
		)
	]
	if not configured_groups:
		return None

	opening_entry = frappe.db.get_value(
		"POS Opening Entry",
		{
			"user": frappe.session.user,
			"pos_profile": pos_profile,
			"status": "Open",
			"docstatus": 1,
		},
		"name",
	)
	if not opening_entry:
		return None

	gated_item_groups = set()
	for group in configured_groups:
		gated_item_groups.update(_get_group_and_children(group))

	allowed_item_codes = {
		r.item
		for r in frappe.get_all(
			"Restaurant Opening Entry Item",
			filters={"parent": opening_entry},
			fields=["item"],
		)
	}

	return gated_item_groups, allowed_item_codes
