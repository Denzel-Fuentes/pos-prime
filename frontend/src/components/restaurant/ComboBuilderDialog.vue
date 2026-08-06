<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRestaurantStore } from '@/stores/restaurant'
import { useItemsStore } from '@/stores/items'
import { usePosSessionStore } from '@/stores/posSession'
import { useCurrency } from '@/composables/useCurrency'
import { X, Check, UtensilsCrossed } from 'lucide-vue-next'
import type { RestaurantCombo, RestaurantComboSlotOption, RestaurantDestination } from '@/types'

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
  return itemsStore.allItems.filter((item) => slot.eligible_groups.includes(item.item_group))
}

function selectForSlot(slotIdx: number, itemCode: string) {
  selections.value[slotIdx] = itemCode
}

const canConfirm = computed(
  () => slots.value.length > 0 && slots.value.every((s) => !!selections.value[s.slot_idx])
)

async function confirm() {
  if (!canConfirm.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const selectionList = slots.value.map((s) => ({
      slot_idx: s.slot_idx,
      item_code: selections.value[s.slot_idx],
    }))
    const comboUid = await restaurantStore.addComboToCart(
      props.combo,
      sessionStore.posProfile,
      selectionList,
      destination.value
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
          <!-- Destination -->
          <div class="flex rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
            <button
              v-for="dest in restaurantStore.config?.destinations || ['Mesa', 'Para llevar']"
              :key="dest"
              @click="destination = dest as RestaurantDestination"
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
                @click="selectForSlot(slot.slot_idx, item.item_code)"
                class="text-left px-3 py-2 rounded-lg border text-sm transition-colors"
                :class="
                  selections[slot.slot_idx] === item.item_code
                    ? 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 font-medium'
                    : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                "
              >
                {{ item.item_name }}
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
  </div>
</template>
