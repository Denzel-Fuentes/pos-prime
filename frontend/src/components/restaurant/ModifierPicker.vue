<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref } from 'vue'
import { useRestaurantStore } from '@/stores/restaurant'
import { X, Check, ListPlus } from 'lucide-vue-next'
import type { RestaurantModifierGroup, RestaurantModifier } from '@/types'

const props = withDefaults(
  defineProps<{
    itemCode: string
    itemName: string
    modelValue: { modifiers: { modifier: string; label: string }[]; notes: string | null }
    // Some combo slots restrict which items may take a predefined modifier
    // group (see slot.allow_modifiers) — the manual note box below stays
    // available regardless, only the chip groups are hidden.
    allowGroups?: boolean
  }>(),
  { allowGroups: true }
)

const emit = defineEmits<{
  close: []
  confirm: [payload: { modifiers: { modifier: string; label: string }[]; notes: string }]
}>()

const restaurantStore = useRestaurantStore()
// Config is fetched once at session start and doesn't change while this
// dialog is open — a plain (non-reactive) snapshot is enough, no need for
// ComboBuilderDialog's onMounted fetch-and-loading dance.
const groups = props.allowGroups ? restaurantStore.modifierGroupsForItem(props.itemCode) : []

const selected = ref<Record<string, { modifier: string; label: string }>>(
  Object.fromEntries(props.modelValue.modifiers.map((m) => [m.modifier, m]))
)
// Notes and modifiers are unified into this one dialog — the manual text
// box lets staff write a modifier/note that isn't one of the predefined
// chips ("sin cebolla", "extra queso") alongside picking from groups.
const notes = ref(props.modelValue.notes || '')

function isSelected(modifier: string) {
  return modifier in selected.value
}

function toggle(group: RestaurantModifierGroup, modifier: RestaurantModifier) {
  const label = modifier.print_label || modifier.modifier_name
  if (group.selection_type === 'Single') {
    // Radio behaviour: picking one clears any other selection from this group.
    for (const m of group.modifiers) delete selected.value[m.modifier]
    selected.value[modifier.modifier] = { modifier: modifier.modifier, label }
  } else if (isSelected(modifier.modifier)) {
    delete selected.value[modifier.modifier]
  } else {
    selected.value[modifier.modifier] = { modifier: modifier.modifier, label }
  }
}

function confirm() {
  emit('confirm', { modifiers: Object.values(selected.value), notes: notes.value.trim() })
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    :aria-label="__('Modifiers')"
    @keydown.escape="emit('close')"
  >
    <div class="absolute inset-0 bg-black/30 dark:bg-black/50" @click="emit('close')" />
    <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl dark:shadow-black/30 w-full max-w-sm max-h-[80vh] overflow-y-auto">
      <div class="sticky top-0 bg-white dark:bg-gray-900 px-4 py-3 flex items-center justify-between border-b border-gray-200 dark:border-gray-800 rounded-t-xl z-10">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center shrink-0">
            <ListPlus :size="16" class="text-teal-600 dark:text-teal-400" />
          </div>
          <div class="min-w-0">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ __('Modifiers') }}</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ itemName }}</p>
          </div>
        </div>
        <button @click="emit('close')" class="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 shrink-0">
          <X :size="18" />
        </button>
      </div>

      <div class="p-4 space-y-4">
        <div v-if="allowGroups && groups.length === 0" class="text-center py-2 text-sm text-gray-400 dark:text-gray-500">
          {{ __('No preset modifiers available for this item') }}
        </div>
        <template v-if="allowGroups">
          <div v-for="group in groups" :key="group.name">
            <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
              {{ group.group_name }}
            </h4>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="modifier in group.modifiers"
                :key="modifier.modifier"
                @click="toggle(group, modifier)"
                class="px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors"
                :class="
                  isSelected(modifier.modifier)
                    ? 'border-teal-400 dark:border-teal-600 bg-teal-50 dark:bg-teal-900/20 text-teal-800 dark:text-teal-300'
                    : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                "
              >
                {{ modifier.print_label || modifier.modifier_name }}
              </button>
            </div>
          </div>
        </template>

        <div>
          <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
            {{ __('Manual note') }}
          </h4>
          <textarea
            v-model="notes"
            rows="2"
            :placeholder="__('e.g. sin cebolla, bien cocido...')"
            class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 resize-none"
          />
        </div>

        <button
          @click="confirm"
          class="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          <Check :size="16" />
          {{ __('Done') }}
        </button>
      </div>
    </div>
  </div>
</template>
