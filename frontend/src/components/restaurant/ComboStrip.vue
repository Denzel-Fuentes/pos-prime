<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { computed } from 'vue'
import { useRestaurantStore } from '@/stores/restaurant'
import { useCurrency } from '@/composables/useCurrency'
import { UtensilsCrossed } from 'lucide-vue-next'
import type { RestaurantCombo } from '@/types'

// Combos aren't real Items, so they don't participate in ItemGrid's
// Fuse.js catalog search — matching the item search box against combo
// names/print labels here is a cheap way to not lose "type to find it"
// for combos too (N is always small, no need for fuzzy matching).
const props = defineProps<{
  searchTerm?: string
}>()

const emit = defineEmits<{
  select: [combo: RestaurantCombo]
}>()

const restaurantStore = useRestaurantStore()
const { formatCurrency } = useCurrency()

const visibleCombos = computed(() => {
  const term = props.searchTerm?.trim().toLowerCase()
  if (!term) return restaurantStore.combos
  return restaurantStore.combos.filter(
    (c) => c.combo_name.toLowerCase().includes(term) || c.print_label?.toLowerCase().includes(term)
  )
})
</script>

<template>
  <div
    v-if="restaurantStore.enabled && visibleCombos.length > 0"
    class="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800"
  >
    <div class="flex gap-2 overflow-x-auto px-3 py-2 no-scrollbar">
      <button
        v-for="combo in visibleCombos"
        :key="combo.name"
        @click="emit('select', combo)"
        class="pos-card shrink-0 flex items-center gap-2 rounded-lg pl-2 pr-3 py-1.5 border border-amber-200 dark:border-amber-900/50 hover:border-amber-400 dark:hover:border-amber-700 transition-colors"
      >
        <div class="w-7 h-7 rounded-md bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center shrink-0 overflow-hidden">
          <img v-if="combo.image" :src="combo.image" :alt="combo.combo_name" class="w-full h-full object-cover" />
          <UtensilsCrossed v-else :size="14" class="text-amber-600 dark:text-amber-400" />
        </div>
        <div class="text-left">
          <div class="text-xs font-semibold text-gray-800 dark:text-gray-200 leading-tight">
            {{ combo.print_label || combo.combo_name }}
          </div>
          <div class="text-[11px] font-bold text-amber-600 dark:text-amber-400 leading-tight">
            {{ formatCurrency(combo.combo_price) }}
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
