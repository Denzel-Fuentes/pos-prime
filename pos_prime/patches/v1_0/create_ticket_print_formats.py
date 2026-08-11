# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

from pos_prime.restaurant.print_formats import create_ticket_print_formats


def execute():
	# create-if-missing, so this can't clobber a format an admin already
	# edited (or one they deliberately deleted and rebuilt by hand).
	create_ticket_print_formats()
