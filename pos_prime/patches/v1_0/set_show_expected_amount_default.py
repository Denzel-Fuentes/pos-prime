# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe


def execute():
	# Same reasoning as set_hide_category_search_default: a Single's new
	# Check field lands in tabSingles as 0 (or absent), never as the
	# doctype's default of 1, so an existing site would silently switch to
	# a blind close. Written unconditionally; a patch runs once per site
	# (Patch Log), so it can't undo an admin's later choice.
	frappe.db.set_single_value("Restaurant Settings", "show_expected_amount_on_close", 1)
