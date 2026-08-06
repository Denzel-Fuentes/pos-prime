# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Idempotent demo menu seed for the restaurant module.

This is site data (one pension's menu), not app data, so it is
deliberately NOT wired into hooks.fixtures — it only runs when a site
admin explicitly asks for it:

	bench --site pos.localhost execute pos_prime.restaurant.setup.setup_demo_menu \
		--kwargs "{'company': 'Estacion Tradicion', 'pos_profile': 'Denzel'}"

Every step checks for existing data first, so re-running is harmless.
"""

import frappe

DEMO_GROUPS = ["Sopas", "Segundos", "Refrescos"]

# (item_code, item_name, group, list rate, is_stock_item)
# Rates match the worked example in the original spec ([6, 9, 4] -> a 15
# combo splits to [4.74, 7.10, 3.16]) so a fresh demo reproduces it exactly.
DEMO_ITEMS = [
	("DEMO-SOPA-MANI", "Sopa de Mani", "Sopas", 6.0, 0),
	("DEMO-SOPA-QUINUA", "Sopa de Quinua", "Sopas", 6.0, 0),
	("DEMO-SEG-MILANESA", "Milanesa de Pollo", "Segundos", 9.0, 0),
	("DEMO-SEG-SILPANCHO", "Silpancho", "Segundos", 9.0, 0),
	("DEMO-REF-MOCOCHINCHI", "Mocochinchi", "Refrescos", 4.0, 1),
	("DEMO-REF-MARACUYA", "Refresco de Maracuya", "Refrescos", 4.0, 1),
]

COMBO_NAME = "Completo"
COMBO_PRICE = 15.0
COMBO_SLOTS = [
	("Sopa", "Sopas", "DEMO-SOPA-MANI"),
	("Segundo", "Segundos", "DEMO-SEG-MILANESA"),
	("Refresco", "Refrescos", "DEMO-REF-MOCOCHINCHI"),
]

MODIFIER_GROUP = "Sin ingredientes"
MODIFIERS = ["Sin cebolla", "Sin sal", "Sin picante"]

PRINTER_NAME = "Impresora de Cocina (configurar IP)"


def setup_demo_menu(company, pos_profile):
	"""Create a small demo menu: 3 item groups, 6 items (stock only for
	Refrescos), the "Completo" combo, a free modifier group, and a
	disabled placeholder printer — then makes sure the POS Profile and
	Restaurant Settings actually surface it.
	"""
	profile = frappe.get_doc("POS Profile", pos_profile)
	price_list = profile.selling_price_list
	currency = frappe.db.get_value("Company", company, "default_currency")
	# Never hardcode "Nos" — on a non-English site the seeded default UOM's
	# actual docname is itself a translation (e.g. "Nos." on this site).
	stock_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"

	for group in DEMO_GROUPS:
		_ensure_item_group(group)

	for item_code, item_name, group, rate, is_stock in DEMO_ITEMS:
		_ensure_item(item_code, item_name, group, is_stock, stock_uom)
		_ensure_price(item_code, price_list, rate, currency)
		if is_stock:
			_ensure_opening_stock(item_code, company, profile.warehouse, qty=50, rate=rate * 0.5)

	_ensure_combo(company, currency)
	_ensure_modifier_group()
	_ensure_placeholder_printer(pos_profile)
	_ensure_profile_item_groups(profile)
	_ensure_restaurant_mode_enabled()

	frappe.db.commit()
	print("Demo menu ready.")


def _root_item_group():
	"""The tree root's name, not its label — on a non-English site "All
	Item Groups" is itself a translation and isn't the actual docname
	(e.g. a Spanish-localized site's root is literally named "Todos los
	grupos de articulos"). Found by structure (is_group with no parent),
	never hardcoded."""
	return frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ["in", ["", None]]}, "name")


def _ensure_item_group(name):
	if frappe.db.exists("Item Group", name):
		return
	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": _root_item_group(),
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	print(f"  Item Group: {name}")


def _ensure_item(item_code, item_name, group, is_stock, stock_uom):
	if frappe.db.exists("Item", item_code):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": group,
			"stock_uom": stock_uom,
			"is_stock_item": is_stock,
		}
	).insert(ignore_permissions=True)
	print(f"  Item: {item_code} - {item_name}")


def _ensure_price(item_code, price_list, rate, currency):
	if frappe.db.exists("Item Price", {"item_code": item_code, "price_list": price_list, "selling": 1}):
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": price_list,
			"price_list_rate": rate,
			"currency": currency,
			"selling": 1,
		}
	).insert(ignore_permissions=True)


def _ensure_opening_stock(item_code, company, warehouse, qty, rate):
	if not warehouse:
		return
	if frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"):
		return
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"items": [{"item_code": item_code, "qty": qty, "t_warehouse": warehouse, "basic_rate": rate}],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	print(f"  Stock: {item_code} x{qty}")


def _ensure_combo(company, currency):
	if frappe.db.exists("Restaurant Combo", COMBO_NAME):
		return
	frappe.get_doc(
		{
			"doctype": "Restaurant Combo",
			"combo_name": COMBO_NAME,
			"company": company,
			"currency": currency,
			"combo_price": COMBO_PRICE,
			"print_label": COMBO_NAME.upper(),
			"slots": [
				{"slot_label": label, "item_group": group, "default_item": default_item}
				for label, group, default_item in COMBO_SLOTS
			],
		}
	).insert(ignore_permissions=True)
	print(f"  Combo: {COMBO_NAME} @ {COMBO_PRICE}")


def _ensure_modifier_group():
	if frappe.db.exists("Restaurant Modifier Group", MODIFIER_GROUP):
		return
	for name in MODIFIERS:
		if not frappe.db.exists("Restaurant Modifier", name):
			frappe.get_doc({"doctype": "Restaurant Modifier", "modifier_name": name}).insert(
				ignore_permissions=True
			)
	frappe.get_doc(
		{
			"doctype": "Restaurant Modifier Group",
			"group_name": MODIFIER_GROUP,
			"selection_type": "Multiple",
			"apply_to_all_items": 1,
			"modifiers": [{"modifier": name} for name in MODIFIERS],
		}
	).insert(ignore_permissions=True)
	print(f"  Modifier Group: {MODIFIER_GROUP}")


def _ensure_placeholder_printer(pos_profile):
	if frappe.db.exists("Restaurant Printer", PRINTER_NAME):
		return
	frappe.get_doc(
		{
			"doctype": "Restaurant Printer",
			"printer_name": PRINTER_NAME,
			"pos_profile": pos_profile,
			"host": "192.168.1.100",
			"port": 9100,
			# Left disabled: this IP is a placeholder. Left enabled it would
			# just fail every sale's comanda (harmlessly, per printing.py's
			# guarantees) until someone points it at a real printer — better
			# to make that step explicit.
			"disabled": 1,
		}
	).insert(ignore_permissions=True)
	print(f"  Printer placeholder: {PRINTER_NAME} (disabled — set the real IP, then enable)")


def _ensure_profile_item_groups(profile):
	"""If this POS Profile restricts visible item groups, the new demo
	groups need to be added to that allow-list or they'll never show up
	in the grid (pos_prime/api/items.py's group_filter_list)."""
	if not profile.item_groups:
		return  # no restriction configured — nothing to do
	existing = {row.item_group for row in profile.item_groups}
	added = False
	for group in DEMO_GROUPS:
		if group not in existing:
			profile.append("item_groups", {"item_group": group})
			added = True
	if added:
		profile.save(ignore_permissions=True)
		print("  Added demo groups to POS Profile's allowed item groups")


def _ensure_restaurant_mode_enabled():
	settings = frappe.get_single("Restaurant Settings")
	if not settings.enable_restaurant_mode:
		settings.enable_restaurant_mode = 1
		settings.save(ignore_permissions=True)
		print("  Enabled Restaurant Mode")
