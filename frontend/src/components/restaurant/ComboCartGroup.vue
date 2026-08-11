<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { computed } from 'vue'
import { UtensilsCrossed, Trash2, StickyNote, Minus, Plus, ShoppingBag } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'
import { useRestaurantStore } from '@/stores/restaurant'
import { useTouchDevice } from '@/composables/useTouchDevice'
import CartItemComp from './../cart/CartItem.vue'
import type { CartItem } from '@/types'

const props = defineProps<{
  comboUid: string
  label: string
  price: number
  destination?: string | null
  notes?: string | null
  lines: { index: number; item: CartItem }[]
  selectedIndex: number | null
}>()

const emit = defineEmits<{
  select: [index: number]
  removeInstance: [comboUid: string]
  updateQty: [comboUid: string, qty: number]
  toggleDestination: [comboUid: string]
  editModifiers: [index: number]
  editComboNotes: [comboUid: string]
}>()

const restaurantStore = useRestaurantStore()
const { formatCurrency } = useCurrency()
const { isTouchDevice } = useTouchDevice()

// Header row is the tightest horizontal space in the redesign (label +
// destination + note + qty stepper + price + delete, all in one row), so
// on touch we use 36px controls rather than the full 44px floor used
// elsewhere — a documented exception for this once-per-instance row.

// Every line of an instance shares the same qty (see
// cartStore.updateComboInstanceQty) — any line's qty represents the
// whole instance's.
const qty = computed(() => props.lines[0]?.item.qty ?? 1)

function destinationLabel(dest?: string | null) {
  if (dest === 'Para llevar') return restaurantStore.labelTakeaway
  return restaurantStore.labelDineIn
}
</script>

<template>
  <div class="rounded-lg border border-amber-200/70 dark:border-amber-900/40 bg-amber-50/40 dark:bg-amber-900/10 mb-1.5 overflow-hidden">
    <div class="flex items-center gap-2 px-2.5 py-1.5 bg-amber-100/60 dark:bg-amber-900/25">
      <UtensilsCrossed :size="13" class="text-amber-600 dark:text-amber-400 shrink-0" />
      <span class="text-xs font-bold text-amber-800 dark:text-amber-300 flex-1 truncate">{{ label }}</span>
      <button
        @click.stop="emit('toggleDestination', comboUid)"
        :aria-label="__('Toggle destination')"
        class="inline-flex items-center gap-1 font-bold uppercase tracking-wide rounded bg-white/70 dark:bg-black/20 text-amber-700 dark:text-amber-400 shrink-0"
        :class="isTouchDevice ? 'px-2 py-1.5 text-[10px]' : 'px-1.5 py-0.5 text-[9px]'"
      >
        <ShoppingBag v-if="destination === 'Para llevar'" :size="9" />
        <UtensilsCrossed v-else :size="9" />
        {{ destinationLabel(destination) }}
      </button>
      <button
        @click.stop="emit('editComboNotes', comboUid)"
        :aria-label="__('Combo note')"
        class="inline-flex items-center gap-1 rounded font-medium max-w-[120px] transition-colors shrink-0"
        :class="[
          isTouchDevice ? 'px-2 py-1.5 text-[10px]' : 'px-1.5 py-0 text-[9px]',
          notes
            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
            : 'bg-white/70 dark:bg-black/20 text-amber-400 dark:text-amber-600'
        ]"
      >
        <StickyNote :size="9" class="shrink-0" />
        <span class="truncate">{{ notes || __('Note') }}</span>
      </button>
      <div class="flex items-center gap-0.5 shrink-0">
        <button
          @click.stop="emit('updateQty', comboUid, qty - 1)"
          :aria-label="__('Decrease quantity')"
          class="rounded-md flex items-center justify-center text-amber-500 dark:text-amber-500 hover:bg-white/70 dark:hover:bg-black/20 active:scale-90 transition-all duration-150"
          :class="isTouchDevice ? 'w-9 h-9' : 'w-6 h-6'"
        >
          <Minus :size="isTouchDevice ? 15 : 12" />
        </button>
        <span class="text-center text-xs font-bold text-amber-800 dark:text-amber-300" :class="isTouchDevice ? 'w-7' : 'w-5'">{{ qty }}</span>
        <button
          @click.stop="emit('updateQty', comboUid, qty + 1)"
          :aria-label="__('Increase quantity')"
          class="rounded-md flex items-center justify-center text-amber-500 dark:text-amber-500 hover:bg-white/70 dark:hover:bg-black/20 active:scale-90 transition-all duration-150"
          :class="isTouchDevice ? 'w-9 h-9' : 'w-6 h-6'"
        >
          <Plus :size="isTouchDevice ? 15 : 12" />
        </button>
      </div>
      <span class="text-xs font-bold text-gray-900 dark:text-gray-100 shrink-0">{{ formatCurrency(price) }}</span>
      <button
        @click.stop="emit('removeInstance', comboUid)"
        :aria-label="__('Remove {0}', [label])"
        class="rounded-md flex items-center justify-center text-amber-400 dark:text-amber-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 active:scale-90 transition-all duration-150 shrink-0"
        :class="isTouchDevice ? 'w-9 h-9' : 'w-6 h-6'"
      >
        <Trash2 :size="isTouchDevice ? 15 : 12" />
      </button>
    </div>
    <div class="px-1 py-0.5">
      <CartItemComp
        v-for="line in lines"
        :key="line.item.uid"
        :item="line.item"
        :index="line.index"
        :selected="selectedIndex === line.index"
        is-combo-component
        @select="emit('select', $event)"
        @update-qty="() => {}"
        @remove="emit('removeInstance', comboUid)"
        @edit-modifiers="emit('editModifiers', $event)"
      />
    </div>
  </div>
</template>
