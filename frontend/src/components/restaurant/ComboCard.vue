<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { UtensilsCrossed, Plus } from 'lucide-vue-next'
import { useSettingsStore } from '@/stores/settings'
import { useCurrency } from '@/composables/useCurrency'
import { useTouchDevice } from '@/composables/useTouchDevice'
import type { RestaurantCombo } from '@/types'

// Deliberately mirrors ItemCard's shape (same image box, same info block,
// same hideImages handling) — combos sit in the very same grid as items, so
// any divergence in height would break the virtualizer's row estimate. Only
// the accent color and the badge tell them apart.
const props = defineProps<{
  combo: RestaurantCombo
}>()

const emit = defineEmits<{
  select: [combo: RestaurantCombo]
}>()

const settingsStore = useSettingsStore()
const { formatCurrency } = useCurrency()
const { isTouchDevice } = useTouchDevice()
</script>

<template>
  <button
    @click="emit('select', props.combo)"
    :aria-label="`Build ${props.combo.print_label || props.combo.combo_name}`"
    class="pos-card group relative flex flex-col rounded-lg overflow-hidden hover:scale-[1.02] transition-all duration-200 text-left border border-amber-200 dark:border-amber-900/50 hover:border-amber-400 dark:hover:border-amber-700"
  >
    <!-- Image -->
    <div
      v-if="!settingsStore.hideImages"
      class="relative h-32 min-h-[8rem] lg:h-36 lg:min-h-[9rem] bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center overflow-hidden"
    >
      <img
        v-if="combo.image"
        :src="combo.image"
        :alt="combo.combo_name"
        loading="lazy"
        class="w-full h-full object-cover"
      />
      <UtensilsCrossed v-else class="text-amber-300 dark:text-amber-800" :size="36" />

      <!-- Add affordance — same rules as ItemCard: hover-reveal on mouse,
           always visible on touch -->
      <div v-if="!isTouchDevice" class="absolute inset-0 bg-amber-600/0 group-hover:bg-amber-600/10 transition-colors duration-200 flex items-center justify-center">
        <div class="w-8 h-8 bg-white dark:bg-gray-800 rounded-full shadow-lg flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-200">
          <Plus :size="16" class="text-amber-600 dark:text-amber-400" />
        </div>
      </div>
      <div v-else class="absolute bottom-1.5 right-1.5 w-8 h-8 bg-white/90 dark:bg-gray-800/90 rounded-full shadow-md flex items-center justify-center">
        <Plus :size="16" class="text-amber-600 dark:text-amber-400" />
      </div>

      <!-- Combo badge — occupies the same corner as ItemCard's Bundle/Options
           badges, so the two card kinds read as one family -->
      <span
        class="absolute top-1.5 left-1.5 text-[9px] lg:text-[10px] font-bold px-1.5 py-0.5 lg:px-2 lg:py-1 rounded-md backdrop-blur-sm bg-amber-500/90 text-white"
      >
        {{ __('Combo') }}
      </span>
    </div>

    <!-- Combo Info -->
    <div class="px-2 py-1.5 flex-1 flex flex-col min-h-[3rem] lg:min-h-[3.5rem]">
      <div class="text-xs lg:text-sm font-semibold text-gray-800 dark:text-gray-200 line-clamp-2 leading-snug">
        {{ combo.print_label || combo.combo_name }}
        <!-- With images off there's no badge slot, so mark it inline -->
        <span
          v-if="settingsStore.hideImages"
          class="ms-1 align-middle text-[9px] font-bold px-1 py-0.5 rounded bg-amber-500/90 text-white"
        >
          {{ __('Combo') }}
        </span>
      </div>
      <div class="mt-auto pt-1">
        <span class="text-sm lg:text-base font-bold text-amber-600 dark:text-amber-400">
          {{ formatCurrency(combo.combo_price) }}
        </span>
      </div>
    </div>
  </button>
</template>
