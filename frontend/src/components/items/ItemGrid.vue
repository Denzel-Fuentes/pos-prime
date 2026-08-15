<!-- Copyright (c) 2026, Ravindu Gajanayaka -->
<!-- Licensed under GPLv3. See license.txt -->

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { useItemsStore } from '@/stores/items'
import { useCartStore } from '@/stores/cart'
import { useSettingsStore } from '@/stores/settings'
import { useRestaurantStore } from '@/stores/restaurant'
import { useBarcodeScanner } from '@/composables/useBarcodeScanner'
import ItemCard from './ItemCard.vue'
import ItemSearch from './ItemSearch.vue'
import ItemGroupFilter from './ItemGroupFilter.vue'
import BatchSerialSelector from './BatchSerialSelector.vue'
import VariantPickerDialog from './VariantPickerDialog.vue'
import CameraScanner from '@/components/scanner/CameraScanner.vue'
import ComboCard from '@/components/restaurant/ComboCard.vue'
import ComboBuilderDialog from '@/components/restaurant/ComboBuilderDialog.vue'
import { Package, PanelLeftClose, PanelLeftOpen, Minus, Plus } from 'lucide-vue-next'
import { useDeskMode } from '@/composables/useDeskMode'
import type { Item, CartItem, RestaurantCombo } from '@/types'

const { isDeskMode } = useDeskMode()

const itemsStore = useItemsStore()
const cartStore = useCartStore()
const settingsStore = useSettingsStore()
const restaurantStore = useRestaurantStore()
const scrollContainer = ref<HTMLElement | null>(null)
const showCameraScanner = ref(false)
const showCategories = ref(localStorage.getItem('pos_show_categories') !== 'false')

function toggleCategories() {
  showCategories.value = !showCategories.value
  localStorage.setItem('pos_show_categories', String(showCategories.value))
}

// Column count is a per-device preference (like showCategories above)
// rather than a responsive auto-fit: a fixed count is what lets a cashier
// pick the density that matches their screen/finger size once and keep it,
// instead of the grid silently reflowing as the cart panel resizes.
const MIN_COLUMNS = 2
const MAX_COLUMNS = 6
const DEFAULT_COLUMNS = 3

function loadColumnCount() {
  const saved = Number(localStorage.getItem('pos_item_grid_columns'))
  return saved >= MIN_COLUMNS && saved <= MAX_COLUMNS ? saved : DEFAULT_COLUMNS
}

const columnCount = ref(loadColumnCount())

function setColumnCount(count: number) {
  columnCount.value = Math.min(MAX_COLUMNS, Math.max(MIN_COLUMNS, count))
  localStorage.setItem('pos_item_grid_columns', String(columnCount.value))
}

onMounted(() => {
  itemsStore.fetchItemGroups()
  itemsStore.fetchAllItems()
})

/** One grid cell — combos and items share the same grid (and therefore the
 * same virtualizer rows), so they travel through it as a tagged union. */
type GridEntry =
  | { kind: 'combo'; key: string; combo: RestaurantCombo }
  | { kind: 'item'; key: string; item: Item }

// Combos aren't real Items: they're in no Item Group and don't participate
// in the store's Fuse.js catalog search. So they're listed only in the
// unfiltered grid, and matched here against the search box by name/print
// label (N is always small — no need for fuzzy matching).
const visibleCombos = computed(() => {
  if (!restaurantStore.enabled) return []
  if (itemsStore.selectedGroup && itemsStore.selectedGroup !== 'All Item Groups') return []
  const term = itemsStore.searchTerm?.trim().toLowerCase()
  if (!term) return restaurantStore.combos
  return restaurantStore.combos.filter(
    (c) => c.combo_name.toLowerCase().includes(term) || c.print_label?.toLowerCase().includes(term)
  )
})

