// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

/**
 * Single source of truth for turning a catalog Item / server InvoiceItem
 * into a CartItem, and for turning a CartItem back into the various
 * payload shapes the backend and the customer display expect.
 *
 * Before this file existed, the same ~18-field item shape was hand-written
 * in five different places (checkout, self-checkout, hold-order, tax
 * calculation, customer display) and drifted — e.g. hold-order silently
 * sent only 8 of those fields. Route every call site through here instead
 * of writing a new object literal.
 */

import type { CartItem, Item, InvoiceItem } from '@/types'
import { newUid } from './uid'

/** Shape of a free item as returned by pos_prime.api.taxes.calculate_taxes
 * (its "free_items" array — see pos_prime/api/taxes.py). */
export interface FreeItemData {
  item_code: string
  item_name: string
  qty: number
  rate: number
  amount: number
  uom: string
  stock_uom: string
  pricing_rules?: string | null
}

/** Build a fresh CartItem from a catalog Item. `overrides` is applied last,
 * so callers can set qty/batch_no/serial_no/etc. atomically at creation
 * time instead of pushing then mutating by index. */
export function makeCartItem(item: Item, overrides: Partial<CartItem> = {}): CartItem {
  return {
    uid: newUid(),
    item_code: item.item_code,
    item_name: item.item_name,
    rate: item.rate,
    qty: 1,
    amount: item.rate,
    uom: item.stock_uom,
    discount_percentage: 0,
    discount_amount: 0,
    image: item.image,
    stock_uom: item.stock_uom,
    has_serial_no: item.has_serial_no,
    has_batch_no: item.has_batch_no,
    serial_no: null,
    batch_no: null,
    serial_and_batch_bundle: null,
    conversion_factor: 1,
    item_tax_template: item.item_tax_template || null,
    margin_type: null,
    margin_rate_or_amount: 0,
    description: item.description || null,
    project: null,
    weight_per_unit: item.weight_per_unit || null,
    weight_uom: item.weight_uom || null,
    combo_uid: null,
    combo: null,
    combo_label: null,
    combo_slot_label: null,
    combo_slot_idx: null,
    destination: null,
    notes: null,
    modifiers: [],
    ...overrides,
  }
}

/** Build a free CartItem line from a pricing-rule "Buy X Get Y" result.
 * Kept separate from makeCartItem because the source shape (FreeItemData)
 * is a narrow API response, not a catalog Item. */
export function makeFreeCartItem(fi: FreeItemData, overrides: Partial<CartItem> = {}): CartItem {
  return {
    uid: newUid(),
    item_code: fi.item_code,
    item_name: fi.item_name,
    rate: fi.rate || 0,
    qty: fi.qty,
    amount: fi.amount || 0,
    uom: fi.uom || fi.stock_uom || '',
    discount_percentage: 0,
    discount_amount: 0,
    image: null,
    stock_uom: fi.stock_uom || fi.uom || '',
    has_serial_no: false,
    has_batch_no: false,
    serial_no: null,
    batch_no: null,
    serial_and_batch_bundle: null,
    conversion_factor: 1,
    item_tax_template: null,
    margin_type: null,
    margin_rate_or_amount: 0,
    description: null,
    project: null,
    weight_per_unit: null,
    weight_uom: null,
    is_free_item: true,
    pricing_rules: fi.pricing_rules || null,
    price_list_rate: null,
    ...overrides,
  }
}

/** Reconstruct a CartItem from a server InvoiceItem (draft resume). Gets a
 * brand-new uid — resumed lines don't need continuity with whatever uid
 * they had before the draft was held. */
