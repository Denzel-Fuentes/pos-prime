<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { UtensilsCrossed, Trash2 } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'
import { useRestaurantStore } from '@/stores/restaurant'
import CartItemComp from './../cart/CartItem.vue'
import type { CartItem } from '@/types'

const props = defineProps<{
  comboUid: string
  label: string
  price: number
  destination?: string | null
  lines: { index: number; item: CartItem }[]
  selectedIndex: number | null
}>()

const emit = defineEmits<{
  select: [index: number]
  removeInstance: [comboUid: string]
}>()

const restaurantStore = useRestaurantStore()
const { formatCurrency } = useCurrency()

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
      <span
        class="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-white/70 dark:bg-black/20 text-amber-700 dark:text-amber-400 shrink-0"
      >
        {{ destinationLabel(destination) }}
      </span>
      <span class="text-xs font-bold text-gray-900 dark:text-gray-100 shrink-0">{{ formatCurrency(price) }}</span>
      <button
        @click.stop="emit('removeInstance', comboUid)"
        :aria-label="__('Remove {0}', [label])"
        class="w-6 h-6 rounded-md flex items-center justify-center text-amber-400 dark:text-amber-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 active:scale-90 transition-all duration-150 shrink-0"
      >
        <Trash2 :size="12" />
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
      />
    </div>
  </div>
</template>
