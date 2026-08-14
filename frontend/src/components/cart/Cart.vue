<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useCartStore } from '@/stores/cart'
import { useCustomerStore } from '@/stores/customer'
import { usePaymentStore } from '@/stores/payment'
import { useSettingsStore } from '@/stores/settings'
import { useRestaurantStore } from '@/stores/restaurant'
import { useCurrency } from '@/composables/useCurrency'
import { useTouchDevice } from '@/composables/useTouchDevice'
import CartItemComp from './CartItem.vue'
import CartSummary from './CartSummary.vue'
import CouponCodeInput from './CouponCodeInput.vue'
import InvoiceDiscount from './InvoiceDiscount.vue'
import InvoiceOptions from './InvoiceOptions.vue'
import NumPad from './NumPad.vue'
import CustomerSelector from '@/components/customer/CustomerSelector.vue'
import CustomerDetailPanel from '@/components/customer/CustomerDetailPanel.vue'
import ComboCartGroup from '@/components/restaurant/ComboCartGroup.vue'
import NoteDialog from '@/components/restaurant/NoteDialog.vue'
import ModifierPicker from '@/components/restaurant/ModifierPicker.vue'
import { ShoppingCart, CreditCard, Pause, Check } from 'lucide-vue-next'
import type { CartItem, RestaurantDestination } from '@/types'

const { isTouchDevice } = useTouchDevice()

const cartStore = useCartStore()
const customerStore = useCustomerStore()
const paymentStore = usePaymentStore()
const settingsStore = useSettingsStore()
const restaurantStore = useRestaurantStore()
const { formatCurrency } = useCurrency()

const showNumPad = ref(false)
const numPadMode = ref<'qty' | 'discount' | 'discountAmt' | 'rate'>('qty')

const availableNumPadModes = computed(() => {
  const modes: ('qty' | 'discount' | 'discountAmt' | 'rate')[] = ['qty']
  if (settingsStore.allowDiscountChange) {
    modes.push('discount')
    modes.push('discountAmt')
  }
  if (settingsStore.allowRateChange) modes.push('rate')
  return modes
})

const numPadValue = computed(() => {
  if (cartStore.selectedItemIndex === null) return 0
  const item = cartStore.items[cartStore.selectedItemIndex]
  if (!item) return 0
  if (numPadMode.value === 'qty') return item.qty
  if (numPadMode.value === 'discount') return item.discount_percentage
  if (numPadMode.value === 'discountAmt') return item.discount_amount
  return item.rate
})

const numPadLabel = computed(() => {
  if (numPadMode.value === 'qty') return __('Quantity')
  if (numPadMode.value === 'discount') return __('Discount %')
  if (numPadMode.value === 'discountAmt') return __('Discount Amt')
  return __('Price')
})

function onItemSelect(index: number) {
  const item = cartStore.items[index]
  if (item?.is_free_item) return // Free items are not editable
  // Combo component rate/qty is fixed by distribute_combo_price and
  // overwritten server-side on sale regardless of any client edit — don't
  // offer an editor that would silently disagree with the final receipt.
  if (item?.combo_uid) return
  cartStore.selectItem(index)
  showNumPad.value = true
  numPadMode.value = 'qty'
  // Sync keyboard input
  if (item) keyboardInput.value = String(item.qty)
}

function onUpdateQty(index: number, qty: number) {
  if (cartStore.items[index]?.is_free_item) return
  cartStore.updateQty(index, qty)
}

function onRemove(index: number) {
  if (cartStore.items[index]?.is_free_item) return
  cartStore.removeItem(index)
  showNumPad.value = false
}

function onToggleItemDestination(index: number) {
  const item = cartStore.items[index]
  if (!item) return
  cartStore.updateItemDestination(index, item.destination === 'Para llevar' ? 'Mesa' : 'Para llevar')
}

