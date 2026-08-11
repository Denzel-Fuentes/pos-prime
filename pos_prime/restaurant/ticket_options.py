# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Which sections a ticket prints, read off Restaurant Settings.

Shared by the kitchen ticket (printing.py) and the till receipt
(receipt_ticket.py) so both read their toggles the same way — and so
neither has to import the other just for this.

The default matters: a Check field added to a Single doctype does NOT
inherit its `default` on a site whose Restaurant Settings row already
exists (or was never saved at all) — the value is simply absent, which
would read as 0 and silently strip sections off every ticket. So an
absent value means "show", matching the doctype defaults, and only an
explicit 0 hides anything. patches/v1_0/set_ticket_content_defaults.py
writes the 1s once so the checkboxes also *look* right in the Desk form.
"""


def shows(settings, fieldname, default=True):
	value = settings.get(fieldname)
	if value is None:
		return default
	return bool(value)
