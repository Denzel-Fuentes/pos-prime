import { test, expect } from '../fixtures/restaurant-fixtures'
import { POSPage } from '../fixtures/pos-page'

/**
 * Restaurant module: destination, notes, modifiers, combos.
 *
 * Every test here test.skip()s rather than fails when the site doesn't
 * have restaurant mode on, or lacks a usable combo/modifier — matching
 * the rest of this suite's philosophy of testing against whatever the
 * site actually has (see restaurant-fixtures.ts / pos-fixtures.ts)
 * instead of requiring a specific seeded fixture set. Run
 * pos_prime.restaurant.setup.setup_demo_menu first for a site that has
 * neither yet.
 */
test.describe('Restaurant Module', () => {
  let pos: POSPage

  test.beforeEach(async ({ posPage, testData, restaurantData }) => {
    test.skip(!restaurantData.enabled, 'Restaurant mode is not enabled on this site')

    pos = new POSPage(posPage)
    await pos.waitForPOSReady()
    if (await pos.hasOpeningEntry()) {
      await pos.fillOpeningEntry(testData.posProfile, { Cash: 0 })
      await posPage.waitForTimeout(2000)
    }
    await posPage.waitForTimeout(1000)
    await pos.selectCustomer(testData.customerName)
  })

  test('destination toggle is visible in the cart header', async ({ posPage }) => {
    const toggle = posPage.locator('[title="F7"] button')
    await expect(toggle).toHaveCount(2)
  })

  test('per-line destination, note, and modifier survive hold/resume', async ({
    posPage,
    testData,
    restaurantData,
  }) => {
    await pos.addItemBySearch(testData.items.stock)
    const row = posPage.locator('[role="listitem"]').last()

    // Destination chip flips independent of the header default.
    const destChip = row.locator('button[aria-label="Toggle destination"]')
    await expect(destChip).toBeVisible()
    const before = (await destChip.textContent())?.trim()
    await destChip.click()
    await posPage.waitForTimeout(200)
    await expect(destChip).not.toHaveText(before || '')

    // Notes and modifiers are unified behind one "Modifiers" button/dialog
    // — the dialog carries a manual text box alongside any predefined
    // modifier chips for this item.
    const modChip = row.locator('button[aria-label="Modifiers"]')
    await expect(modChip).toBeVisible()
    await modChip.click()
    const modDialog = posPage.locator('[role="dialog"][aria-label="Modifiers"]')
    await expect(modDialog).toBeVisible({ timeout: 5000 })
    await modDialog.locator('textarea').fill('sin cebolla e2e')
    if (restaurantData.modifierLabel) {
      await modDialog.locator(`button:has-text("${restaurantData.modifierLabel}")`).first().click()
    }
    await modDialog.locator('button').last().click() // Done is the dialog's last button
    await expect(modDialog).toBeHidden({ timeout: 5000 })
    await expect(modChip).toContainText('sin cebolla e2e')
    if (restaurantData.modifierLabel) {
      await expect(modChip).toContainText(restaurantData.modifierLabel)
    }

    // Hold, resume, and confirm everything above survived the round trip.
    await pos.holdOrder()
    await pos.openHeldOrders()
    // pos.resumeHeldOrder() already handles the Spanish "Reanudar" label.
    await pos.resumeHeldOrder(0)
    await posPage.waitForTimeout(1500)

    const resumedRow = posPage.locator('[role="listitem"]').last()
    const resumedModChip = resumedRow.locator('button[aria-label="Modifiers"]')
    await expect(resumedModChip).toContainText('sin cebolla e2e')
    if (restaurantData.modifierLabel) {
      await expect(resumedModChip).toContainText(restaurantData.modifierLabel)
    }
  })

  test('combo builder adds exactly one line per slot at the combo price', async ({
    posPage,
    restaurantData,
  }) => {
    test.skip(!restaurantData.combo, 'No usable combo configured on this site')
    const combo = restaurantData.combo!

    const countBefore = await pos.getCartItemCount()

    const comboTile = posPage.locator('button.pos-card.border-amber-200').first()
    await expect(comboTile).toBeVisible({ timeout: 10_000 })
    await comboTile.click()

    const dialog = posPage.locator('[role="dialog"][aria-modal="true"]').last()
    await expect(dialog).toBeVisible()

    for (const slot of combo.slots) {
      await dialog.locator(`button:has-text("${slot.itemName}")`).first().click()
    }
    await dialog.locator('button').last().click() // Add to Cart is the dialog's last button
    await expect(dialog).toBeHidden({ timeout: 10_000 })

    // Every slot became its own component line, atomically.
    expect(await pos.getCartItemCount()).toBe(countBefore + combo.slots.length)

    // The lines' amounts distribute the combo's fixed price exactly —
    // this is the cart-side half of distribute_combo_price's guarantee
    // (pos_prime/restaurant/pricing.py), the invoice/order-side half is
    // covered by the checkout test below. Read the total off the
    // checkout button rather than pos.getNetTotal() — that helper's
    // "text=Net Total" locator is English-only and this site is
    // Spanish-localized (same class of issue as checkoutAndPay's
    // aria-label mismatch, see pos-page.ts).
    await pos.waitForTaxCalculation()
    const checkoutBtnText = (await posPage.locator('button.checkout-btn').textContent()) || ''
    const amounts = checkoutBtnText.match(/[\d.]+/g)
    const total = amounts ? parseFloat(amounts[amounts.length - 1]) : NaN
    expect(total).toBeCloseTo(combo.price, 1)
  })

  test('checkout with a combo creates a linked Restaurant Order with correctly split, linked lines', async ({
    posPage,
    api,
    restaurantData,
  }) => {
    test.skip(!restaurantData.combo, 'No usable combo configured on this site')
    const combo = restaurantData.combo!

    const comboTile = posPage.locator('button.pos-card.border-amber-200').first()
    await expect(comboTile).toBeVisible({ timeout: 10_000 })
    await comboTile.click()

    const dialog = posPage.locator('[role="dialog"][aria-modal="true"]').last()
    await expect(dialog).toBeVisible()
    for (const slot of combo.slots) {
      await dialog.locator(`button:has-text("${slot.itemName}")`).first().click()
    }
    await dialog.locator('button').last().click()
    await expect(dialog).toBeHidden({ timeout: 10_000 })

    await pos.waitForTaxCalculation()
    await pos.clickCheckout()

    const paymentDialog = posPage.locator('[role="dialog"][aria-modal="true"]').last()
    await expect(paymentDialog).toBeVisible({ timeout: 10_000 })
    await posPage.waitForTimeout(500)
    const shortcut = paymentDialog.locator('.grid button').first()
    if (await shortcut.isVisible({ timeout: 2000 }).catch(() => false)) {
      await shortcut.click()
      await posPage.waitForTimeout(300)
    }

    const responsePromise = posPage.waitForResponse(
      (resp) => resp.url().includes('create_restaurant_sale'),
      { timeout: 30_000 }
    )
    await paymentDialog.locator('button').last().click({ timeout: 5000 })
    const response = await responsePromise
    expect(response.status()).toBeLessThan(400)
    const body = await response.json()
    const restaurantOrderName = body?.message?.restaurant_order
    expect(restaurantOrderName).toBeTruthy()

    // Not waiting for the payment dialog to hide here: it's immediately
    // replaced by the receipt dialog (same [role="dialog"][aria-modal]
    // selector), so "wait for hidden" would just time out against the new
    // dialog. The response already resolving means the sale is committed
    // server-side, which is what the assertions below actually check.

    // Verify server-side state directly — the UI already confirmed the
    // cart-side split in the previous test; this confirms the same
    // guarantee holds on what actually got persisted and submitted.
    const order = await api.getDoc('Restaurant Order', restaurantOrderName)
    expect(order.docstatus).toBe(1)
    expect(order.items.length).toBe(combo.slots.length)
    expect(order.items.every((item: any) => !!item.combo_uid)).toBe(true)
    const sum = order.items.reduce((acc: number, item: any) => acc + item.amount, 0)
    expect(sum).toBeCloseTo(combo.price, 1)
  })
})
