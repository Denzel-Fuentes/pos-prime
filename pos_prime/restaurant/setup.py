# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Idempotent demo menu seed for the restaurant module.

This is site data (one pension's menu), not app data, so it is
deliberately NOT wired into hooks.fixtures — it only runs when a site
admin explicitly asks for it:

	bench --site pos.localhost execute pos_prime.restaurant.setup.setup_demo_menu \
		--kwargs "{'company': 'Estacion Tradicion', 'pos_profile': 'Denzel'}"

A second, independent seed (`setup_demo_variant_menu`) creates an Item
Group tree with template/variant Items — for testing the POS's template
card -> variant picker flow (get_item_variants):

	bench --site pos.localhost execute pos_prime.restaurant.setup.setup_demo_variant_menu \
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
	_ensure_daily_menu_groups()

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


def _ensure_profile_item_groups(profile, groups=DEMO_GROUPS):
	"""If this POS Profile restricts visible item groups, the new demo
	groups need to be added to that allow-list or they'll never show up
	in the grid (pos_prime/api/items.py's group_filter_list)."""
	if not profile.item_groups:
		return  # no restriction configured — nothing to do
	existing = {row.item_group for row in profile.item_groups}
	added = False
	for group in groups:
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


def _ensure_daily_menu_groups():
	"""Reference config for the "platos del dia" feature: require an
	explicit daily selection for the same three demo groups this seed
	already creates (Sopas, Segundos, Refrescos) — a site adopting this
	feature for real would list its own equivalent categories here
	instead."""
	settings = frappe.get_single("Restaurant Settings")
	existing = {row.item_group for row in settings.daily_menu_item_groups}
	added = False
	for group in DEMO_GROUPS:
		if group not in existing:
			settings.append("daily_menu_item_groups", {"item_group": group})
			added = True
	if added:
		settings.save(ignore_permissions=True)
		print("  Daily Menu requires a selection for: " + ", ".join(DEMO_GROUPS))


# ── Template/variant demo data ("Pollo a la Brasa") ──────────────────────
# Exercises pos_prime/api/items.py's template-card -> get_item_variants
# flow: two ERPNext Item Templates (has_variants=1) with real variants via
# the "Corte" Item Attribute, plus one simple item with no variants at all
# (Pollo Entero) to confirm that path is untouched.

VARIANT_ROOT_GROUP = "Pollo a la Brasa"
VARIANT_CHILD_GROUPS = ["Pollo 1/4", "Pollo 1/2", "Pollo Entero"]

CORTE_ATTRIBUTE = "Corte"
# (value, abbr) — abbr is a mandatory field on Item Attribute Value.
CORTE_VALUES = [
	("Pierna", "PIE"),
	("Pecho", "PEC"),
	("Pierna+Pecho", "P+P"),
	("Contra+Ala", "C+A"),
]

# (template_code, template_name, group, [(variant_code, variant_name, attribute_value, rate), ...])
VARIANT_TEMPLATES = [
	(
		"DEMO-POLLO-14",
		"Pollo a la Brasa 1/4",
		"Pollo 1/4",
		[
			("DEMO-POLLO-14-PIERNA", "Pollo a la Brasa 1/4 - Pierna", "Pierna", 12.0),
			("DEMO-POLLO-14-PECHO", "Pollo a la Brasa 1/4 - Pecho", "Pecho", 12.0),
		],
	),
	(
		"DEMO-POLLO-12",
		"Pollo a la Brasa 1/2",
		"Pollo 1/2",
		[
			("DEMO-POLLO-12-PP", "Pollo a la Brasa 1/2 - Pierna+Pecho", "Pierna+Pecho", 22.0),
			("DEMO-POLLO-12-CA", "Pollo a la Brasa 1/2 - Contra+Ala", "Contra+Ala", 22.0),
		],
	),
]

# Simple item (no variants) — the "only one option" leaf from the tree.
VARIANT_SIMPLE_ITEM = ("DEMO-POLLO-ENTERO", "Pollo a la Brasa Entero", "Pollo Entero", 40.0)


def setup_demo_variant_menu(company, pos_profile):
	"""Create the "Pollo a la Brasa" Item Group tree (parent + 3 children),
	two Item Templates with real variants via the "Corte" attribute, and
	one variant-less item — a minimal fixture for testing the POS's
	template-card -> variant-picker flow end to end."""
	profile = frappe.get_doc("POS Profile", pos_profile)
	price_list = profile.selling_price_list
	currency = frappe.db.get_value("Company", company, "default_currency")
	stock_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"

	_ensure_item_group_node(VARIANT_ROOT_GROUP, _root_item_group(), is_group=1)
	for group in VARIANT_CHILD_GROUPS:
		_ensure_item_group_node(group, VARIANT_ROOT_GROUP, is_group=0)

	_ensure_item_attribute(CORTE_ATTRIBUTE, CORTE_VALUES)

	for template_code, template_name, group, variants in VARIANT_TEMPLATES:
		_ensure_item_template(template_code, template_name, group, stock_uom, CORTE_ATTRIBUTE)
		for item_code, item_name, attr_value, rate in variants:
			_ensure_variant_item(item_code, item_name, template_code, group, stock_uom, CORTE_ATTRIBUTE, attr_value)
			_ensure_price(item_code, price_list, rate, currency)

	simple_code, simple_name, simple_group, simple_rate = VARIANT_SIMPLE_ITEM
	_ensure_item(simple_code, simple_name, simple_group, is_stock=0, stock_uom=stock_uom)
	_ensure_price(simple_code, price_list, simple_rate, currency)

	_ensure_profile_item_groups(profile, groups=[VARIANT_ROOT_GROUP, *VARIANT_CHILD_GROUPS])

	frappe.db.commit()
	print("Demo variant menu ready.")


def _ensure_item_group_node(name, parent, is_group):
	if frappe.db.exists("Item Group", name):
		return
	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": parent,
			"is_group": is_group,
		}
	).insert(ignore_permissions=True)
	print(f"  Item Group: {name}")


def _ensure_item_attribute(name, values):
	if frappe.db.exists("Item Attribute", name):
		return
	frappe.get_doc(
		{
			"doctype": "Item Attribute",
			"attribute_name": name,
			"item_attribute_values": [
				{"attribute_value": value, "abbr": abbr} for value, abbr in values
			],
		}
	).insert(ignore_permissions=True)
	print(f"  Item Attribute: {name}")


def _ensure_item_template(item_code, item_name, group, stock_uom, attribute_name):
	if frappe.db.exists("Item", item_code):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": group,
			"stock_uom": stock_uom,
			"is_stock_item": 0,
			"has_variants": 1,
			"variant_based_on": "Item Attribute",
			"attributes": [{"attribute": attribute_name}],
		}
	).insert(ignore_permissions=True)
	print(f"  Template: {item_code} - {item_name}")


def _ensure_variant_item(item_code, item_name, template_code, group, stock_uom, attribute_name, attribute_value):
	if frappe.db.exists("Item", item_code):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": group,
			"stock_uom": stock_uom,
			"is_stock_item": 0,
			"variant_of": template_code,
			"attributes": [{"attribute": attribute_name, "attribute_value": attribute_value}],
		}
	).insert(ignore_permissions=True)
	print(f"  Variant: {item_code} - {item_name}")
