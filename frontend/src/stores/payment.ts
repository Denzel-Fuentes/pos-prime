// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { call } from 'frappe-ui'
import type { PaymentEntry, POSInvoice, InvoiceOptions } from '@/types'
import { useRestaurantStore } from '@/stores/restaurant'

export const usePaymentStore = defineStore('payment', () => {
  const payments = ref<PaymentEntry[]>([])
  const activePaymentMethod = ref<string>('')
  const showPaymentDialog = ref(false)
  const submitting = ref(false)
  const lastInvoice = ref<POSInvoice | null>(null)
  const error = ref<string | null>(null)
  // The method currently holding an amount we filled in ourselves (never
  // typed by the cashier).  Switching away from it hands its amount to the
  // newly picked method instead of leaving both populated; any manual edit
  // clears the mark so a deliberate split payment is left alone.
  const autoFilledMethod = ref<string | null>(null)

  const totalPaid = computed(() =>
    payments.value.reduce((sum, p) => sum + p.amount, 0)
  )

  function initializePayments(
    paymentMethods: { mode_of_payment: string; default: boolean }[],
    grandTotal: number,
    disableGrandTotalToDefaultMop: boolean
  ) {
    // Initialize all payment methods with 0 amount
    payments.value = paymentMethods.map((pm) => ({
      mode_of_payment: pm.mode_of_payment,
      amount: 0,
    }))

    // Set active to default method
    const defaultMethod = paymentMethods.find((p) => p.default)
    activePaymentMethod.value =
      defaultMethod?.mode_of_payment || paymentMethods[0]?.mode_of_payment || 'Cash'

    // Pre-fill default method with grand total unless disabled
    autoFilledMethod.value = null
    if (!disableGrandTotalToDefaultMop && grandTotal > 0) {
      const defaultPayment = payments.value.find(
        (p) => p.mode_of_payment === activePaymentMethod.value
      )
      if (defaultPayment) {
        defaultPayment.amount = grandTotal
        autoFilledMethod.value = defaultPayment.mode_of_payment
      }
    }
  }

  function writeAmount(modeOfPayment: string, amount: number) {
    const value = Math.max(0, Math.round(amount * 100) / 100)
    const existing = payments.value.find(
      (p) => p.mode_of_payment === modeOfPayment
    )
    if (existing) {
      existing.amount = value
    } else {
      payments.value.push({ mode_of_payment: modeOfPayment, amount: value })
    }
  }

  function setPaymentAmount(modeOfPayment: string, amount: number) {
    // A hand-typed amount is a deliberate choice — stop treating it as ours.
    if (autoFilledMethod.value === modeOfPayment) {
      autoFilledMethod.value = null
    }
    writeAmount(modeOfPayment, amount)
  }

  function setActivePaymentMethod(mode: string, grandTotal?: number) {
    if (activePaymentMethod.value === mode) return

    // Hand over an untouched auto-filled amount rather than leaving it
    // behind — otherwise the cashier has to clear it by hand and, if they
    // forget, the sale records two payment rows and a bogus change.
    if (autoFilledMethod.value && autoFilledMethod.value !== mode) {
      writeAmount(autoFilledMethod.value, 0)
      autoFilledMethod.value = null
    }

    activePaymentMethod.value = mode

    if (grandTotal === undefined) return

    // Fill the new method with whatever is still owed: the whole total when
    // nothing else is tendered, or just the shortfall when the cashier
    // already typed a partial amount elsewhere (e.g. 80 cash of 100 -> 20).
    const current = payments.value.find((p) => p.mode_of_payment === mode)
    if (current && current.amount > 0) return
    const remaining = Math.round((grandTotal - totalPaid.value) * 100) / 100
    if (remaining > 0) {
      writeAmount(mode, remaining)
      autoFilledMethod.value = mode
    }
  }

  function changeAmount(grandTotal: number) {
    return Math.round(Math.max(0, totalPaid.value - grandTotal) * 100) / 100
  }

  function remainingAmount(grandTotal: number) {
    return Math.round(Math.max(0, grandTotal - totalPaid.value) * 100) / 100
  }

  function writeOffAmount(grandTotal: number, writeOffLimit: number) {
    const remaining = remainingAmount(grandTotal)
    if (remaining > 0 && remaining <= writeOffLimit) {
      return remaining
    }
    return 0
  }

  async function submitInvoice(args: {
    customer: string
    pos_profile: string
    items: { item_code: string; qty: number; rate: number; [key: string]: any }[]
    payments: PaymentEntry[]
    taxes?: string
    additional_discount_percentage?: number
    discount_amount?: number
    apply_discount_on?: string
    coupon_code?: string
    loyalty_points?: number
    loyalty_program?: string
    redeem_loyalty_points?: boolean
    loyalty_redemption_account?: string
    loyalty_redemption_cost_center?: string
    is_return?: boolean
    return_against?: string
  } & Partial<InvoiceOptions>) {
    submitting.value = true
    try {
      // Restaurant mode always routes through create_restaurant_sale, even
      // for a cart with no combos in it — it's also what creates the
      // Restaurant Order that carries every line's destination (and, once
      // wired, notes/modifiers), which plain create_pos_invoice knows
      // nothing about.
      const restaurantStore = useRestaurantStore()
      const method = restaurantStore.enabled
        ? 'pos_prime.api.restaurant.create_restaurant_sale'
        : 'pos_prime.api.invoices.create_pos_invoice'
      const data = await call(method, args)
      lastInvoice.value = data
      return data
    } catch (e) {
      error.value = 'Failed to submit invoice'
      throw e
    } finally {
      submitting.value = false
    }
  }

  function openPaymentDialog() {
    showPaymentDialog.value = true
  }

  function closePaymentDialog() {
    showPaymentDialog.value = false
  }

  function $reset() {
    payments.value = []
    activePaymentMethod.value = ''
    autoFilledMethod.value = null
    showPaymentDialog.value = false
    submitting.value = false
    lastInvoice.value = null
    error.value = null
  }

  return {
    payments,
    activePaymentMethod,
    autoFilledMethod,
    showPaymentDialog,
    submitting,
    lastInvoice,
    error,
    totalPaid,
    initializePayments,
    setPaymentAmount,
    setActivePaymentMethod,
    changeAmount,
    remainingAmount,
    writeOffAmount,
    submitInvoice,
    openPaymentDialog,
    closePaymentDialog,
    $reset,
  }
})
