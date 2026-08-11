# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

from pos_prime.restaurant.custom_fields import create_restaurant_custom_fields
from pos_prime.restaurant.print_formats import create_ticket_print_formats


def after_install():
	create_restaurant_custom_fields()
	# Seeded, not wired: a Restaurant Printer keeps using the built-in
	# layout until someone points its Print Format field at one of these.
	create_ticket_print_formats()
