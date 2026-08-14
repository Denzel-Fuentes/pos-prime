<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePosSessionStore } from '@/stores/posSession'
import { useSettingsStore } from '@/stores/settings'
import { useRestaurantStore } from '@/stores/restaurant'
import { useCurrency } from '@/composables/useCurrency'
import { useDeskMode } from '@/composables/useDeskMode'
import { LogIn, Calculator, UtensilsCrossed, ArrowLeft } from 'lucide-vue-next'
import DenominationCalculator from '@/components/shift/DenominationCalculator.vue'
import type { DailyMenuGroup } from '@/types'

const router = useRouter()
const sessionStore = usePosSessionStore()
const settingsStore = useSettingsStore()
const restaurantStore = useRestaurantStore()
const { formatCurrency } = useCurrency()
const { isDeskMode } = useDeskMode()

const selectedProfile = ref('')
const company = ref('')
const openingBalances = ref<{ mode_of_payment: string; opening_amount: number }[]>([])
const loading = ref(false)
const error = ref('')
const denomCalcIndex = ref(-1)
const showDenomCalc = ref(false)
// Two-step wizard: step 1 collects profile/company/opening balances, step 2
// (only shown when the profile has a daily menu configured) collects today's
// available dishes.
const step = ref<1 | 2>(1)
// "Platos del dia" — restaurant module. Starts empty every time (opt-in:
// the cashier actively marks what's available today, nothing is assumed).
const availableDishes = ref<Record<string, boolean>>({})

function isCash(mode: string): boolean {
  return mode.toLowerCase().includes('cash')
}

function openDenomCalc(index: number) {
  denomCalcIndex.value = index
  showDenomCalc.value = true
}

function onDenomApply(value: number) {
  if (denomCalcIndex.value >= 0) {
    openingBalances.value[denomCalcIndex.value].opening_amount = value
  }
}

onMounted(async () => {
  const data = await settingsStore.fetchPOSProfiles()
  if (data?.openEntry) {
    router.replace({ name: 'POS' })
    return
  }
  if (settingsStore.posProfiles.length === 1) {
    selectedProfile.value = settingsStore.posProfiles[0].name
    company.value = settingsStore.posProfiles[0].company
    await loadProfilePaymentMethods()
  }
})

async function onProfileChange() {
  const profile = settingsStore.posProfiles.find(
    (p) => p.name === selectedProfile.value
  )
  if (profile) {
    company.value = profile.company
    await loadProfilePaymentMethods()
  }
}

async function loadProfilePaymentMethods() {
  availableDishes.value = {}
  step.value = 1
  if (!selectedProfile.value) {
    openingBalances.value = []
    await restaurantStore.fetchDailyMenuCandidates('')
    return
  }
  try {
    await settingsStore.loadPOSProfile(selectedProfile.value)
    const methods = settingsStore.paymentMethods
    openingBalances.value = methods.map((pm) => ({
      mode_of_payment: pm.mode_of_payment,
      opening_amount: 0,
    }))
  } catch {
    openingBalances.value = [{ mode_of_payment: 'Cash', opening_amount: 0 }]
  }
  await restaurantStore.fetchDailyMenuCandidates(selectedProfile.value)
}

function toggleDish(itemCode: string) {
  availableDishes.value[itemCode] = !availableDishes.value[itemCode]
}

function selectedCountFor(group: DailyMenuGroup) {
  return group.items.filter((item) => availableDishes.value[item.item_code]).length
}

/** Per-group "All"/"None" — a pensión with thirty segundos shouldn't have
 * to tap thirty chips to say "everything is on today". */
function setGroupSelection(group: DailyMenuGroup, selected: boolean) {
  for (const item of group.items) {
    availableDishes.value[item.item_code] = selected
  }
}

function goToNextStep() {
  if (!selectedProfile.value) {
    error.value = __('Please select a POS Profile')
    return
  }
  for (const balance of openingBalances.value) {
    if (balance.opening_amount < 0) {
      error.value = __('Opening amounts cannot be negative')
      return
    }
  }
  error.value = ''
  if (restaurantStore.hasDailyMenu) {
    step.value = 2
  } else {
    openShift()
  }
}

function goToPreviousStep() {
  error.value = ''
  step.value = 1
}

