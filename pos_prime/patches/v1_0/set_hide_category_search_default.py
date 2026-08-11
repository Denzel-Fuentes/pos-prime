# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe


def execute():
	# A Single's new fields don't inherit their doctype default on a site
	# that already has a Restaurant Settings row: depending on when the
	# DocType sync materializes the column, the value ends up either absent
	# or 0 — never the doctype's 1. So write it here, unconditionally.
	# A patch runs exactly once per site (Frappe records it in Patch Log),
	# so this can't undo an admin's later choice.
	frappe.db.set_single_value("Restaurant Settings", "hide_category_search", 1)