export function fromInvoiceItem(item: InvoiceItem, overrides: Partial<CartItem> = {}): CartItem {
  return {
    uid: newUid(),
    item_code: item.item_code,
    item_name: item.item_name,
    rate: item.rate,
    qty: item.qty,
    amount: item.amount ?? item.rate * item.qty,
    uom: item.uom || '',
    discount_percentage: item.discount_percentage || 0,
    discount_amount: item.discount_amount || 0,
    image: null,
    stock_uom: item.stock_uom || item.uom || '',
    has_serial_no: !!item.serial_no,
    has_batch_no: !!item.batch_no,
    serial_no: item.serial_no || null,
    batch_no: item.batch_no || null,
    serial_and_batch_bundle: item.serial_and_batch_bundle || null,
    conversion_factor: item.conversion_factor || 1,
    item_tax_template: item.item_tax_template || null,
    margin_type: item.margin_type || null,
    margin_rate_or_amount: item.margin_rate_or_amount || 0,
    description: item.description || null,
    project: item.project || null,
    weight_per_unit: item.weight_per_unit || null,
    weight_uom: item.weight_uom || null,
    combo_uid: item.combo_uid || null,
    combo: item.combo || null,
    combo_label: item.combo_label || null,
    combo_slot_idx: item.combo_slot_idx ?? null,
    destination: item.destination || null,
    notes: item.notes || null,
    modifiers: (item.modifiers || []).map((name) => ({ modifier: name, label: name })),
    ...overrides,
  }
}

/** Full item payload for create_pos_invoice / save_draft_invoice /
 * update_and_submit_draft — anywhere a real POS Invoice Item gets built.
 * `line_uid` rides along so the backend can echo it back once
 * pos_prime_line_uid exists (harmless no-op until then — build_item_dict
 * is a strict allowlist and silently drops unknown keys). */
export function toPayloadItem(item: CartItem) {
  return {
    line_uid: item.uid,
    item_code: item.item_code,
    qty: item.qty,
    rate: item.rate,
    discount_percentage: item.discount_percentage,
    discount_amount: item.discount_amount || undefined,
    serial_no: item.serial_no || undefined,
    batch_no: item.batch_no || undefined,
    serial_and_batch_bundle: item.serial_and_batch_bundle || undefined,
    uom: item.uom || undefined,
    conversion_factor: item.conversion_factor || 1,
    item_tax_template: item.item_tax_template || undefined,
    margin_type: item.margin_type || undefined,
    margin_rate_or_amount: item.margin_rate_or_amount || undefined,
    description: item.description || undefined,
    project: item.project || undefined,
    weight_per_unit: item.weight_per_unit || undefined,
    weight_uom: item.weight_uom || undefined,
    combo_uid: item.combo_uid || undefined,
    combo: item.combo || undefined,
    combo_label: item.combo_label || undefined,
    combo_slot_label: item.combo_slot_label || undefined,
    combo_slot_idx: item.combo_slot_idx ?? undefined,
    destination: item.destination || undefined,
    notes: item.notes || undefined,
    modifiers: item.modifiers?.length ? item.modifiers.map((m) => m.modifier) : undefined,
  }
}

/** Narrower item payload for pos_prime.api.taxes.calculate_taxes — that
 * endpoint builds its own item dict server-side (deliberately not
 * build_item_dict, see pos_prime/api/taxes.py) and only reads this subset.
 * Keep the two in sync or the previewed total can diverge from the
 * submitted one. */
export function toTaxPayloadItem(item: CartItem) {
  return {
    line_uid: item.uid,
    item_code: item.item_code,
    qty: item.qty,
    rate: item.rate,
    discount_percentage: item.discount_percentage,
    discount_amount: item.discount_amount || 0,
    serial_no: item.serial_no || '',
    batch_no: item.batch_no || '',
    uom: item.uom || '',
    conversion_factor: item.conversion_factor || 1,
    item_tax_template: item.item_tax_template || '',
    margin_type: item.margin_type || '',
    margin_rate_or_amount: item.margin_rate_or_amount || 0,
    // Lets calculate_taxes skip pricing-rule re-evaluation on combo
    // components (their rate is fixed by distribute_combo_price) — see
    // pos_prime/api/taxes.py.
    combo_uid: item.combo_uid || undefined,
  }
}

/** Minimal item shape broadcast to the customer-facing pole display. */
export function toDisplayItem(item: CartItem) {
  return {
    item_name: item.item_name,
    qty: item.qty,
    rate: item.rate,
    amount: item.amount,
    is_free_item: item.is_free_item || false,
    pricing_rules: item.pricing_rules || null,
    price_list_rate: item.price_list_rate ?? null,
    discount_percentage: item.discount_percentage || 0,
    discount_amount: item.discount_amount || 0,
  }
}