async function openShift() {
  if (!selectedProfile.value) {
    error.value = __('Please select a POS Profile')
    return
  }
  // Validate opening balances are non-negative
  for (const balance of openingBalances.value) {
    if (balance.opening_amount < 0) {
      error.value = __('Opening amounts cannot be negative')
      return
    }
  }
  loading.value = true
  error.value = ''
  try {
    const available_items = Object.keys(availableDishes.value).filter(
      (code) => availableDishes.value[code]
    )
    await sessionStore.createOpeningEntry({
      pos_profile: selectedProfile.value,
      company: company.value,
      balance_details: openingBalances.value,
      available_items,
    })
    await settingsStore.loadPOSProfile(selectedProfile.value)
    router.replace({ name: 'POS' })
  } catch (e: any) {
    error.value = e.messages?.[0] || e.message || 'Failed to open shift'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div :class="['bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4', isDeskMode ? 'min-h-full' : 'min-h-screen']">
    <!-- The dish picker holds several groups of dishes side by side, so it
         gets a wider card than the one-column balances step. -->
    <div
      class="w-full bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 transition-[max-width]"
      :class="step === 2 && restaurantStore.hasDailyMenu ? 'max-w-3xl' : 'max-w-md'"
    >
      <div class="flex items-center gap-3 mb-6">
        <div class="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <LogIn class="text-blue-600 dark:text-blue-400" :size="20" />
        </div>
        <div>
          <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ __('Open POS Shift') }}</h1>
          <p class="text-sm text-gray-500 dark:text-gray-400">{{ __('Select profile and enter opening balances') }}</p>
        </div>
      </div>

      <div v-if="error" class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg text-sm">
        {{ error }}
      </div>

      <!-- Step indicator (only meaningful when there's a second step) -->
      <div v-if="restaurantStore.hasDailyMenu" class="flex items-center gap-2 mb-6">
        <div class="flex items-center gap-1.5 flex-1">
          <div
            class="h-1.5 flex-1 rounded-full transition-colors"
            :class="step >= 1 ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
          />
          <div
            class="h-1.5 flex-1 rounded-full transition-colors"
            :class="step >= 2 ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
          />
        </div>
        <span class="text-xs text-gray-500 dark:text-gray-400 shrink-0">
          {{ __('Step') }} {{ step }} {{ __('of') }} 2
        </span>
      </div>

      <div v-show="step === 1" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ __('POS Profile') }}
          </label>
          <select
            v-model="selectedProfile"
            @change="onProfileChange"
            class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">{{ __('Select Profile...') }}</option>
            <option
              v-for="profile in settingsStore.posProfiles"
              :key="profile.name"
              :value="profile.name"
            >
              {{ profile.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ __('Company') }}
          </label>
          <input
            :value="company"
            readonly
            class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-600 dark:text-gray-400"
          />
        </div>

        <!-- Opening balances for each payment method -->
        <div v-if="openingBalances.length > 0">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {{ __('Opening Balances') }}
          </label>
          <div class="space-y-2">
            <div
              v-for="(balance, index) in openingBalances"
              :key="balance.mode_of_payment"
              class="flex items-center gap-3"
            >
              <span class="text-sm text-gray-600 dark:text-gray-400 w-28 shrink-0">
                {{ balance.mode_of_payment }}
              </span>
              <input
                v-model.number="openingBalances[index].opening_amount"
                type="number"
                min="0"
                step="0.01"
                class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0.00"
              />
              <button
                v-if="isCash(balance.mode_of_payment)"
                @click="openDenomCalc(index)"
                class="p-2 rounded-lg text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                title="Denomination calculator"
              >
                <Calculator :size="18" />
              </button>
            </div>
          </div>
        </div>

        <button
          @click="goToNextStep"
          :disabled="loading || !selectedProfile"
          class="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ restaurantStore.hasDailyMenu ? __('Next') : (loading ? __('Opening...') : __('Open Shift')) }}
        </button>
      </div>

      <!-- Platos del dia (restaurant module) — only shown when Restaurant
           Settings has Item Groups configured under "Daily Menu". Nothing
           is pre-checked: the cashier actively marks what's available. -->
      <div v-if="step === 2 && restaurantStore.hasDailyMenu" class="space-y-4">
        <div>
          <label class="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <UtensilsCrossed :size="14" class="text-amber-500" />
            {{ __('Available Dishes Today') }}
          </label>
          <!-- A pensión can list dozens of dishes across several groups.
               The list scrolls inside its own box so the Back / Open Shift
               buttons below stay reachable, and each dish is a grid cell
               with a truncating label so a long name can't widen the page. -->
          <div class="space-y-3 max-h-[55vh] overflow-y-auto pr-1 -mr-1">
            <div v-for="group in restaurantStore.dailyMenuCandidates" :key="group.item_group">
              <div class="sticky top-0 z-10 bg-white dark:bg-gray-900 flex items-center gap-2 py-1 mb-1.5">
                <span class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide truncate">
                  {{ group.item_group }}
                </span>
                <span class="text-[10px] text-gray-400 dark:text-gray-500 shrink-0">
                  {{ selectedCountFor(group) }}/{{ group.items.length }}
                </span>
                <div v-if="group.items.length" class="ml-auto flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    @click="setGroupSelection(group, true)"
                    class="px-1.5 py-0.5 rounded text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                  >
                    {{ __('All') }}
                  </button>
                  <button
                    type="button"
                    @click="setGroupSelection(group, false)"
                    class="px-1.5 py-0.5 rounded text-[10px] font-semibold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    {{ __('None') }}
                  </button>
                </div>
              </div>
              <div v-if="group.items.length === 0" class="text-xs text-gray-400 dark:text-gray-500">
                {{ __('No items in this group') }}
              </div>
              <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1.5">
                <button
                  v-for="item in group.items"
                  :key="item.item_code"
                  type="button"
                  :title="item.item_name"
                  @click="toggleDish(item.item_code)"
                  class="px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors text-left truncate"
                  :class="
                    availableDishes[item.item_code]
                      ? 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 font-semibold'
                      : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600'
                  "
                >
                  {{ item.item_name }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="goToPreviousStep"
            :disabled="loading"
            class="py-2.5 px-4 flex items-center justify-center gap-1.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ArrowLeft :size="16" />
            {{ __('Back') }}
          </button>
          <button
            @click="openShift"
            :disabled="loading"
            class="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ loading ? __('Opening...') : __('Open Shift') }}
          </button>
        </div>
      </div>
    </div>

    <DenominationCalculator
      :modelValue="denomCalcIndex >= 0 ? openingBalances[denomCalcIndex]?.opening_amount ?? 0 : 0"
      @update:modelValue="onDenomApply"
      :currency="settingsStore.currency"
      v-model:show="showDenomCalc"
    />
  </div>
</template>