// Combos first, then the catalog — a combo is the headline offer of a
// restaurant menu, and pinning them to the top keeps them reachable without
// scrolling however long the item list is.
const entries = computed<GridEntry[]>(() => [
  ...visibleCombos.value.map((combo) => ({
    kind: 'combo' as const,
    key: `combo:${combo.name}`,
    combo,
  })),
  ...itemsStore.filteredItems.map((item) => ({
    kind: 'item' as const,
    key: `item:${item.item_code}`,
    item,
  })),
])

// Group into rows for virtual scrolling
const rows = computed(() => {
  const cols = columnCount.value
  const result: GridEntry[][] = []
  for (let i = 0; i < entries.value.length; i += cols) {
    result.push(entries.value.slice(i, i + cols))
  }
  return result
})

const virtualizer = useVirtualizer(
  computed(() => ({
    count: rows.value.length,
    getScrollElement: () => scrollContainer.value,
    estimateSize: () => settingsStore.hideImages ? 70 : (isDeskMode.value ? 200 : 215),
    overscan: 5,
  }))
)

// Default destination for any new line — the header/F7 toggle seeds this;
// null (not "Mesa") when restaurant mode is off, so non-restaurant sites
// never send a destination field at all.
function currentDestination() {
  return restaurantStore.enabled ? restaurantStore.defaultDestination : null
}

// Auto-add to cart if setting enabled and exactly 1 item matches
watch(
  () => [itemsStore.searchTerm, itemsStore.filteredItems.length],
  () => {
    if (
      settingsStore.autoAddItemToCart &&
      itemsStore.filteredItems.length === 1 &&
      itemsStore.searchTerm
    ) {
      const err = cartStore.addItem(
        itemsStore.filteredItems[0],
        settingsStore.validateStockOnSave,
        currentDestination()
      )
      if (err) showStockError(err)
      itemsStore.setSearchTerm('')
    }
  }
)

function onSearchChange(term: string) {
  itemsStore.setSearchTerm(term)
}

function onGroupSelect(group: string) {
  itemsStore.setSelectedGroup(group)
}

// Batch/Serial selector state
const batchSerialItem = ref<Item | null>(null)

// Variant picker state (template item clicked, awaiting a variant choice)
const variantPickerItem = ref<Item | null>(null)

// Combo builder state
const comboBeingBuilt = ref<RestaurantCombo | null>(null)

function onComboSelect(combo: RestaurantCombo) {
  comboBeingBuilt.value = combo
}

function onComboConfirm() {
  comboBeingBuilt.value = null
}

function showStockError(msg: string) {
  const frappe = (window as any).frappe
  if (frappe?.show_alert) {
    frappe.show_alert({ message: msg, indicator: 'orange' }, 3)
  }
}

function onItemSelect(item: Item) {
  if (item.has_variants) {
    variantPickerItem.value = item
    return
  }
  if (item.has_batch_no || item.has_serial_no) {
    // Show batch/serial selector dialog
    batchSerialItem.value = item
    return
  }
  const err = cartStore.addItem(item, settingsStore.validateStockOnSave, currentDestination())
  if (err) showStockError(err)
}

function onVariantPicked(variant: Item) {
  variantPickerItem.value = null
  onItemSelect(variant)
}

function onBatchSerialConfirm(batchNo: string | null, serialNo: string | null) {
  const item = batchSerialItem.value
  if (!item) return

  const overrides: Partial<CartItem> = { destination: currentDestination() }
  // For serial items, serials may span multiple batches — auto-split.
  // This case shouldn't happen with current UI (batch is required first),
  // but handle it for safety.
  if (serialNo && item.has_batch_no && item.has_serial_no && !batchNo) {
    overrides.serial_no = serialNo
  } else {
    overrides.batch_no = batchNo
    overrides.serial_no = serialNo
  }
  // Set qty from serial count if multiple serials were selected
  if (serialNo) {
    const serialCount = serialNo.split('\n').filter((s) => s.trim()).length
    if (serialCount > 1) overrides.qty = serialCount
  }

  const { error } = cartStore.addConfiguredItem(item, overrides, settingsStore.validateStockOnSave)
  if (error) showStockError(error)
  batchSerialItem.value = null
}

