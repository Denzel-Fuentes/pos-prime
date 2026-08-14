<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRestaurantStore } from '@/stores/restaurant'
import { useItemsStore } from '@/stores/items'
import { usePosSessionStore } from '@/stores/posSession'
import { useCurrency } from '@/composables/useCurrency'
import { X, Check, UtensilsCrossed, StickyNote, ListPlus } from 'lucide-vue-next'
import NoteDialog from './NoteDialog.vue'
import ModifierPicker from './ModifierPicker.vue'
import VariantPickerDialog from '@/components/items/VariantPickerDialog.vue'
import type { Item, RestaurantCombo, RestaurantComboSlotOption, RestaurantDestination } from '@/types'

const props = defineProps<{
  combo: RestaurantCombo
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()

const restaurantStore = useRestaurantStore()
const itemsStore = useItemsStore()
const sessionStore = usePosSessionStore()
const { formatCurrency } = useCurrency()

const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const slots = ref<RestaurantComboSlotOption[]>([])
const selections = ref<Record<number, string>>({})
const destination = ref<RestaurantDestination>(restaurantStore.defaultDestination)
// Per-slot notes/modifiers, kept as maps parallel to `selections` (keyed
// by slot_idx) rather than folded into it, so canConfirm and the
// default_item pre-seed don't need to change shape.
const slotNotes = ref<Record<number, string>>({})
const slotModifiers = ref<Record<number, { modifier: string; label: string }[]>>({})
// Per-slot destination override. Empty means "follow the combo-wide
// toggle" — set only when the customer splits the combo (segundo at the
// table, sopa to take away), which the header toggle then resets.
const slotDestinations = ref<Record<number, RestaurantDestination>>({})
const comboNotes = ref('')
const modifierDialogSlot = ref<number | null>(null)
const showComboNoteDialog = ref(false)
// When a slot option is a template (has_variants), clicking it opens this
// picker instead of selecting it directly. selectionTemplates/Names track,
// per slot, which template + variant name produced the current selection —
// `selections` itself always holds the concrete (sellable) item_code.
const variantPickerSlot = ref<{ slotIdx: number; templateItem: Item } | null>(null)
const selectionTemplates = ref<Record<number, string>>({})
const selectionVariantNames = ref<Record<number, string>>({})

onMounted(async () => {
  loading.value = true
  try {
    const options = await restaurantStore.fetchComboOptions(props.combo.name, sessionStore.posProfile)
    slots.value = options.slots
    for (const slot of slots.value) {
      if (slot.default_item) selections.value[slot.slot_idx] = slot.default_item
    }
  } catch (e: any) {
    error.value = e?.message || __('Failed to load combo options')
  } finally {
    loading.value = false
  }
})

function itemsForSlot(slot: RestaurantComboSlotOption) {
  // A slot draws from an Item Group, from explicitly listed items, or both
  // — mirrors _slot_eligible_items in pos_prime/api/restaurant.py, which
  // validates the same thing at sale time.
  return itemsStore.allItems.filter(
    (item) =>
      slot.eligible_groups.includes(item.item_group) ||
      (slot.eligible_items || []).includes(item.item_code)
  )
}

function slotDestination(slotIdx: number): RestaurantDestination {
  return slotDestinations.value[slotIdx] || destination.value
}

function setSlotDestination(slotIdx: number, dest: RestaurantDestination) {
  slotDestinations.value[slotIdx] = dest
}

/** The header toggle is the "whole combo goes here" control — it drops any
 * per-slot override rather than leaving overridden slots silently behind. */
function setComboDestination(dest: RestaurantDestination) {
  destination.value = dest
  slotDestinations.value = {}
}

function selectForSlot(slotIdx: number, itemCode: string) {
  if (selections.value[slotIdx] === itemCode) return
  selections.value[slotIdx] = itemCode
  // Modifiers are specific to the previously selected item — clear them
  // (and the note, since it's usually about the dish that just changed)
  // rather than carry them over to the new item.
  delete slotNotes.value[slotIdx]
  delete slotModifiers.value[slotIdx]
}

function isSlotOptionSelected(slotIdx: number, item: Item): boolean {
  if (item.has_variants) return selectionTemplates.value[slotIdx] === item.item_code
  return selections.value[slotIdx] === item.item_code
}

function onSlotItemClick(slotIdx: number, item: Item) {
  if (item.has_variants) {
    variantPickerSlot.value = { slotIdx, templateItem: item }
    return
  }
  selectForSlot(slotIdx, item.item_code)
  delete selectionTemplates.value[slotIdx]
  delete selectionVariantNames.value[slotIdx]
}

function onSlotVariantPicked(variant: Item) {
  const target = variantPickerSlot.value
  if (!target) return
  selectForSlot(target.slotIdx, variant.item_code)
  selectionTemplates.value[target.slotIdx] = target.templateItem.item_code
  selectionVariantNames.value[target.slotIdx] = variant.item_name
  variantPickerSlot.value = null
}

const canConfirm = computed(
  () => slots.value.length > 0 && slots.value.every((s) => !!selections.value[s.slot_idx])
)

// Notes and modifiers are unified behind one dialog per slot — see
// ModifierPicker's manual text box alongside its predefined chips.
function onSaveSlotModifiers(payload: { modifiers: { modifier: string; label: string }[]; notes: string }) {
  if (modifierDialogSlot.value === null) return
  const slotIdx = modifierDialogSlot.value
  if (payload.modifiers.length) slotModifiers.value[slotIdx] = payload.modifiers
  else delete slotModifiers.value[slotIdx]
  if (payload.notes) slotNotes.value[slotIdx] = payload.notes
  else delete slotNotes.value[slotIdx]
  modifierDialogSlot.value = null
}

function slotSummary(slotIdx: number): string {
  const parts: string[] = []
  if (slotNotes.value[slotIdx]) parts.push(slotNotes.value[slotIdx])
  if (slotModifiers.value[slotIdx]?.length) parts.push(...slotModifiers.value[slotIdx].map((m) => m.label))
  return parts.length ? parts.join(', ') : __('Modifiers')
}

function onSaveComboNote(notes: string) {
  comboNotes.value = notes.trim()
  showComboNoteDialog.value = false
}

async function confirm() {
  if (!canConfirm.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const selectionList = slots.value.map((s) => ({
      slot_idx: s.slot_idx,
      item_code: selections.value[s.slot_idx],
      notes: slotNotes.value[s.slot_idx] || undefined,
      modifiers: slotModifiers.value[s.slot_idx]?.length ? slotModifiers.value[s.slot_idx] : undefined,
      destination: slotDestination(s.slot_idx),
    }))
    const comboUid = await restaurantStore.addComboToCart(
      props.combo,
      sessionStore.posProfile,
      selectionList,
      destination.value,
      comboNotes.value || undefined
    )
    if (comboUid) {
      emit('confirm')
    } else {
      error.value = __('Could not add the combo — one or more items are no longer available.')
    }
  } catch (e: any) {
    error.value = e?.message || __('Failed to add combo')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    :aria-label="combo.combo_name"
    @keydown.escape="emit('close')"
  >
    <div class="absolute inset-0 bg-black/30 dark:bg-black/50" @click="emit('close')" />
    <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl dark:shadow-black/30 w-full max-w-lg max-h-[85vh] overflow-y-auto">
      <div class="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center justify-between rounded-t-xl z-10">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center shrink-0">
            <UtensilsCrossed :size="16" class="text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
              {{ combo.print_label || combo.combo_name }}
            </h3>
            <p class="text-xs font-bold text-amber-600 dark:text-amber-400">
              {{ formatCurrency(combo.combo_price) }}
            </p>
          </div>
        </div>
        <button @click="emit('close')" class="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
          <X :size="18" />
        </button>
      </div>

      <div class="p-4 space-y-4">
        <div v-if="loading" class="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
          {{ __('Loading...') }}
        </div>

        <template v-else>
          <!-- Destination + instance note -->
          <div class="flex items-center gap-1.5">
            <div class="flex flex-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
              <button
                v-for="dest in restaurantStore.config?.destinations || ['Mesa', 'Para llevar']"
                :key="dest"
                @click="setComboDestination(dest as RestaurantDestination)"
                class="flex-1 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide transition-colors"
                :class="
                  destination === dest
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400'
                "
              >
                {{ dest === 'Mesa' ? restaurantStore.labelDineIn : restaurantStore.labelTakeaway }}
              </button>
            </div>
            <button
              @click="showComboNoteDialog = true"
              :aria-label="__('Combo note')"
              class="shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
              :class="comboNotes
                ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'"
            >
              <StickyNote :size="13" />
              <span class="max-w-[90px] truncate">{{ comboNotes || __('Note') }}</span>
            </button>
          </div>

          <!-- Slots -->
          <div v-for="slot in slots" :key="slot.slot_idx">
            <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
              {{ slot.slot_label }}
            </h4>
            <div v-if="itemsForSlot(slot).length === 0" class="text-xs text-gray-400 dark:text-gray-500 py-2">
              {{ __('No items available for this slot') }}
            </div>
            <div v-else class="grid grid-cols-2 gap-1.5">
              <button
                v-for="item in itemsForSlot(slot)"
                :key="item.item_code"
                @click="onSlotItemClick(slot.slot_idx, item)"
                class="text-left px-3 py-2 rounded-lg border text-sm transition-colors"
                :class="
                  isSlotOptionSelected(slot.slot_idx, item)
                    ? 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 font-medium'
                    : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                "
              >
                {{ item.item_name }}
                <span v-if="item.has_variants && selectionVariantNames[slot.slot_idx] && isSlotOptionSelected(slot.slot_idx, item)" class="block text-xs font-normal opacity-80">
                  {{ selectionVariantNames[slot.slot_idx] }}
                </span>
              </button>
            </div>

            <!-- Per-component destination + notes/modifiers (unified into
                 one dialog), once a selection exists -->
            <div v-if="selections[slot.slot_idx]" class="flex flex-wrap items-center gap-1 mt-1.5">
              <div class="inline-flex rounded bg-gray-100 dark:bg-gray-800 p-0.5">
                <button
                  v-for="dest in restaurantStore.config?.destinations || ['Mesa', 'Para llevar']"
                  :key="dest"
                  @click="setSlotDestination(slot.slot_idx, dest as RestaurantDestination)"
                  class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide transition-colors"
                  :class="
                    slotDestination(slot.slot_idx) === dest
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-400 dark:text-gray-500'
                  "
                >
                  {{ dest === 'Mesa' ? restaurantStore.labelDineIn : restaurantStore.labelTakeaway }}
                </button>
              </div>
              <button
                @click="modifierDialogSlot = slot.slot_idx"
                :aria-label="__('Modifiers')"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium max-w-[200px] transition-colors"
                :class="(slotModifiers[slot.slot_idx]?.length || slotNotes[slot.slot_idx])
                  ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'"
              >
                <ListPlus :size="10" class="shrink-0" />
                <span class="truncate">{{ slotSummary(slot.slot_idx) }}</span>
              </button>
            </div>
          </div>

          <p v-if="error" class="text-xs text-red-600 dark:text-red-400">{{ error }}</p>
        </template>

        <button
          @click="confirm"
          :disabled="!canConfirm || submitting"
          class="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          <Check :size="16" />
          {{ submitting ? __('Adding...') : __('Add to Cart') }}
        </button>
      </div>
    </div>

    <!-- Variant picker for slot options that are templates -->
    <VariantPickerDialog
      v-if="variantPickerSlot"
      :item="variantPickerSlot.templateItem"
      @select="onSlotVariantPicked"
      @close="variantPickerSlot = null"
    />

    <!-- Per-component modifier picker (also carries the manual note box) -->
    <ModifierPicker
      v-if="modifierDialogSlot !== null"
      :key="selections[modifierDialogSlot]"
      :item-code="selections[modifierDialogSlot]"
      :item-name="slots.find((s) => s.slot_idx === modifierDialogSlot)?.slot_label || ''"
      :model-value="{ modifiers: slotModifiers[modifierDialogSlot] || [], notes: slotNotes[modifierDialogSlot] || null }"
      :allow-groups="slots.find((s) => s.slot_idx === modifierDialogSlot)?.allow_modifiers ?? true"
      @confirm="onSaveSlotModifiers"
      @close="modifierDialogSlot = null"
    />

    <!-- Instance-wide combo note dialog -->
    <NoteDialog
      v-if="showComboNoteDialog"
      :item-name="combo.print_label || combo.combo_name"
      :model-value="comboNotes || null"
      @confirm="onSaveComboNote"
      @close="showComboNoteDialog = false"
    />
  </div>
</template>
