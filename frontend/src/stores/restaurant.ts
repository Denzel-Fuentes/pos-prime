// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { call } from 'frappe-ui'
import type {
  CartItem,
  DailyMenuGroup,
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

/** One slot's choice for preview_combo/create_restaurant_sale.
 * notes/modifiers are UI-only — _resolve_combo_selection (see
 * pos_prime/api/restaurant.py) only reads slot_idx/item_code and ignores
 * the rest, so extending this shape needs no backend change. */
export interface ComboSlotSelection {
  slot_idx: number
  item_code: string
  notes?: string
  modifiers?: { modifier: string; label: string }[]
  /** Per-component destination — a customer can eat the segundo at a table
   * and take the sopa away. Falls back to the combo-wide destination. */
  destination?: RestaurantDestination
}

export const useRestaurantStore = defineStore('restaurant', () => {
  const config = ref<RestaurantConfig | null>(null)
  const loading = ref(false)
  // "Platos del dia" candidates for the OpenShift picker — fetched
  // independently of `config`, since OpenShift runs before a POS
  // session/shift exists (fetchConfig is only called once one does).
  const dailyMenuCandidates = ref<DailyMenuGroup[]>([])

  const enabled = computed(() => config.value?.settings.enable_restaurant_mode ?? false)
  const combos = computed(() => config.value?.combos ?? [])
  const modifierGroups = computed(() => config.value?.modifier_groups ?? [])
  const hasPrinter = computed(() => config.value?.has_printer ?? false)
  const hasReceiptPrinter = computed(() => config.value?.has_receipt_printer ?? false)
  const comboStripLabel = computed(() => config.value?.settings.combo_strip_label || __('Combos'))
  const labelDineIn = computed(() => config.value?.settings.label_dine_in || 'MESA')
  const labelTakeaway = computed(() => config.value?.settings.label_takeaway || 'PARA LLEVAR')
  const disableCouponCode = computed(() => config.value?.settings.disable_coupon_code ?? false)
  const disableMoreOptions = computed(() => config.value?.settings.disable_more_options ?? false)
  // Defaults to true (hidden) — matches the doctype default, and keeps the
  // behavior stable against a backend that predates the field.
  const hideCategorySearch = computed(() => Boolean(config.value?.settings.hide_category_search ?? true))
  const hasDailyMenu = computed(() => dailyMenuCandidates.value.length > 0)

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

  /** Called from OpenShift.vue once a POS Profile is picked, ahead of any
   * shift existing — separate from fetchConfig for that reason. Resets to
   * empty (not left stale) so switching profiles before opening doesn't
   * leave a previous profile's picker showing. */
  async function fetchDailyMenuCandidates(posProfile: string) {
    if (!posProfile) {
      dailyMenuCandidates.value = []
      return
    }
    try {
      const data = await call('pos_prime.api.restaurant.get_daily_menu_candidates', {
        pos_profile: posProfile,
      })
      dailyMenuCandidates.value = data?.groups || []
    } catch {
      dailyMenuCandidates.value = []
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
    selections: ComboSlotSelection[]
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

  /** Normalized key for one slot selection — used to compare a
   * newly-built selection against an existing cart instance's lines,
   * ignoring array order. */
  function selectionKey(
    slotIdx: number,
    itemCode: string,
    notes?: string | null,
    modifiers?: { modifier: string; label: string }[],
    destination?: RestaurantDestination | null
  ): string {
    return JSON.stringify({
      slot_idx: slotIdx,
      item_code: itemCode,
      notes: notes || null,
      modifiers: (modifiers || []).map((m) => m.modifier).sort(),
      destination: destination || null,
    })
  }

  /** Finds an existing cart instance of the same combo whose instance-wide
   * note and every per-slot selection (item/notes/modifiers/destination)
   * exactly match what's about to be added — so re-adding an identical
   * Completo bumps its qty instead of creating a visually redundant
   * duplicate group. Any difference (a swapped slot item, a different
   * note, one component sent to the table) is treated as a distinct
   * instance, never merged. */
  function findMatchingInstance(
    items: CartItem[],
    comboName: string,
    destination: RestaurantDestination,
    selections: ComboSlotSelection[],
    comboNotes?: string
  ): string | null {
    const wanted = selections
      .map((s) => selectionKey(s.slot_idx, s.item_code, s.notes, s.modifiers, s.destination || destination))
      .sort()
      .join('|')

    const groups = new Map<string, CartItem[]>()
    for (const item of items) {
      if (item.combo_uid && item.combo === comboName) {
        const list = groups.get(item.combo_uid) || []
        list.push(item)
        groups.set(item.combo_uid, list)
      }
    }

    for (const [uid, lines] of groups) {
      if ((lines[0].combo_notes || null) !== (comboNotes || null)) continue
      const actual = lines
        .map((l) =>
          selectionKey(l.combo_slot_idx ?? -1, l.item_code, l.notes, l.modifiers, l.destination)
        )
        .sort()
        .join('|')
      if (actual === wanted) return uid
    }
    return null
  }

  /** Resolve a combo instance's chosen items into priced cart lines and
   * push them atomically. Rates come from the server preview — never
   * computed client-side, matching pricing.py's "backend is authoritative"
   * design. Notes/modifiers are per component and never touch pricing —
   * _resolve_combo_selection only reads slot_idx/item_code from each
   * selection and ignores the rest, so they ride along untouched.
   *
   * If an identical instance (same combo, destination, and per-slot
   * selections) is already in the cart, this bumps its qty instead of
   * adding a new group — see findMatchingInstance. */
  async function addComboToCart(
    combo: RestaurantCombo,
    posProfile: string,
    selections: ComboSlotSelection[],
    destination: RestaurantDestination,
    comboNotes?: string
  ): Promise<string | null> {
    const cartStore = useCartStore()
    const itemsStore = useItemsStore()

    const existingUid = findMatchingInstance(cartStore.items, combo.name, destination, selections, comboNotes)
    if (existingUid) {
      const currentQty = cartStore.items.find((i) => i.combo_uid === existingUid)?.qty ?? 1
      cartStore.updateComboInstanceQty(existingUid, currentQty + 1)
      return existingUid
    }

    const preview = await previewCombo(combo.name, posProfile, selections)
    const selectionsBySlot = new Map(selections.map((s) => [s.slot_idx, s]))

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
        const selection = selectionsBySlot.get(comp.slot_idx)
        return makeCartItem(catalogItem, {
          rate: comp.rate,
          amount: comp.rate,
          destination: selection?.destination || destination,
          combo_uid: comboUid,
          combo: combo.name,
          combo_label: `${label} · ${comp.slot_label}`,
          combo_slot_label: comp.slot_label,
          combo_slot_idx: comp.slot_idx,
          notes: selection?.notes || null,
          modifiers: selection?.modifiers || [],
          combo_notes: comboNotes || null,
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
    dailyMenuCandidates.value = []
  }

  return {
    config,
    loading,
    enabled,
    combos,
    modifierGroups,
    hasPrinter,
    hasReceiptPrinter,
    comboStripLabel,
    labelDineIn,
    labelTakeaway,
    disableCouponCode,
    disableMoreOptions,
    hideCategorySearch,
    dailyMenuCandidates,
    hasDailyMenu,
    defaultDestination,
    setDefaultDestination,
    fetchConfig,
    fetchDailyMenuCandidates,
    fetchComboOptions,
    previewCombo,
    addComboToCart,
    modifierGroupsForItem,
    $reset,
  }
})
