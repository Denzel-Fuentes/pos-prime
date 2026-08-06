// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { call } from 'frappe-ui'
import type {
  RestaurantConfig,
  RestaurantCombo,
  RestaurantComboSlotOption,
  RestaurantDestination,
  RestaurantModifierGroup,
} from '@/types'
import { useCartStore } from '@/stores/cart'
import { useItemsStore } from '@/stores/items'
import { makeCartItem } from '@/utils/cartPayload'
import { newUid } from '@/utils/uid'

export const useRestaurantStore = defineStore('restaurant', () => {
  const config = ref<RestaurantConfig | null>(null)
  const loading = ref(false)

  const enabled = computed(() => config.value?.settings.enable_restaurant_mode ?? false)
  const combos = computed(() => config.value?.combos ?? [])
  const modifierGroups = computed(() => config.value?.modifier_groups ?? [])
  const hasPrinter = computed(() => config.value?.has_printer ?? false)
  const comboStripLabel = computed(() => config.value?.settings.combo_strip_label || __('Combos'))
  const labelDineIn = computed(() => config.value?.settings.label_dine_in || 'MESA')
  const labelTakeaway = computed(() => config.value?.settings.label_takeaway || 'PARA LLEVAR')

  // UI-selected default for newly added lines (Phase 4 adds the header
  // toggle that writes this and persists it to localStorage). Falls back
  // to Restaurant Settings' own default, then "Mesa".
  const defaultDestination = ref<RestaurantDestination>(
    (localStorage.getItem('pos_restaurant_destination') as RestaurantDestination | null) || 'Mesa'
  )

  function setDefaultDestination(destination: RestaurantDestination) {
    defaultDestination.value = destination
    localStorage.setItem('pos_restaurant_destination', destination)
  }

  async function fetchConfig(posProfile: string) {
    loading.value = true
    try {
      const data = await call('pos_prime.api.restaurant.get_restaurant_config', {
        pos_profile: posProfile,
      })
      config.value = data as RestaurantConfig
      if (data?.settings?.default_destination) {
        defaultDestination.value = data.settings.default_destination
      }
      return config.value
    } finally {
      loading.value = false
    }
  }

  async function fetchComboOptions(combo: string, posProfile: string): Promise<{
    combo: string
    combo_name: string
    combo_price: number
    currency: string
    print_label: string | null
    slots: RestaurantComboSlotOption[]
  }> {
    return await call('pos_prime.api.restaurant.get_combo_options', {
      combo,
      pos_profile: posProfile,
    })
  }

  async function previewCombo(
    combo: string,
    posProfile: string,
    selections: { slot_idx: number; item_code: string }[]
  ): Promise<{
    combo: string
    combo_price: number
    components: { item_code: string; slot_idx: number; slot_label: string; list_rate: number; rate: number }[]
  }> {
    return await call('pos_prime.api.restaurant.preview_combo', {
      combo,
      pos_profile: posProfile,
      selections,
    })
  }

  /** Resolve a combo instance's chosen items into priced cart lines and
   * push them atomically. Rates come from the server preview — never
   * computed client-side, matching pricing.py's "backend is authoritative"
   * design. */
  async function addComboToCart(
    combo: RestaurantCombo,
    posProfile: string,
    selections: { slot_idx: number; item_code: string }[],
    destination: RestaurantDestination
  ): Promise<string | null> {
    const cartStore = useCartStore()
    const itemsStore = useItemsStore()

    const preview = await previewCombo(combo.name, posProfile, selections)

    const comboUid = newUid()
    const existingInstances = new Set(
      cartStore.items.filter((i) => i.combo === combo.name).map((i) => i.combo_uid)
    ).size
    const instanceNo = existingInstances + 1
    const label = `${combo.print_label || combo.combo_name} #${instanceNo}`

    const lines = preview.components
      .map((comp) => {
        const catalogItem = itemsStore.allItems.find((it) => it.item_code === comp.item_code)
        if (!catalogItem) {
          console.error(`addComboToCart: ${comp.item_code} not found in the loaded catalog`)
          return null
        }
        return makeCartItem(catalogItem, {
          rate: comp.rate,
          amount: comp.rate,
          destination,
          combo_uid: comboUid,
          combo: combo.name,
          combo_label: `${label} · ${comp.slot_label}`,
          combo_slot_label: comp.slot_label,
          combo_slot_idx: comp.slot_idx,
        })
      })
      .filter((line) => line !== null)

    if (lines.length !== preview.components.length) {
      return null // one or more components couldn't be resolved — don't add a partial combo
    }

    cartStore.addComboLines(lines)
    return comboUid
  }

  /** Modifier groups applicable to one catalog item — by direct item match,
   * item-group match, or "apply to all items". Looks the item's group up
   * from the already-loaded catalog rather than requiring callers (CartItem,
   * ModifierPicker) to plumb it through. */
  function modifierGroupsForItem(itemCode: string): RestaurantModifierGroup[] {
    const itemsStore = useItemsStore()
    const itemGroup = itemsStore.allItems.find((i) => i.item_code === itemCode)?.item_group
    return modifierGroups.value.filter(
      (g) =>
        g.apply_to_all_items ||
        (itemGroup && g.item_groups?.includes(itemGroup)) ||
        g.items?.includes(itemCode)
    )
  }

  function $reset() {
    config.value = null
    loading.value = false
  }

  return {
    config,
    loading,
    enabled,
    combos,
    modifierGroups,
    hasPrinter,
    comboStripLabel,
    labelDineIn,
    labelTakeaway,
    defaultDestination,
    setDefaultDestination,
    fetchConfig,
    fetchComboOptions,
    previewCombo,
    addComboToCart,
    modifierGroupsForItem,
    $reset,
  }
})
