<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useItemsStore } from '@/stores/items'
import { usePosSessionStore } from '@/stores/posSession'
import { useCurrency } from '@/composables/useCurrency'
import { X, Package } from 'lucide-vue-next'
import type { Item } from '@/types'

const props = defineProps<{
  item: Item
}>()

const emit = defineEmits<{
  close: []
  select: [variant: Item]
}>()

const itemsStore = useItemsStore()
const sessionStore = usePosSessionStore()
const { formatCurrency } = useCurrency()

const loading = ref(false)
const error = ref<string | null>(null)
const variants = ref<Item[]>([])

onMounted(async () => {
  loading.value = true
  try {
    variants.value = await itemsStore.fetchVariants(props.item.item_code, sessionStore.posProfile)
    if (variants.value.length === 0) {
      error.value = __('No variants available for this item')
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    :aria-label="item.item_name"
    @keydown.escape="emit('close')"
  >
    <div class="absolute inset-0 bg-black/30 dark:bg-black/50" @click="emit('close')" />
    <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl dark:shadow-black/30 w-full max-w-md max-h-[85vh] overflow-y-auto">
      <div class="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center justify-between rounded-t-xl z-10">
        <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
          {{ item.item_name }}
        </h3>
        <button @click="emit('close')" class="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
          <X :size="18" />
        </button>
      </div>

      <div class="p-4 space-y-2">
        <div v-if="loading" class="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
          {{ __('Loading...') }}
        </div>

        <div v-else-if="error" class="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
          {{ error }}
        </div>

        <button
          v-for="variant in variants"
          :key="variant.item_code"
          @click="emit('select', variant)"
          class="w-full flex items-center gap-3 text-left px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
        >
          <div class="w-9 h-9 rounded-md bg-gray-50 dark:bg-gray-800 flex items-center justify-center overflow-hidden shrink-0">
            <img
              v-if="variant.image"
              :src="variant.image"
              :alt="variant.item_name"
              class="w-full h-full object-cover"
            />
            <Package v-else class="text-gray-300 dark:text-gray-600" :size="18" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
              {{ variant.item_name }}
            </div>
            <div
              v-if="(variant.is_stock_item || variant.is_product_bundle) && variant.actual_qty !== undefined"
              class="text-xs"
              :class="
                variant.actual_qty > 10
                  ? 'text-green-600 dark:text-green-400'
                  : variant.actual_qty > 0
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-red-600 dark:text-red-400'
              "
            >
              {{ variant.actual_qty > 0 ? `${variant.actual_qty} ${variant.stock_uom}` : __('Out of stock') }}
            </div>
          </div>
          <span class="text-sm font-bold text-gray-900 dark:text-gray-100 shrink-0">
            {{ formatCurrency(variant.rate) }}
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
