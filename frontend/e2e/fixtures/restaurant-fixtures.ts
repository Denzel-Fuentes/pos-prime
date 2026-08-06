import { test as base, expect } from './pos-fixtures'
import type { FrappeAPI } from './frappe-api'

export interface RestaurantComboSlotData {
  slotIdx: number
  slotLabel: string
  itemCode: string
  itemName: string
}

export interface RestaurantTestData {
  enabled: boolean
  combo: {
    name: string
    printLabel: string
    price: number
    slots: RestaurantComboSlotData[]
  } | null
  modifierName: string | null
  modifierLabel: string | null
}

/**
 * Extends pos-fixtures with restaurant-module test data, discovered from
 * whatever already exists on the site (same philosophy as testData in
 * pos-fixtures.ts: pick real data rather than assume fixtures were
 * seeded). A site with restaurant mode off, or with a combo whose slots
 * have no matching items, yields enabled: false / combo: null — tests
 * are expected to test.skip() on that rather than fail.
 */
export const test = base.extend<{ restaurantData: RestaurantTestData }>({
  restaurantData: async ({ api, testData }, use) => {
    await use(await discoverRestaurantData(api, testData.posProfile))
  },
})

export { expect }

let _cached: RestaurantTestData | null = null

async function discoverRestaurantData(api: FrappeAPI, posProfile: string): Promise<RestaurantTestData> {
  if (_cached) return _cached

  const settings = await api.getDoc('Restaurant Settings', 'Restaurant Settings')
  if (!settings?.enable_restaurant_mode) {
    _cached = { enabled: false, combo: null, modifierName: null, modifierLabel: null }
    return _cached
  }

  const combo = await findUsableCombo(api, posProfile)

  let modifierName: string | null = null
  let modifierLabel: string | null = null
  const groups = await api.getList('Restaurant Modifier Group', { disabled: 0 }, ['name'], 5)
  for (const group of groups) {
    const rows = await api.getList('Restaurant Modifier Group Modifier', { parent: group.name }, ['modifier'], 1)
    if (!rows.length) continue
    const modifier = await api.getDoc('Restaurant Modifier', rows[0].modifier)
    if (modifier) {
      modifierName = modifier.name
      modifierLabel = modifier.print_label || modifier.modifier_name
      break
    }
  }

  _cached = { enabled: true, combo, modifierName, modifierLabel }
  return _cached
}

/** First enabled combo whose every slot resolves to at least one real,
 * enabled Item — skips a combo defined with an empty/misconfigured
 * item group rather than letting the whole suite fail on it. */
async function findUsableCombo(api: FrappeAPI, posProfile: string) {
  const combos = await api.getList(
    'Restaurant Combo',
    { disabled: 0 },
    ['name', 'print_label', 'combo_name', 'combo_price'],
    5
  )
  for (const combo of combos) {
    const options = await api.call('pos_prime.api.restaurant.get_combo_options', {
      combo: combo.name,
      pos_profile: posProfile,
    })
    const slots: RestaurantComboSlotData[] = []
    for (const slot of options.slots) {
      const items = await api.getList(
        'Item',
        { item_group: ['in', slot.eligible_groups], disabled: 0 },
        ['item_code', 'item_name'],
        1
      )
      if (!items.length) break
      slots.push({
        slotIdx: slot.slot_idx,
        slotLabel: slot.slot_label,
        itemCode: items[0].item_code,
        itemName: items[0].item_name,
      })
    }
    if (slots.length > 0 && slots.length === options.slots.length) {
      return {
        name: combo.name,
        printLabel: combo.print_label || combo.combo_name,
        price: combo.combo_price,
        slots,
      }
    }
  }
  return null
}
