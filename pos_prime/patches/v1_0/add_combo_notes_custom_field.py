# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

from pos_prime.restaurant.custom_fields import create_restaurant_custom_fields


def execute():
	# create_custom_fields() is idempotent — it skips fields that already
	# exist, so re-running it here only adds the new pos_prime_combo_notes
	# field without touching the ones add_restaurant_custom_fields already
	# created.
	create_restaurant_custom_fields()