// Hardware barcode scanner integration
async function handleBarcodeScan(barcode: string) {
  const result = await itemsStore.searchByBarcode(barcode)
  if (result && result.item_code) {
    const destination = currentDestination()
    // Find item in full list or create minimal item for cart
    const existingItem = itemsStore.allItems.find((i) => i.item_code === result.item_code)
    if (existingItem) {
      const err = cartStore.addItem(existingItem, settingsStore.validateStockOnSave, destination)
      if (err) { showStockError(err); return }
    } else {
      // Add as minimal item — the backend will resolve full details
      const err = cartStore.addItem({
        item_code: result.item_code,
        item_name: result.item_name || result.item_code,
        rate: result.rate || 0,
        actual_qty: result.actual_qty || 0,
        is_stock_item: result.is_stock_item ?? true,
        stock_uom: result.stock_uom || 'Nos',
        description: '',
        item_group: '',
        image: null,
        currency: settingsStore.currency,
        has_batch_no: !!result.batch_no || !!result.has_batch_no,
        has_serial_no: !!result.serial_no || !!result.has_serial_no,
        brand: null,
        weight_per_unit: null,
        weight_uom: null,
        barcode: result.barcode || null,
        item_tax_template: null,
        is_product_bundle: false,
        has_variants: false,
        variant_of: null,
      }, settingsStore.validateStockOnSave, destination)
      if (err) { showStockError(err); return }

      // If scanned item has batch/serial info, update the cart item
      if (result.batch_no || result.serial_no) {
        const lastIndex = cartStore.items.length - 1
        cartStore.updateItemBatchSerial(
          lastIndex,
          result.batch_no || null,
          result.serial_no || null
        )
      }
    }

    // Apply barcode-specific UOM if returned by backend
    if (result.barcode_uom) {
      const lastIndex = cartStore.items.length - 1
      cartStore.updateItemUom(lastIndex, result.barcode_uom, result.barcode_conversion_factor || 1)
    }
  }
}

useBarcodeScanner(handleBarcodeScan)

function onCameraScan(value: string) {
  showCameraScanner.value = false
  handleBarcodeScan(value)
}