function onToggleComboDestination(comboUid: string) {
  const lines = cartStore.items.filter((i) => i.combo_uid === comboUid)
  if (!lines.length) return
  // Components can differ (segundo at the table, sopa to take away). From a
  // mixed instance the first tap only unifies them — flipping straight away
  // would silently discard the per-line choices behind one destination.
  const first = lines[0].destination === 'Para llevar' ? 'Para llevar' : 'Mesa'
  const mixed = lines.some((l) => (l.destination || 'Mesa') !== first)
  const target: RestaurantDestination = mixed ? first : first === 'Para llevar' ? 'Mesa' : 'Para llevar'
  cartStore.updateComboInstanceDestination(comboUid, target)
}

function onUpdateComboQty(comboUid: string, qty: number) {
  cartStore.updateComboInstanceQty(comboUid, qty)
}

// Instance-wide combo note — a parallel dialog target to modifierPickerIndex
// below, addressed by combo_uid instead of index since it applies to every
// line in the instance (see cartStore.updateComboNotes).
const comboNotesUid = ref<string | null>(null)
const comboNotesItem = computed(() =>
  comboNotesUid.value !== null ? cartStore.items.find((i) => i.combo_uid === comboNotesUid.value) ?? null : null
)

function onEditComboNotes(comboUid: string) {
  comboNotesUid.value = comboUid
}

function onSaveComboNotes(notes: string) {
  if (comboNotesUid.value !== null) cartStore.updateComboNotes(comboNotesUid.value, notes)
  comboNotesUid.value = null
}

const modifierPickerIndex = ref<number | null>(null)
const modifierPickerItem = computed(() =>
  modifierPickerIndex.value !== null ? cartStore.items[modifierPickerIndex.value] ?? null : null
)

function onEditModifiers(index: number) {
  modifierPickerIndex.value = index
}

// Notes and modifiers are unified behind one dialog — see ModifierPicker's
// manual text box alongside its predefined chips.
function onSaveModifiers(payload: { modifiers: { modifier: string; label: string }[]; notes: string }) {
  if (modifierPickerIndex.value !== null) {
    cartStore.updateItemModifiers(modifierPickerIndex.value, payload.modifiers)
    cartStore.updateItemNotes(modifierPickerIndex.value, payload.notes)
  }
  modifierPickerIndex.value = null
}

function onNumPadUpdate(value: number) {
  if (cartStore.selectedItemIndex === null) return
  if (numPadMode.value === 'qty') {
    cartStore.updateQty(cartStore.selectedItemIndex, value)
  } else if (numPadMode.value === 'discount') {
    cartStore.updateItemDiscount(cartStore.selectedItemIndex, value)
  } else if (numPadMode.value === 'discountAmt') {
    cartStore.updateItemDiscountAmount(cartStore.selectedItemIndex, value)
  } else {
    cartStore.updateRate(cartStore.selectedItemIndex, value)
  }
}

function switchNumPadMode(mode: 'qty' | 'discount' | 'discountAmt' | 'rate') {
  numPadMode.value = mode
}

// Keyboard input for non-touch desktops
const keyboardInput = ref('')

function onKeyboardInputChange() {
  const val = parseFloat(keyboardInput.value) || 0
  onNumPadUpdate(val)
}

function closeKeyboardInput() {
  onKeyboardInputChange()
  showNumPad.value = false
}

function openPayment() {
  paymentStore.openPaymentDialog()
}

const showCustomerDetail = ref(false)
const cartScrollContainer = ref<HTMLElement | null>(null)

// Auto-scroll cart to bottom when items are added
watch(
  () => cartStore.items.length,
  () => {
    nextTick(() => {
      if (cartScrollContainer.value) {
        cartScrollContainer.value.scrollTo({
          top: cartScrollContainer.value.scrollHeight,
          behavior: 'smooth',
        })
      }
    })
  }
)

const emit = defineEmits<{
  holdOrder: []
}>()

