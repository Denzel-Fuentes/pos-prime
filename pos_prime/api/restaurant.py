# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

import json
import re

import frappe
from frappe import _
from frappe.utils import flt

from pos_prime.api._utils import (
	format_invoice_response,
	safe_float,
	validate_pos_access,
)
from pos_prime.api.invoices import _create_pos_invoice_doc
from pos_prime.api.items import _get_group_and_children
from pos_prime.restaurant.pricing import distribute_combo_price

DESTINATIONS = ("Mesa", "Para llevar")


@frappe.whitelist()
def get_restaurant_config(pos_profile):
	"""Everything the POS frontend needs to render combo/modifier pickers,
	fetched once at session start rather than per-item."""
	validate_pos_access(pos_profile)

	settings = frappe.get_single("Restaurant Settings")

	combos = frappe.get_all(
		"Restaurant Combo",
		filters={"disabled": 0},
		fields=[
			"name",
			"combo_name",
			"combo_price",
			"currency",
			"print_label",
			"image",
			"description",
			"sort_order",
		],
		order_by="sort_order asc, combo_name asc",
	)
	# Slot detail (with item-group expansion) is fetched per-combo, on
	# demand, by get_combo_options — mirrors the batch/serial selector
	# pattern (fetch when the picker opens, not for every combo up front).

	modifier_groups = frappe.get_all(
		"Restaurant Modifier Group",
		filters={"disabled": 0},
		fields=["name", "group_name", "selection_type", "apply_to_all_items"],
		order_by="group_name asc",
	)
	for group in modifier_groups:
		group["modifiers"] = frappe.get_all(
			"Restaurant Modifier Group Modifier",
			filters={"parent": group.name},
			fields=["modifier", "is_default"],
			order_by="idx asc",
		)
		modifier_names = [m.modifier for m in group["modifiers"]]
		modifier_meta = {
			m.name: m
			for m in frappe.get_all(
				"Restaurant Modifier",
				filters={"name": ["in", modifier_names], "disabled": 0},
				fields=["name", "modifier_name", "print_label"],
			)
		}
		group["modifiers"] = [
			{**m, **modifier_meta[m["modifier"]]}
			for m in group["modifiers"]
			if m["modifier"] in modifier_meta
		]
		if not group.apply_to_all_items:
			group["item_groups"] = [
				r.item_group
				for r in frappe.get_all(
					"Restaurant Modifier Group Item Group",
					filters={"parent": group.name},
					fields=["item_group"],
				)
			]
			group["items"] = [
				r.item
				for r in frappe.get_all(
					"Restaurant Modifier Group Item",
					filters={"parent": group.name},
					fields=["item"],
				)
			]

	has_printer = bool(
		frappe.get_all(
			"Restaurant Printer",
			filters={"disabled": 0, "pos_profile": ["in", ["", pos_profile]]},
			limit_page_length=1,
		)
	)

	return {
		"settings": settings.as_dict(),
		"combos": combos,
		"modifier_groups": modifier_groups,
		"has_printer": has_printer,
		"destinations": list(DESTINATIONS),
	}


@frappe.whitelist()
def get_combo_options(combo, pos_profile):
	"""Slot definitions for one combo, with each slot's Item Group expanded
	to include child groups — lets the frontend filter its already-loaded
	catalog client-side instead of a second item fetch per slot."""
	validate_pos_access(pos_profile)

	combo_doc = frappe.get_doc("Restaurant Combo", combo)
	slots = []
	for slot in combo_doc.slots:
		eligible_groups = (
			_get_group_and_children(slot.item_group) if slot.include_child_groups else [slot.item_group]
		)
		slots.append(
			{
				"slot_idx": slot.idx - 1,
				"slot_label": slot.slot_label,
				"item_group": slot.item_group,
				"eligible_groups": eligible_groups,
				"default_item": slot.default_item,
				"allow_modifiers": slot.allow_modifiers,
			}
		)

	return {
		"combo": combo_doc.name,
		"combo_name": combo_doc.combo_name,
		"combo_price": combo_doc.combo_price,
		"currency": combo_doc.currency,
		"print_label": combo_doc.print_label,
		"slots": slots,
	}