// Display label: show selected group or "All Items"
const headerLabel = computed(() => {
  return itemsStore.selectedGroup === 'All Item Groups'
    ? __('All Items')
    : itemsStore.selectedGroup || __('All Items')
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Filter section — ERPNext-style: label + search + category toggle -->
    <div class="flex items-center gap-2 px-3 py-2">
      <!-- Section label (like ERPNext's "All Items") -->
      <div class="hidden sm:flex items-center gap-2 shrink-0">
        <button
          v-if="itemsStore.itemGroups.length > 1"
          class="hidden lg:flex items-center justify-center shrink-0 w-9 h-9 rounded-md text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          :title="showCategories ? __('Hide categories') : __('Show categories')"
          @click="toggleCategories"
        >
          <PanelLeftClose v-if="showCategories" :size="16" />
          <PanelLeftOpen v-else :size="16" />
        </button>
        <span class="text-base font-bold text-gray-900 dark:text-gray-100 whitespace-nowrap">{{ headerLabel }}</span>
      </div>

      <!-- Item grid column count (per-device preference, see loadColumnCount) -->
      <div class="flex items-center gap-0.5 shrink-0 rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5" :title="__('Columns')">
        <button
          @click="setColumnCount(columnCount - 1)"
          :disabled="columnCount <= MIN_COLUMNS"
          :aria-label="__('Fewer columns')"
          class="w-7 h-7 rounded-md flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <Minus :size="13" />
        </button>
        <span class="w-4 text-center text-xs font-bold text-gray-700 dark:text-gray-300">{{ columnCount }}</span>
        <button
          @click="setColumnCount(columnCount + 1)"
          :disabled="columnCount >= MAX_COLUMNS"
          :aria-label="__('More columns')"
          class="w-7 h-7 rounded-md flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <Plus :size="13" />
        </button>
      </div>

      <!-- Search -->
      <ItemSearch
        class="flex-1"
        :model-value="itemsStore.searchTerm"
        @update:model-value="onSearchChange"
        @open-scanner="showCameraScanner = true"
      />
    </div>

    <!-- Mobile horizontal categories (tablets and up use the sidebar below —
         a fixed vertical list is faster to scan/tap than a scrolling strip) -->
    <ItemGroupFilter
      v-if="itemsStore.itemGroups.length > 1"
      mode="mobile"
      class="lg:hidden"
      :groups="itemsStore.itemGroups"
      :selected="itemsStore.selectedGroup"
      @select="onGroupSelect"
    />

    <div class="flex flex-1 overflow-hidden">
      <!-- Desktop sidebar categories -->
      <ItemGroupFilter
        v-if="itemsStore.itemGroups.length > 1 && showCategories"
        mode="desktop"
        class="hidden lg:flex"
        :groups="itemsStore.itemGroups"
        :selected="itemsStore.selectedGroup"
        @select="onGroupSelect"
      />

      <div
        ref="scrollContainer"
        class="flex-1 overflow-y-auto"
      >
        <div
          v-if="itemsStore.loading && itemsStore.allItems.length === 0"
          class="flex items-center justify-center py-12"
        >
          <div class="text-gray-400 dark:text-gray-500 text-sm">{{ __('Loading items...') }}</div>
        </div>

        <div
          v-else-if="entries.length === 0"
          class="flex flex-col items-center justify-center py-12"
        >
          <Package class="text-gray-300 dark:text-gray-600 mb-3" :size="48" />
          <p class="text-gray-500 dark:text-gray-400 text-sm">{{ __('No items found') }}</p>
        </div>

        <!-- Virtual scrolling grid -->
        <div
          v-else
          :style="{ height: `${virtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }"
        >
          <div
            v-for="virtualRow in virtualizer.getVirtualItems()"
            :key="virtualRow.index"
            :ref="(el) => { if (el) virtualizer.measureElement(el as Element) }"
            :data-index="virtualRow.index"
            :style="{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`,
            }"
            style="padding-left: var(--padding-sm, 8px); padding-right: var(--padding-sm, 8px);"
          >
            <div
              class="grid pb-2"
              style="gap: var(--margin-sm, 8px);"
              :style="{ gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))` }"
            >
              <template v-for="entry in rows[virtualRow.index]" :key="entry.key">
                <ComboCard
                  v-if="entry.kind === 'combo'"
                  :combo="entry.combo"
                  @select="onComboSelect"
                />
                <ItemCard v-else :item="entry.item" @select="onItemSelect" />
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Camera scanner overlay -->
    <CameraScanner
      v-if="showCameraScanner"
      @scan="onCameraScan"
      @close="showCameraScanner = false"
    />

    <!-- Batch/Serial selector dialog -->
    <BatchSerialSelector
      v-if="batchSerialItem"
      :item-code="batchSerialItem.item_code"
      :item-name="batchSerialItem.item_name"
      :has-batch-no="batchSerialItem.has_batch_no"
      :has-serial-no="batchSerialItem.has_serial_no"
      @confirm="onBatchSerialConfirm"
      @close="batchSerialItem = null"
    />

    <!-- Variant picker dialog -->
    <VariantPickerDialog
      v-if="variantPickerItem"
      :item="variantPickerItem"
      @select="onVariantPicked"
      @close="variantPickerItem = null"
    />

    <!-- Combo builder dialog -->
    <ComboBuilderDialog
      v-if="comboBeingBuilt"
      :combo="comboBeingBuilt"
      @confirm="onComboConfirm"
      @close="comboBeingBuilt = null"
    />
  </div>
</template>
