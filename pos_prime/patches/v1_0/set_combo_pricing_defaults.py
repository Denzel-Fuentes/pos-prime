# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe

from pos_prime.restaurant.pricing import PROPORTIONAL


def execute():
	# Written unconditionally: syncing the DocType materializes the new field
	# into tabSingles as empty before patches run, so an "only if unset" guard
	# would never fire. A patch runs exactly once per site (Frappe records it
	# in Patch Log), so this can't undo an admin's later choice.
	#
	# Existing combos keep pricing_method blank, which means "inherit" — so
	# every combo already configured goes on being priced proportionally,
	# exactly as before.
	frappe.db.set_single_value("Restaurant Settings", "default_combo_pricing_method", PROPORTIONAL)
