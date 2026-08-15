<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { computed } from 'vue'
import { Minus, Plus, Trash2, Gift, Zap, Package, ShoppingBag, ListPlus, UtensilsCrossed } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'
import { useRestaurantStore } from '@/stores/restaurant'
import { useTouchDevice } from '@/composables/useTouchDevice'
import type { CartItem } from '@/types'

const props = defineProps<{
  item: CartItem
  index: number
  selected: boolean
  // True for a component row rendered inside ComboCartGroup. Qty is fixed
  // at 1 by the price-distribution algorithm and deletion removes the
  // whole combo instance (via the group header), not just this row — so
  // both controls are redundant/misleading here and are hidden. Destination,
  // notes and modifiers stay editable per component: one customer eats the
  // segundo at a table and takes the sopa away, and "hold the salt" applies
  // to just the soup. The group header still flips all of them at once.
  isComboComponent?: boolean
}>()

const emit = defineEmits<{
  select: [index: number]
  updateQty: [index: number, qty: number]
  remove: [index: number]
  toggleDestination: [index: number]
  editModifiers: [index: number]
}>()

const { formatCurrency } = useCurrency()
const restaurantStore = useRestaurantStore()
const { isTouchDevice } = useTouchDevice()

// Qty/delete column widths must stay in lockstep with Cart.vue's header row
// and ComboCartGroup.vue's placeholder columns, since combo-component rows
// (isComboComponent) hide these controls but keep placeholder divs the same
// width to preserve the Amount column's alignment across row types.
const qtyColWidth = computed(() => (isTouchDevice.value ? '132px' : '88px'))
const deleteColWidth = computed(() => (isTouchDevice.value ? '44px' : '28px'))

// Notes and modifiers are unified behind one button/dialog (ModifierPicker
// carries a manual text box alongside any predefined modifier chips), so
// this chip's summary combines both rather than showing separate ones.
const hasNotesOrModifiers = computed(() => !!props.item.notes || !!(props.item.modifiers && props.item.modifiers.length))
const modifiersSummary = computed(() => {
  const parts: string[] = []
  if (props.item.notes) parts.push(props.item.notes)
  if (props.item.modifiers?.length) parts.push(...props.item.modifiers.map((m) => m.label))
  return parts.length ? parts.join(', ') : __('Modifiers')
})
</script>

