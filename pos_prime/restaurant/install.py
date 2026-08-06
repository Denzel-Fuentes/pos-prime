# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

from pos_prime.restaurant.custom_fields import create_restaurant_custom_fields


def after_install():
	create_restaurant_custom_fields()
