# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Pure combo price distribution — no Frappe/DB dependency beyond frappe.throw.

Given the list price of each component in a combo and the combo's fixed
selling price, split the fixed price across the components so the split
sums to EXACTLY the combo price (to the cent).

Three methods, chosen per combo (see Restaurant Combo.pricing_method, with
Restaurant Settings.default_combo_pricing_method as the fallback):

  - Proporcional: every component drops by the same percentage, so each
    dish keeps its relative weight in the kitchen's numbers.
  - Margen alto: components keep their list price and the whole discount is
    taken out of the slots flagged to absorb it (Restaurant Combo Slot.
    discount_order), in that order — for when the main dish costs too much
    in ingredients to discount and the drink can carry the loss instead.
  - Mixto: the protected slots keep their list price and what's left of the
    combo price is split proportionally among the absorbing ones.

Everything is computed in integer minor units (cents), so "sums exactly" is
a property of the arithmetic rather than of floating-point luck.

This is backend-only and authoritative: the frontend previews a split via
pos_prime.api.restaurant.preview_combo rather than porting this logic to
TypeScript, so there is exactly one implementation to keep correct — and
the caller building the actual sale never trusts a client-supplied split.
"""

import math

import frappe

PROPORTIONAL = "Proporcional"
ABSORPTION = "Margen alto"
MIXED = "Mixto"
METHODS = (PROPORTIONAL, ABSORPTION, MIXED)


def _proportional_units(list_units, total_units):
	"""Split total_units across list_units proportionally, in integer units.

	Largest-remainder (Hare) method, so the result sums exactly. Falls back
	to an equal split when every list rate is 0 (e.g. a combo made entirely
	of complimentary components).

	Deterministic: remainder ties break by larger list rate, then by lower
	index, so the same input always produces the same split.
	"""
	n = len(list_units)
	total_list = sum(list_units)

	if total_list > 0:
		raw = [total_units * units / total_list for units in list_units]
	else:
		raw = [total_units / n] * n

	floors = [math.floor(r) for r in raw]
	remainders = [r - f for r, f in zip(raw, floors, strict=True)]
	leftover = total_units - sum(floors)

	order = sorted(range(n), key=lambda i: (-remainders[i], -list_units[i], i))
	result = list(floors)
	for i in order[:leftover]:
		result[i] += 1
	return result


def _absorb(units, indices, delta, unbounded_at=None):
	"""Take `delta` (integer units, positive) out of the components named by
	`indices`, in that order, flooring each at zero — except the position
	given by `unbounded_at`, which swallows whatever is left even if that
	pushes the component below zero.

	Returns whatever could not be absorbed (0 in every realistic case: the
	components can always give back at most their own list price, which is
	exactly what a discount asks of them).
	"""
	for position, i in enumerate(indices):
		if delta <= 0:
			break
		if position == unbounded_at:
			units[i] -= delta
			return 0
		take = min(delta, max(0, units[i]))
		units[i] -= take
		delta -= take
	return delta


def distribute_combo_price(list_rates, combo_price, precision=2):
	"""Proportional split — kept as its own entry point because it's the
	primitive the other methods build on, and the one every existing caller
	and doc refers to."""
	if not list_rates:
		frappe.throw("distribute_combo_price: at least one component is required.")

	scale = 10**precision
	total_units = round(combo_price * scale)
	units = _proportional_units([round(rate * scale) for rate in list_rates], total_units)

	if sum(units) != total_units:
		# Should be unreachable — fail loud rather than silently mis-price a sale.
		frappe.throw("distribute_combo_price: split does not sum to the combo price.")

	return [u / scale for u in units]


def split_combo_price(
	list_rates,
	combo_price,
	method=PROPORTIONAL,
	discount_orders=None,
	allow_negative=False,
	precision=2,
):
	"""Split combo_price across the components by the combo's chosen method.

	`discount_orders` is aligned with `list_rates`: 1 absorbs the discount
	first, 2 second, and 0 (or None) means the slot is protected — it only
	gives anything up if the absorbers couldn't cover the discount on their
	own. `allow_negative` lets the last absorber go below zero instead of
	cascading (the "refresco at -3.00, booked as a loss on the drink" case).
	"""
	n = len(list_rates)
	if n == 0:
		frappe.throw("split_combo_price: at least one component is required.")

	orders = list(discount_orders or [0] * n)
	absorbers = sorted(
		(i for i in range(n) if (orders[i] or 0) >= 1), key=lambda i: (orders[i], i)
	)
	protected = [i for i in range(n) if i not in set(absorbers)]

	# No absorber configured means the other two methods have nothing to act
	# on — fall back rather than mis-price a sale. Restaurant Combo.validate
	# catches this at save time, where it can actually be corrected.
	if method not in (ABSORPTION, MIXED) or not absorbers:
		return distribute_combo_price(list_rates, combo_price, precision)

	scale = 10**precision
	total_units = round(combo_price * scale)
	units = [round(rate * scale) for rate in list_rates]

	if method == ABSORPTION:
		delta = sum(units) - total_units
		if delta < 0:
			# Combo priced ABOVE the sum of its parts: there's no discount to
			# absorb, so the surcharge goes to the first absorber.
			units[absorbers[0]] -= delta
			delta = 0
		elif delta > 0:
			cascade = absorbers + protected
			delta = _absorb(
				units,
				cascade,
				delta,
				unbounded_at=(len(absorbers) - 1) if allow_negative else None,
			)
			if delta:
				# Unreachable for a combo priced at or above zero; keep the
				# invariant rather than return a split that doesn't add up.
				units[cascade[-1]] -= delta
	else:  # MIXED
		remaining = total_units - sum(units[i] for i in protected)
		if remaining >= 0:
			split = _proportional_units([units[i] for i in absorbers], remaining)
			for position, i in enumerate(absorbers):
				units[i] = split[position]
		else:
			# The protected slots alone already cost more than the combo: the
			# absorbers go to zero and the deficit cascades into the protected
			# ones, cheapest configuration order first.
			for i in absorbers:
				units[i] = 0
			deficit = _absorb(
				units,
				protected,
				-remaining,
				unbounded_at=(len(protected) - 1) if allow_negative and protected else None,
			)
			if deficit:
				units[(protected or absorbers)[-1]] -= deficit

	if sum(units) != total_units:
		# Should be unreachable — fail loud rather than silently mis-price a sale.
		frappe.throw("split_combo_price: split does not sum to the combo price.")

	return [u / scale for u in units]
