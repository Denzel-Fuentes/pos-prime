<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref } from 'vue'
import { X, Check, StickyNote } from 'lucide-vue-next'

const props = defineProps<{
  itemName: string
  modelValue: string | null
}>()

const emit = defineEmits<{
  close: []
  confirm: [notes: string]
}>()

const text = ref(props.modelValue || '')

function confirm() {
  emit('confirm', text.value.trim())
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    :aria-label="__('Kitchen note')"
    @keydown.escape="emit('close')"
  >
    <div class="absolute inset-0 bg-black/30 dark:bg-black/50" @click="emit('close')" />
    <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl dark:shadow-black/30 w-full max-w-sm">
      <div class="px-4 py-3 flex items-center justify-between border-b border-gray-200 dark:border-gray-800">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center shrink-0">
            <StickyNote :size="16" class="text-purple-600 dark:text-purple-400" />
          </div>
          <div class="min-w-0">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ __('Kitchen note') }}</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ itemName }}</p>
          </div>
        </div>
        <button @click="emit('close')" class="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 shrink-0">
          <X :size="18" />
        </button>
      </div>

      <div class="p-4 space-y-3">
        <textarea
          v-model="text"
          rows="3"
          autofocus
          :placeholder="__('e.g. sin cebolla, bien cocido...')"
          @keydown.enter.exact.prevent="confirm"
          class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 resize-none"
        />
        <button
          @click="confirm"
          class="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          <Check :size="16" />
          {{ __('Save') }}
        </button>
      </div>
    </div>
  </div>
</template>
