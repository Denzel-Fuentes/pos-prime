# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import frappe

# Ticket-content checks that default to on. The layout code already treats an
# absent value as "show" (see pos_prime/restaurant/ticket_options.py), so this
# is about the Desk form: without it an admin opens Restaurant Settings, sees
# every box unchecked, and has no way to tell that the tickets are in fact
# printing all of it.
FIELDS = (
	"comanda_show_order_no",
	"comanda_show_time",
	"comanda_show_customer",
	"comanda_show_modifiers",
	"receipt_show_invoice_info",
	"receipt_show_customer",
	"receipt_show_taxes",
	"receipt_show_payments",
)


def execute():
	# Written unconditionally: syncing the DocType materializes the new
	# Check fields into tabSingles as 0 before patches run, so an
	# "only if unset" guard would never fire and every ticket would come
	# out stripped. A patch runs exactly once per site (Frappe records it
	# in Patch Log), so this can't undo an admin's later choice.
	for fieldname in FIELDS:
		frappe.db.set_single_value("Restaurant Settings", fieldname, 1)
