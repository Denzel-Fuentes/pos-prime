# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Pure combo price distribution — no Frappe/DB dependency beyond frappe.throw.

Given the list price of each component in a combo and the combo's fixed
selling price, split the fixed price across the components so the split
sums to EXACTLY the combo price (to the cent) and is proportional to each
component's list price.

This is backend-only and authoritative: the frontend previews a split via
pos_prime.api.restaurant.preview_combo rather than porting this logic to
TypeScript, so there is exactly one implementation to keep correct — and
the caller building the actual sale never trusts a client-supplied split.
"""

import frappe


def distribute_combo_price(list_rates, combo_price, precision=2):
	"""Split combo_price across len(list_rates) components.

	Works in integer minor units (cents) and uses the largest-remainder
	(Hare) method, so the result sums exactly regardless of floating-point
	rounding. Falls back to an equal split when every list rate is 0 (e.g.
	a combo made entirely of complimentary components).

	Deterministic: remainder ties break by larger list rate, then by lower
	index, so the same input always produces the same split.
	"""
	n = len(list_rates)
	if n == 0:
		frappe.throw("distribute_combo_price: at least one component is required.")

	scale = 10**precision
	total_units = round(combo_price * scale)
	total_list = sum(list_rates)

	if total_list > 0:
		raw = [total_units * rate / total_list for rate in list_rates]
	else:
		raw = [total_units / n] * n

	floors = [int(r) for r in raw]
	remainders = [r - f for r, f in zip(raw, floors, strict=True)]
	leftover = total_units - sum(floors)

	order = sorted(range(n), key=lambda i: (-remainders[i], -list_rates[i], i))
	units = list(floors)
	for i in order[:leftover]:
		units[i] += 1

	if sum(units) != total_units:
		# Should be unreachable — fail loud rather than silently mis-price a sale.
		frappe.throw("distribute_combo_price: split does not sum to the combo price.")

	return [u / scale for u in units]