def _resolve_combo_selection(combo_doc, selections, profile, precision=2):
	"""Validate a combo instance's chosen items against its slot
	definitions and compute the distributed rate for each.

	`selections` is a list of {"slot_idx": int, "item_code": str} — one
	per slot, in any order. Never trusts a client-supplied rate: list
	rates are always re-fetched from the POS Profile's selling price list
	at call time.

	Returns a list of dicts (in slot order): item_code, slot_idx,
	slot_label, list_rate, rate.
	"""
	slots = combo_doc.slots
	if len(selections) != len(slots):
		frappe.throw(
			_("{0}: expected {1} components, got {2}.").format(
				combo_doc.combo_name, len(slots), len(selections)
			)
		)

	by_slot_idx = {}
	for sel in selections:
		idx = int(sel.get("slot_idx"))
		if idx in by_slot_idx:
			frappe.throw(_("{0}: slot {1} was selected twice.").format(combo_doc.combo_name, idx))
		by_slot_idx[idx] = sel.get("item_code")

	item_codes = []
	for slot in slots:
		slot_idx = slot.idx - 1
		item_code = by_slot_idx.get(slot_idx)
		if not item_code:
			frappe.throw(
				_('{0}: no item selected for slot "{1}".').format(combo_doc.combo_name, slot.slot_label)
			)

		eligible_groups = (
			_get_group_and_children(slot.item_group) if slot.include_child_groups else [slot.item_group]
		)
		item_group = frappe.db.get_value("Item", item_code, "item_group")
		if item_group not in eligible_groups:
			frappe.throw(
				_('{0}: {1} does not belong to item group "{2}" (slot "{3}").').format(
					combo_doc.combo_name, item_code, slot.item_group, slot.slot_label
				)
			)
		item_codes.append(item_code)

	list_rates = {
		r.item_code: r.price_list_rate
		for r in frappe.get_all(
			"Item Price",
			filters={"item_code": ["in", item_codes], "price_list": profile.selling_price_list, "selling": 1},
			fields=["item_code", "price_list_rate"],
		)
	}

	ordered_list_rates = [flt(list_rates.get(code, 0)) for code in item_codes]
	rates = distribute_combo_price(ordered_list_rates, flt(combo_doc.combo_price), precision)

	result = []
	for i, slot in enumerate(slots):
		result.append(
			{
				"item_code": item_codes[i],
				"slot_idx": slot.idx - 1,
				"slot_label": slot.slot_label,
				"list_rate": ordered_list_rates[i],
				"rate": rates[i],
			}
		)
	return result


@frappe.whitelist()
def preview_combo(combo, pos_profile, selections):
	"""Preview the price split for a combo instance before adding it to
	the cart. Read-only — create_restaurant_sale re-validates and
	re-computes from scratch rather than trusting this response."""
	validate_pos_access(pos_profile)

	if isinstance(selections, str):
		selections = json.loads(selections)

	combo_doc = frappe.get_doc("Restaurant Combo", combo)
	profile = frappe.get_doc("POS Profile", pos_profile)
	resolved = _resolve_combo_selection(combo_doc, selections, profile)

	return {
		"combo": combo_doc.name,
		"combo_price": combo_doc.combo_price,
		"components": resolved,
	}


def _sanitize_uid(value):
	"""Restaurant *_uid fields are Data fields that end up in report SQL —
	reject anything that isn't a plain client-generated id."""
	if value is None:
		return None
	value = str(value)
	if not re.fullmatch(r"[A-Za-z0-9\-]{1,64}", value):
		frappe.throw(_("Invalid line identifier."))
	return value