// Group cart lines by combo_uid for rendering, preserving each line's real
// index so the existing index-based handlers (select/updateQty/remove)
// keep working unchanged. A parallel "combo instances" list isn't used —
// applyPricingRuleData() and $reset() both replace cartStore.items
// wholesale, so any separate list would drift; deriving from items here
// can't.
type CartDisplayGroup =
  | { kind: 'item'; index: number; item: CartItem }
  | {
      kind: 'combo'
      comboUid: string
      label: string
      price: number
      destination: string | null
      lines: { index: number; item: CartItem }[]
    }

const displayGroups = computed<CartDisplayGroup[]>(() => {
  const groups: CartDisplayGroup[] = []
  const comboGroups = new Map<string, Extract<CartDisplayGroup, { kind: 'combo' }>>()

  cartStore.items.forEach((item, index) => {
    if (!item.combo_uid) {
      groups.push({ kind: 'item', index, item })
      return
    }
    let group = comboGroups.get(item.combo_uid)
    if (!group) {
      // combo_label is always "{instance label} · {slot label}" (set by
      // restaurantStore.addComboToCart / create_restaurant_sale) — every
      // line in the group shares the same prefix, so any line can supply
      // the group's own label.
      const parts = (item.combo_label || item.combo || '').split(' · ')
      group = {
        kind: 'combo',
        comboUid: item.combo_uid,
        label: parts.length > 1 ? parts.slice(0, -1).join(' · ') : parts[0],
        price: 0,
        destination: item.destination ?? null,
        lines: [],
      }
      comboGroups.set(item.combo_uid, group)
      groups.push(group)
    }
    group.lines.push({ index, item })
    group.price += item.amount
  })

  return groups
})
</script>