<template>
  <div>
    <div
      role="listitem"
      @click="emit('select', index)"
      class="group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all duration-150"
      :class="[
        item.is_free_item
          ? 'bg-green-50 dark:bg-green-900/10'
          : selected
            ? 'bg-blue-50/50 dark:bg-blue-900/10'
            : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
      ]"
    >
      <!-- Item image thumbnail (ERPNext-style) -->
      <div class="w-8 h-8 rounded-md flex items-center justify-center shrink-0 overflow-hidden bg-gray-100 dark:bg-gray-800">
        <img
          v-if="item.image"
          :src="item.image"
          :alt="item.item_name"
          class="w-full h-full object-cover"
        />
        <Package v-else class="text-gray-300 dark:text-gray-600" :size="14" />
      </div>

      <!-- Item name & description -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-sm font-bold text-gray-800 dark:text-gray-200 break-words leading-tight">
            {{ item.item_name }}
          </span>
          <span
            v-if="item.is_free_item"
            class="inline-flex items-center gap-0.5 px-1.5 py-0 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 rounded text-[9px] font-bold shrink-0"
          >
            <Gift :size="8" />
            {{ __('Free') }}
          </span>
          <span
            v-else-if="item.pricing_rules"
            class="inline-flex items-center gap-0.5 px-1.5 py-0 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 rounded text-[9px] font-bold shrink-0"
          >
            <Zap :size="8" />
            {{ __('Promo') }}
          </span>
        </div>
        <div class="flex items-center gap-1.5 mt-0.5 text-xs text-gray-500 dark:text-gray-400">
          <span v-if="item.is_free_item" class="text-green-600 dark:text-green-400 font-medium">{{ formatCurrency(0) }}</span>
          <template v-else>
            <span v-if="item.price_list_rate && item.price_list_rate !== item.rate" class="line-through text-gray-400 dark:text-gray-500 text-[10px]">{{ formatCurrency(item.price_list_rate) }}</span>
            <span class="font-medium">{{ formatCurrency(item.rate) }}</span>
          </template>
          <span v-if="!item.is_free_item && item.discount_percentage > 0" class="inline-flex items-center px-1 py-0 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded text-[10px] font-semibold">
            -{{ item.discount_percentage }}%
          </span>
          <span v-else-if="!item.is_free_item && item.discount_amount > 0" class="inline-flex items-center px-1 py-0 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded text-[10px] font-semibold">
            -{{ formatCurrency(item.discount_amount) }}
          </span>
        </div>
        <div v-if="item.batch_no || item.serial_no" class="flex items-center gap-1 mt-0.5">
          <span v-if="item.batch_no" class="inline-flex items-center px-1.5 py-0 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded text-[9px] font-medium">
            B: {{ item.batch_no }}
          </span>
          <span v-if="item.serial_no" class="inline-flex items-center px-1.5 py-0 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded text-[9px] font-medium">
            SN: {{ item.serial_no }}
          </span>
        </div>
        <div v-if="item.uom !== item.stock_uom" class="text-[9px] text-gray-400 dark:text-gray-500 mt-0.5">
          {{ item.uom }} ({{ item.conversion_factor }}x)
        </div>
        <div v-if="item.item_tax_template" class="text-[9px] text-purple-500 dark:text-purple-400 mt-0.5">
          {{ item.item_tax_template }}
        </div>

        <!-- Restaurant: destination / notes / modifiers (hidden entirely
             for free pricing-rule items, which aren't independently
             editable) -->
        <div
          v-if="restaurantStore.enabled && !item.is_free_item"
          class="flex flex-wrap items-center gap-1 mt-1"
          @click.stop
        >
          <button
            @click="emit('toggleDestination', index)"
            :aria-label="__('Toggle destination')"
            class="inline-flex items-center gap-1 rounded font-bold uppercase tracking-wide transition-colors shrink-0"
            :class="[
              isTouchDevice ? 'px-2 py-1 text-[10px]' : 'px-1.5 py-0 text-[9px]',
              item.destination === 'Para llevar'
                ? 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400'
                : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
            ]"
          >
            <ShoppingBag v-if="item.destination === 'Para llevar'" :size="9" />
            <UtensilsCrossed v-else :size="9" />
            {{ item.destination === 'Para llevar' ? restaurantStore.labelTakeaway : restaurantStore.labelDineIn }}
          </button>

          <button
            @click="emit('editModifiers', index)"
            :aria-label="__('Modifiers')"
            class="inline-flex items-center gap-1 rounded font-medium max-w-[200px] transition-colors"
            :class="[
              isTouchDevice ? 'px-2 py-1 text-[10px]' : 'px-1.5 py-0 text-[9px]',
              hasNotesOrModifiers
                ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'
            ]"
          >
            <ListPlus :size="9" class="shrink-0" />
            <span class="truncate">{{ modifiersSummary }}</span>
          </button>
        </div>
      </div>

      <!-- Qty Controls (hidden for free items and combo components) -->
      <div
        v-if="!item.is_free_item && !isComboComponent"
        class="flex items-center gap-0.5 shrink-0"
        :style="{ width: qtyColWidth }"
      >
        <button
          @click.stop="emit('updateQty', index, item.qty - 1)"
          aria-label="Decrease quantity"
          class="rounded-md flex items-center justify-center text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-600 dark:hover:text-gray-300 active:scale-90 transition-all duration-150"
          :class="isTouchDevice ? 'w-11 h-11' : 'w-7 h-7'"
        >
          <Minus :size="isTouchDevice ? 18 : 14" />
        </button>
        <span
          class="text-center text-xs font-bold text-gray-800 dark:text-gray-200"
          :class="isTouchDevice ? 'w-11' : 'w-7'"
        >
          {{ item.qty }}
        </span>
        <button
          @click.stop="emit('updateQty', index, item.qty + 1)"
          aria-label="Increase quantity"
          class="rounded-md flex items-center justify-center text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-600 dark:hover:text-gray-300 active:scale-90 transition-all duration-150"
          :class="isTouchDevice ? 'w-11 h-11' : 'w-7 h-7'"
        >
          <Plus :size="isTouchDevice ? 18 : 14" />
        </button>
      </div>
      <div v-else-if="item.is_free_item" class="shrink-0" :style="{ width: qtyColWidth }">
        <span class="text-xs font-bold text-green-600 dark:text-green-400">&times;{{ item.qty }}</span>
      </div>
      <div v-else-if="!isComboComponent" :style="{ width: qtyColWidth }" />
      <!-- combo component: qty is edited at the instance level from the
           ComboCartGroup header — nothing to show here, and unlike a plain
           item row this one isn't sharing a column grid with Cart.vue's
           header (it's nested inside ComboCartGroup's own box), so the
           placeholder is dropped rather than reserved: that width goes to
           the name and the destination/modifiers row instead. -->

      <!-- Amount -->
      <div class="w-[72px] text-right shrink-0">
        <span class="text-sm font-bold" :class="item.is_free_item ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-gray-100'">
          {{ formatCurrency(item.is_free_item ? 0 : item.amount) }}
        </span>
      </div>

      <!-- Delete (hidden for free items — managed by pricing rules — and
           for combo components, whose whole instance deletes together via
           the ComboCartGroup header instead). Always visible on touch
           devices — hover doesn't exist there, so gating visibility on
           hover/selection would force a select-then-delete two-tap. -->
      <button
        v-if="!item.is_free_item && !isComboComponent"
        @click.stop="emit('remove', index)"
        aria-label="Remove item"
        class="rounded-md flex items-center justify-center text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 active:scale-90 transition-all duration-150"
        :class="isTouchDevice
          ? 'w-11 h-11'
          : ['w-7 h-7 opacity-0 group-hover:opacity-100', { 'opacity-100': selected }]"
      >
        <Trash2 :size="isTouchDevice ? 17 : 13" />
      </button>
      <div v-else-if="!isComboComponent" :style="{ width: deleteColWidth }" />
    </div>

    <!-- Separator line (ERPNext-style) -->
    <div class="mx-3 border-b border-gray-100 dark:border-gray-800" />
  </div>
</template>