@frappe.whitelist()
def create_restaurant_sale(customer, pos_profile, items, payments, **kwargs):
	"""Atomically create the POS Invoice and its Restaurant Order.

	`items` is the same flat per-line shape create_pos_invoice accepts,
	with two additions used only by combo component lines:
	  - combo_uid: groups every line belonging to one combo instance
	  - combo, combo_slot_idx: which Restaurant Combo / slot this line fills

	Component rates are always re-derived server-side via
	distribute_combo_price — any rate the client sent for a combo line is
	discarded. Every other kwarg (taxes, discounts, loyalty, ...) is the
	same as create_pos_invoice and is forwarded as-is.

	Frappe wraps the whole request in one DB transaction that commits
	after this function returns, and invoice.submit()/order.submit() do
	not commit early — so if building the Restaurant Order fails, the
	invoice rolls back with it. Never call frappe.db.commit() on this
	path; it would break that guarantee.
	"""
	# frappe.call(method, **frappe.form_dict) always includes "cmd" (the
	# dotted method path itself, used for routing) alongside the real
	# request body — harmless for a fully-explicit signature like
	# create_pos_invoice's, but **kwargs here would otherwise forward it
	# straight into _create_pos_invoice_doc(), which doesn't accept it.
	kwargs.pop("cmd", None)

	validate_pos_access(pos_profile)

	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		frappe.throw(_("Items cannot be empty"))

	profile = frappe.get_doc("POS Profile", pos_profile)

	all_modifier_names = {m for item in items for m in (item.get("modifiers") or [])}
	modifier_labels = (
		{
			m.name: (m.print_label or m.modifier_name)
			for m in frappe.get_all(
				"Restaurant Modifier",
				filters={"name": ["in", list(all_modifier_names)]},
				fields=["name", "modifier_name", "print_label"],
			)
		}
		if all_modifier_names
		else {}
	)

	for item in items:
		item["line_uid"] = _sanitize_uid(item.get("line_uid"))
		item["combo_uid"] = _sanitize_uid(item.get("combo_uid"))
		if not item.get("destination"):
			item["destination"] = (
				frappe.db.get_single_value("Restaurant Settings", "default_destination") or "Mesa"
			)
		if item["destination"] not in DESTINATIONS:
			frappe.throw(_("Invalid destination: {0}").format(item["destination"]))
		# Silently drop any modifier name the client sent that isn't a
		# real, resolvable Restaurant Modifier — never trust it blind.
		item["modifiers"] = [m for m in (item.get("modifiers") or []) if m in modifier_labels]

	# Group items by combo_uid — everything else is sold individually.
	combo_groups = {}
	for item in items:
		if item.get("combo_uid"):
			combo_groups.setdefault(item["combo_uid"], []).append(item)

	combo_meta = {}  # combo_uid -> {"combo_doc": ..., "instance_no": ..., "destination": ...}
	for instance_no, (combo_uid, group_items) in enumerate(combo_groups.items(), start=1):
		combo_names = {i.get("combo") for i in group_items}
		if len(combo_names) != 1 or not next(iter(combo_names)):
			frappe.throw(
				_("Combo instance {0}: all components must reference the same combo.").format(combo_uid)
			)
		combo_doc = frappe.get_doc("Restaurant Combo", next(iter(combo_names)))
		if combo_doc.disabled:
			frappe.throw(_("{0} is disabled.").format(combo_doc.combo_name))

		selections = [
			{"slot_idx": i.get("combo_slot_idx"), "item_code": i.get("item_code")} for i in group_items
		]
		resolved = _resolve_combo_selection(combo_doc, selections, profile)
		resolved_by_slot = {r["slot_idx"]: r for r in resolved}

		label = f"{combo_doc.print_label or combo_doc.combo_name} #{instance_no}"
		for item in group_items:
			slot = resolved_by_slot[int(item.get("combo_slot_idx"))]
			item["rate"] = slot["rate"]
			item["lock_rate"] = True
			item["combo"] = combo_doc.name
			item["combo_slot_label"] = slot["slot_label"]
			item["combo_label"] = f"{label} · {slot['slot_label']}"
			item["description"] = f"{label} · {slot['slot_label']}"
			item["_list_rate"] = slot["list_rate"]

		combo_meta[combo_uid] = {
			"combo_doc": combo_doc,
			"instance_no": instance_no,
			"label": label,
			"destination": group_items[0]["destination"],
			"combo_price": combo_doc.combo_price,
		}

	args = dict(kwargs)
	args.update(
		customer=customer,
		pos_profile=pos_profile,
		items=items,
		payments=payments,
	)
	invoice = _create_pos_invoice_doc(**args)

	order = _build_restaurant_order(invoice, items, combo_meta, profile, modifier_labels)

	frappe.db.set_value(
		"POS Invoice", invoice.name, "pos_prime_restaurant_order", order.name, update_modified=False
	)

	response = format_invoice_response(invoice)
	response["restaurant_order"] = order.name
	return response


def _build_restaurant_order(invoice, items, combo_meta, profile, modifier_labels):
	invoice_rows_by_uid = {
		row.get("pos_prime_line_uid"): row for row in invoice.items if row.get("pos_prime_line_uid")
	}

	order = frappe.get_doc(
		{
			"doctype": "Restaurant Order",
			"pos_invoice": invoice.name,
			"pos_profile": profile.name,
			"company": profile.company,
			"customer": invoice.customer,
			"posting_date": invoice.posting_date,
			"posting_time": invoice.posting_time,
			"order_total": invoice.grand_total,
			"currency": invoice.currency,
		}
	)

	for item in items:
		row = invoice_rows_by_uid.get(item.get("line_uid"))
		combo_uid = item.get("combo_uid")
		meta = combo_meta.get(combo_uid)
		order.append(
			"items",
			{
				"line_uid": item.get("line_uid") or "",
				"item_code": item.get("item_code"),
				"qty": safe_float(item.get("qty", 1)),
				"uom": row.get("uom") if row else item.get("uom"),
				"rate": row.rate if row else safe_float(item.get("rate", 0)),
				"amount": row.amount
				if row
				else safe_float(item.get("rate", 0)) * safe_float(item.get("qty", 1)),
				"list_rate": item.get("_list_rate") if combo_uid else (row.price_list_rate if row else 0),
				"destination": item.get("destination"),
				"notes": item.get("notes") or "",
				"modifiers_summary": ", ".join(
					modifier_labels.get(m, m) for m in (item.get("modifiers") or [])
				),
				"combo_uid": combo_uid or "",
				"combo": meta["combo_doc"].name if meta else None,
				"combo_slot_label": item.get("combo_slot_label") if meta else None,
				"combo_slot_idx": item.get("combo_slot_idx") if meta else None,
				"pos_invoice_item": row.name if row else None,
				"pos_invoice_item_idx": row.idx if row else None,
			},
		)
		for modifier_name in item.get("modifiers") or []:
			order.append(
				"modifiers",
				{
					"line_uid": item.get("line_uid") or "",
					"combo_uid": combo_uid or "",
					"modifier": modifier_name,
				},
			)

	for combo_uid, meta in combo_meta.items():
		order.append(
			"combos",
			{
				"combo": meta["combo_doc"].name,
				"instance_no": meta["instance_no"],
				"combo_uid": combo_uid,
				"combo_price": meta["combo_price"],
				"destination": meta["destination"],
				"sort_index": meta["instance_no"],
			},
		)

	order.insert(ignore_permissions=True)
	order.submit()
	return order