<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-900">
    <!-- Customer section (ERPNext-style: separate area at top) -->
    <div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800 flex items-center gap-2">
      <div class="flex-1 min-w-0">
        <CustomerSelector @open-detail="showCustomerDetail = true" />
      </div>
      <!-- Mobile-only actions (held orders, mobile menu) injected by the
           parent — kept out of AppShell's own header to save vertical
           space on narrow screens. -->
      <div class="lg:hidden flex items-center gap-1 shrink-0">
        <slot name="header-actions" />
      </div>
    </div>

    <!-- Customer detail panel -->
    <CustomerDetailPanel
      v-if="showCustomerDetail && customerStore.customer"
      @close="showCustomerDetail = false"
    />

    <!-- Cart label + column headers (ERPNext-style) -->
    <div class="px-3 pt-2 pb-1.5">
      <div class="flex items-center justify-between mb-1.5">
        <div class="text-sm font-bold text-gray-900 dark:text-gray-100">{{ __('Cart') }}</div>
        <!-- Default destination for newly-added lines. Same toggle as F7 —
             see useKeyboardShortcuts/POS.vue — the model stays per-line,
             this is just a quick seed for new lines. -->
        <div v-if="restaurantStore.enabled" class="flex rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5" title="F7">
          <button
            v-for="dest in restaurantStore.config?.destinations || ['Mesa', 'Para llevar']"
            :key="dest"
            @click="restaurantStore.setDefaultDestination(dest as RestaurantDestination); cartStore.setAllItemsDestination(dest as RestaurantDestination)"
            class="rounded-md font-bold uppercase tracking-wide transition-colors"
            :class="[
              isTouchDevice ? 'px-3.5 py-2 text-xs' : 'px-2.5 py-1 text-[10px]',
              restaurantStore.defaultDestination === dest
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                : 'text-gray-500 dark:text-gray-400'
            ]"
          >
            {{ dest === 'Mesa' ? restaurantStore.labelDineIn : restaurantStore.labelTakeaway }}
          </button>
        </div>
      </div>
      <div v-if="cartStore.items.length > 0" class="flex items-center text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">
        <span class="flex-1">{{ __('Item') }}</span>
        <!-- Widths must match CartItem.vue's qtyColWidth/deleteColWidth
             (and the same 44px-on-touch rule) or the Amount column
             desyncs from the header on touch devices. -->
        <span class="text-center" :style="{ width: isTouchDevice ? '132px' : '88px' }">{{ __('Qty') }}</span>
        <span class="w-[72px] text-right">{{ __('Amount') }}</span>
        <span :style="{ width: isTouchDevice ? '44px' : '28px' }" />
      </div>
    </div>

    <!-- Cart items -->
    <div ref="cartScrollContainer" class="flex-1 overflow-y-auto px-2 py-1">
      <div
        v-if="cartStore.items.length === 0"
        class="flex flex-col items-center justify-center h-full rounded-lg bg-gray-100 dark:bg-gray-800"
      >
        <ShoppingCart :size="28" class="text-gray-300 dark:text-gray-600 mb-2" />
        <span class="text-sm font-medium text-gray-400 dark:text-gray-500">{{ __('No items in cart') }}</span>
      </div>
      <TransitionGroup v-else name="cart-item" tag="div">
        <template v-for="group in displayGroups" :key="group.kind === 'combo' ? group.comboUid : group.item.uid">
          <ComboCartGroup
            v-if="group.kind === 'combo'"
            :combo-uid="group.comboUid"
            :label="group.label"
            :price="group.price"
            :destination="group.destination"
            :notes="group.lines[0]?.item.combo_notes"
            :lines="group.lines"
            :selected-index="cartStore.selectedItemIndex"
            @select="onItemSelect"
            @remove-instance="cartStore.removeComboInstance"
            @update-qty="onUpdateComboQty"
            @toggle-destination="onToggleComboDestination"
            @toggle-line-destination="onToggleItemDestination"
            @edit-modifiers="onEditModifiers"
            @edit-combo-notes="onEditComboNotes"
          />
          <CartItemComp
            v-else
            :item="group.item"
            :index="group.index"
            :selected="cartStore.selectedItemIndex === group.index"
            @select="onItemSelect"
            @update-qty="onUpdateQty"
            @remove="onRemove"
            @toggle-destination="onToggleItemDestination"
            @edit-modifiers="onEditModifiers"
          />
        </template>
      </TransitionGroup>
    </div>

    <!-- NumPad for touch devices -->
    <Transition name="numpad">
      <div v-if="isTouchDevice && showNumPad && cartStore.selectedItemIndex !== null" class="px-2 pb-2 border-t border-gray-100 dark:border-gray-800">
        <div class="flex gap-1 my-2">
          <button
            v-for="mode in availableNumPadModes"
            :key="mode"
            @click="switchNumPadMode(mode)"
            class="flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all duration-150 uppercase tracking-wider"
            :class="numPadMode === mode
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'"
          >
            {{ mode === 'qty' ? __('Qty') : mode === 'discount' ? __('Disc%') : mode === 'discountAmt' ? __('Disc$') : __('Price') }}
          </button>
        </div>
        <NumPad
          :value="numPadValue"
          :label="numPadLabel"
          @update:value="onNumPadUpdate"
          @close="showNumPad = false"
        />
      </div>
    </Transition>

    <!-- Keyboard input for non-touch desktops -->
    <Transition name="numpad">
      <div v-if="!isTouchDevice && showNumPad && cartStore.selectedItemIndex !== null" class="px-3 py-2 border-t border-gray-100 dark:border-gray-800">
        <div class="flex gap-1 mb-2">
          <button
            v-for="mode in availableNumPadModes"
            :key="mode"
            @click="() => { switchNumPadMode(mode); const item = cartStore.items[cartStore.selectedItemIndex!]; if (item) keyboardInput = String(mode === 'qty' ? item.qty : mode === 'discount' ? item.discount_percentage : mode === 'discountAmt' ? item.discount_amount : item.rate) }"
            class="flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all duration-150 uppercase tracking-wider"
            :class="numPadMode === mode
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'"
          >
            {{ mode === 'qty' ? __('Qty') : mode === 'discount' ? __('Disc%') : mode === 'discountAmt' ? __('Disc$') : __('Price') }}
          </button>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider shrink-0">{{ numPadLabel }}</span>
          <input
            v-model="keyboardInput"
            type="number"
            step="any"
            min="0"
            @input="onKeyboardInputChange"
            @keydown.enter="closeKeyboardInput"
            class="flex-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm font-semibold text-right focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
            autofocus
          />
          <button
            @click="closeKeyboardInput"
            class="flex items-center gap-1 text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors px-2 py-1.5 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/30"
          >
            <Check :size="12" />
            {{ __('Done') }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- Totals + Actions (sticky bottom, ERPNext-style) -->
    <div class="border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
      <!-- Expandable extras -->
      <div v-if="cartStore.items.length > 0" class="px-3 pt-1.5 space-y-1">
        <InvoiceDiscount />
        <CouponCodeInput v-if="!(restaurantStore.enabled && restaurantStore.disableCouponCode)" />
        <InvoiceOptions v-if="!(restaurantStore.enabled && restaurantStore.disableMoreOptions)" />
      </div>

      <!-- Summary -->
      <div class="px-3 pt-1.5 pb-1.5">
        <CartSummary />
      </div>

      <!-- Action Buttons -->
      <div class="px-3 pb-2 flex gap-2">
        <button
          @click="emit('holdOrder')"
          :disabled="cartStore.items.length === 0"
          aria-label="Hold Order"
          class="py-2.5 px-4 rounded-lg text-sm font-bold transition-all duration-150 flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
          title="Hold Order"
        >
          <Pause :size="16" />
          <span class="hidden lg:inline">{{ __('Hold') }}</span>
        </button>
        <button
          @click="openPayment"
          :disabled="cartStore.items.length === 0 || !customerStore.customer"
          class="checkout-btn flex-1 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 flex items-center justify-center gap-2 text-white disabled:cursor-not-allowed"
          :class="cartStore.items.length > 0 && customerStore.customer
            ? 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
            : 'bg-blue-300 dark:bg-blue-800 opacity-70'"
        >
          <CreditCard :size="16" />
          {{ __('Checkout') }} {{ cartStore.items.length > 0 ? formatCurrency(cartStore.roundedTotal) : '' }}
        </button>
      </div>
    </div>

    <!-- Combo instance note dialog -->
    <NoteDialog
      v-if="comboNotesItem"
      :item-name="comboNotesItem.combo_label?.split(' · ')[0] || comboNotesItem.combo || comboNotesItem.item_name"
      :model-value="comboNotesItem.combo_notes ?? null"
      @confirm="onSaveComboNotes"
      @close="comboNotesUid = null"
    />

    <!-- Modifier picker (also carries the manual note box — notes and
         modifiers are unified into this one dialog) -->
    <ModifierPicker
      v-if="modifierPickerItem"
      :item-code="modifierPickerItem.item_code"
      :item-name="modifierPickerItem.item_name"
      :model-value="{ modifiers: modifierPickerItem.modifiers || [], notes: modifierPickerItem.notes ?? null }"
      @confirm="onSaveModifiers"
      @close="modifierPickerIndex = null"
    />
  </div>
</template>

<style scoped>
.cart-item-enter-active {
  transition: all 0.25s ease-out;
}
.cart-item-leave-active {
  transition: all 0.2s ease-in;
}
.cart-item-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
.cart-item-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
.cart-item-move {
  transition: transform 0.25s ease;
}

.numpad-enter-active {
  transition: all 0.2s ease-out;
}
.numpad-leave-active {
  transition: all 0.15s ease-in;
}
.numpad-enter-from,
.numpad-leave-to {
  opacity: 0;
  max-height: 0;
}
.numpad-enter-to,
.numpad-leave-from {
  max-height: 400px;
}
</style>
