# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

POS Prime is a custom Frappe app (`pos_prime`) that replaces ERPNext's built-in Point of Sale with a Vue 3 SPA. It has two halves that live in one repo:

- **Backend** (`pos_prime/`) — a Frappe Python app: whitelisted API endpoints under `pos_prime/api/*.py`, hooks in `pos_prime/hooks.py`, a Desk page (`pos_prime/pos_prime/page/pos_terminal`), and a website route (`pos_prime/www/pos_prime.*`) that serves the SPA.
- **Frontend** (`frontend/`) — Vue 3 + TypeScript + Pinia + Tailwind, built with Vite, using `frappe-ui` for the Frappe API client.

**Core rule (also stated in CONTRIBUTING.md): outside the restaurant module, POS Prime makes zero modifications to ERPNext's schema.** The base app has no custom doctypes and no custom fields — `pos_prime/pos_prime/` originally contained only a workspace, a Desk page, and number cards, and all data was read/written through ERPNext's standard doctypes (POS Invoice, POS Opening/Closing Entry, POS Profile, Item, Item Price, Customer, Bin, etc.).

**Deliberate, scoped exception: the restaurant module.** This fork adds a restaurant/pensión extension (dine-in vs takeaway per line, kitchen notes, free modifiers, configurable combos, kitchen ticket printing, combo reporting) that **does** add its own doctypes under `pos_prime/pos_prime/doctype/` (`Restaurant Order`, `Restaurant Combo`, `Restaurant Modifier`, etc.) and a handful of `pos_prime_*` custom fields on `POS Invoice`/`POS Invoice Item`. This was a conscious tradeoff: POS Prime's drafts are real `POS Invoice` documents with `docstatus=0`, so per-line restaurant data (destination/notes/combo linkage) has to survive on the invoice item itself or holding an order with a combo and resuming it silently loses that data. The exception is scoped to this module — don't take it as license to add unrelated custom fields elsewhere, and still prefer standard ERPNext doctypes for anything that isn't restaurant-specific.

This repo does **not** contain a Frappe bench — there's no `sites/`, no MariaDB/Redis, and the backend cannot run standalone. It must be installed into an existing bench (`bench get-app` + `bench --site <site> install-app pos_prime`) to do anything.

## Commands

### Frontend (`frontend/`)
```bash
yarn install       # or npm install
yarn dev            # vite dev server (proxies API calls to the Frappe backend)
yarn build           # vite build — outputs into pos_prime/public/frontend (consumed by pos_prime/www/pos_prime.html)
yarn typecheck        # vue-tsc --noEmit
yarn test              # playwright, all 3 version projects
yarn test:v14 / test:v15 / test:v16   # single ERPNext version
yarn test:report        # open the last playwright HTML report
```
E2E tests (`frontend/e2e/tests/`) run against **live, already-running Frappe/ERPNext instances**, not mocks — `playwright.config.ts` points each project (`v14`, `v15`, `v16`) at a different `baseURL` (default `http://pos.localhost:8000`, `http://v14.localhost:8001`, `http://v16.localhost:8002`, overridable via `V14_URL`/`V15_URL`/`V16_URL`). A real site with `pos_prime` installed and test data (POS Profile, items, a customer) must be reachable before running them.

### Backend (`pos_prime/`)
Runs through `bench` from inside the bench directory, not from this repo root:
```bash
bench --site <site> install-app pos_prime
bench --site <site> migrate
bench --site <site> console        # ipython shell with frappe/erpnext/pos_prime pre-imported
```
Linting is `ruff` (see `pyproject.toml` — tabs, double quotes, line-length 110, target py310) and is normally invoked via pre-commit (`.pre-commit-config.yaml`), which also runs `ruff-format`, `prettier` (js/vue/scss) and `eslint` (js only — `.eslintrc`) on the frontend/legacy JS.

There is no generic backend test command — `pos_prime/test_all_pricing_rules.py` is a standalone verification script hardcoded to specific site data (`POS_PROFILE = "Spare Parts - Weligama"`, a specific customer), meant to be run manually against a bench with that data present, not a reusable pytest suite.

## Architecture

### Standalone vs Desk mode (frontend mounting)
The same built SPA serves two very different contexts, decided at runtime in `frontend/src/main.ts`:
- **Desk mode**: mounts into `#pos-prime-app` when embedded inside Frappe Desk at `/app/pos-terminal` (or `/desk/pos-terminal` on v16+). Router uses `createMemoryHistory()` — the browser URL never changes.
- **Standalone mode**: mounts into `#app` only when `window.location.pathname` starts with `/pos-prime`. Router uses `createWebHistory('/pos-prime')`, so all routes are relative to that base (e.g. the POS view is `/pos-prime/`, not `/`). Hitting the frontend dev server at bare `/` will always render blank — there's nothing to mount there.

`frontend/vite.config.ts` has a build-only plugin (`injectFrappeContext`) that rewrites the built `index.html` with Jinja (`{{ }}`) placeholders — CSRF token, desk theme, favicon/title from Website Settings, and a redirect script that sends non-standalone `/pos-prime/*` paths to the Desk page. This only applies at `apply: 'build'` time; the raw HTML is written into `pos_prime/www/pos_prime.html`, which Frappe then renders through `pos_prime/www/pos_prime.py`'s `get_context` (this is also where the v14/v15 `/app` vs v16 `/desk` prefix is decided, via `frappe.__version__`).

### Multi-version compatibility (v14 / v15 / v16)
The app targets three ERPNext major versions concurrently (`required_apps`/`tool.bench.frappe-dependencies` allow `>=14,<17`), and this shapes a lot of the backend and frontend code. Known divergences (see README "Compatibility" section for the full table):
- Store credit / partial payments: work with no extra config on v14; v15/v16 require `Allow Partial Payment` enabled on the POS Profile.
- Serial/batch: v14 uses legacy `serial_no`/`batch_no` fields; v15/v16 use `serial_and_batch_bundle`. Backend code checks for the field's existence via `frappe.get_meta(doctype).has_field(...)` rather than branching on version numbers directly (see `pos_prime/api/_utils.py`).
- `campaign` was renamed to `utm_campaign` in v16 on both `POS Profile` and `POS Invoice` (`set_campaign_from_profile` in `_utils.py` tries both).
- POS Closing Entry references invoices via `pos_transactions` (v14/v15) vs `pos_invoices` (v16).
- Desk URL prefix: `/app/` (v14/v15) vs `/desk/` (v16+).

When touching any code that reads/writes these fields, check for the field's existence rather than assuming a schema, matching the existing pattern.

### Backend API layer (`pos_prime/api/`)
One module per concern (`pos_session.py`, `items.py`, `invoices.py`, `payments.py`, `orders.py`, `drafts.py`, `customers.py`, `customer_profile.py`, `addresses.py`, `loyalty.py`, `stock.py`, `taxes.py`), all `@frappe.whitelist()` functions. `_utils.py` holds cross-cutting helpers:
- `validate_pos_access(pos_profile=None)` — call this at the top of any endpoint; checks `POS Invoice` read permission plus, if a profile is given, that the user is in its `applicable_for_users` (empty list = everyone allowed).
- `build_item_dict` / `set_invoice_optional_fields` — translate request payloads into POS Invoice (Item) field dicts, applying POS Profile fallbacks.
- `format_invoice_response` / `format_invoice_item` — the canonical shape the frontend expects back for an invoice; keep these in sync when adding fields either side.
- Product Bundle helpers (`get_product_bundle_items`, `validate_bundle_stock`, `get_bundle_availability`) — bundles are resolved to their components for stock checks since ERPNext doesn't track bundle stock directly.

### Frontend structure (`frontend/src/`)
- `stores/` — one Pinia store per domain: `cart`, `items`, `customer`, `customerDisplay`, `drafts`, `orders`, `payment`, `posSession`, `session`, `settings`, `restaurant`. `posSession` gates shift-scoped routes (see `router.ts`'s `requiresShift` meta + `beforeEach` guard, which redirects to `OpenShift` if there's no open POS Opening Entry).
- `composables/` — hardware/UX integrations: `useBarcodeScanner`, `useSerialDisplay` + `useBroadcastDisplay` (customer pole display, both VFD-serial and second-screen variants), `usePaymentTerminal`, `useKioskMode`, `useKeyboardShortcuts` (F1–F10, F7 for restaurant destination), `useFocusTrap`, `useRTL`, `useTouchDevice`.
- `views/` — one per route: `POS`, `OpenShift`, `CloseShift`, `Orders`, `CustomerPoleDisplay` (`/display`), `CustomerDisplay` (`/customers`, `/customers/:id`), `SelfCheckout` (`/kiosk`).
- Path alias `@` → `frontend/src` (see `vite.config.ts` / `tsconfig.json`).

### Restaurant module (`pos_prime/restaurant/`, `pos_prime/api/restaurant.py`)

A dine-in/takeaway extension: per-line destination (Mesa/Para llevar), free-text kitchen notes, free modifiers, configurable combos ("Completo" = pick one item from each of N slots at a fixed price), kitchen ticket (comanda) printing over ESC/POS, daily dish availability gated at shift-open, and combo-aware reports. Gated behind `Restaurant Settings.enable_restaurant_mode` (off by default) — every restaurant UI surface is conditional on `restaurantStore.enabled`, and disabled sites see zero behavior change.

- **Doctypes** (`pos_prime/pos_prime/doctype/restaurant_*`, listed in the exception noted above): `Restaurant Combo` (+ `Restaurant Combo Slot`), `Restaurant Modifier` (+ `Restaurant Modifier Group` and its two Table MultiSelect child doctypes), `Restaurant Printer`, `Restaurant Daily Menu Item Group` (Table MultiSelect child of `Restaurant Settings.daily_menu_item_groups`), `Restaurant Opening Entry Item` (Table MultiSelect child of the `pos_prime_available_items` custom field on `POS Opening Entry`), `Restaurant Settings` (Single), and the transactional `Restaurant Order` (+ `Restaurant Order Combo`/`Item`/`Modifier`), submitted alongside its POS Invoice inside `create_restaurant_sale` — never before. `Restaurant Order Item.combo_uid` is what the whole reporting layer depends on: empty means sold individually, set means it's one component of the combo instance sharing that uid.
- **Daily dish availability ("platos del dia")**: Restaurant Settings can flag specific Item Groups (e.g. Segundos, Sopas, Refrescos) as requiring an explicit daily pick — `OpenShift.vue` then shows a picker for those groups' items, and the choice is written onto the new `POS Opening Entry` via `pos_prime_available_items`. Enforcement is hide-only and lives entirely server-side in `pos_prime/api/items.py` (`get_items`/`search_barcode`), via `pos_prime/restaurant/daily_menu.py::get_daily_menu_gate` — looked up from the caller's current open shift, so it applies uniformly across the item grid, barcode scan, and kiosk/self-checkout without any of those call sites needing to know about it. Item Groups not listed under Restaurant Settings' Daily Menu section are completely unaffected. `items.py` only reaches into the restaurant layer via a guarded, lazily-imported call (never a top-level import) so it stays behaviorally identical on non-restaurant sites and avoids a circular import back into `restaurant.py`, which already imports the other way.
- **Combo pricing is backend-only and authoritative** (`pos_prime/restaurant/pricing.py::split_combo_price`) — splits a combo's fixed price across its components in integer minor units, so the split always sums to exactly the combo price. Three methods, picked by `Restaurant Combo.pricing_method` falling back to `Restaurant Settings.default_combo_pricing_method`: `Proporcional` (largest-remainder over list prices — `distribute_combo_price`, still the primitive the others build on), `Margen alto` (components keep their list price and the slots with a `Restaurant Combo Slot.discount_order` absorb the discount in that order, flooring at 0 and cascading on — or going negative when `allow_negative_component` is set), and `Mixto` (protected slots keep their list price, the remainder is split proportionally among the absorbing ones). A method with no absorber configured falls back to proportional rather than mis-pricing; `Restaurant Combo.validate` is what stops that configuration from being saved in the first place. The frontend only ever previews a split via `preview_combo`; `create_restaurant_sale` recomputes from scratch server-side regardless of what the client sent.
- **`create_restaurant_sale`** is the one atomic entry point for a restaurant-mode sale (routed to instead of `create_pos_invoice` whenever `restaurantStore.enabled`, see `frontend/src/stores/payment.ts`): validates every combo instance's slot selections, builds the POS Invoice via `invoices.py`'s internal `_create_pos_invoice_doc`, then builds and submits the linked `Restaurant Order` in the same request. Atomicity relies on Frappe's implicit per-request transaction (`submit()` doesn't commit) — nothing on this path calls `frappe.db.commit()`.
- **Kitchen ticket printing** (`escpos.py` builds raw ESC/POS bytes; `printing.py` owns the socket connection and ticket layout) always runs after the sale already committed (`frappe.enqueue(..., enqueue_after_commit=True)`) — an unreachable printer can never revert or block a sale, it only ever changes `Restaurant Order.comanda_status` (`Not Printed` → `Printed`/`Failed`/`Not Required`). `Not Required` means no enabled `Restaurant Printer` matched the role (`Comanda (Cocina)` for the kitchen, `Recibo (Caja)` for the till receipt) — auto-printing is entirely driven by those records existing, so a site with none silently falls back to the frontend's manual print button. Note `Printed` under `delivery_mode = "Puente Android"` only means the job was published over realtime to the bridge user, not that paper came out.
- **Ticket layout can move out of Python entirely**: `Restaurant Printer.print_format` optionally points at a Print Format with Raw Printing on (`Restaurant Order` for a kitchen printer, `POS Invoice` for a till one — enforced in the doctype's `validate`), and `restaurant/ticket_template.py` renders its Raw Commands through Jinja instead of running the built-in layout. The template owns only the content: EscposBuilder still emits the init/codepage prologue and the feed/cut/drawer epilogue, so `cut_paper`/`cash_drawer_pulse`/`copies` behave the same either way. Templates get control-code constants (`CENTER`, `BOLD`, `BIG`…) and helpers (`row`, `sep`, `money`, `qty`, `shows`) rather than raw escapes — and note a context dict must never expose a key named `items`, since Jinja resolves `block.items` to `dict.items` first (hence `loose_items`). `restaurant/print_formats.py` seeds two editable, non-standard formats reproducing the built-in layouts; they're seeded but never wired, so nothing changes until a printer points at one.
- **Ticket content** is toggled per section from Restaurant Settings (`comanda_show_*`, `receipt_show_*`), read through `restaurant/ticket_options.py::shows`, which treats an absent value as "show". Adding a Check field to a Single needs a patch that writes the 1 **unconditionally**: syncing the DocType materializes new fields into `tabSingles` as 0 before patches run, so an "only if unset" guard never fires and every ticket comes out stripped. Patches run once per site (Patch Log), so an unconditional write can't clobber an admin's later choice.
- **Reports** (`pos_prime/pos_prime/report/`) all read `Restaurant Order` (submitted), never `Sales Invoice` — POS Closing Entry consolidation doesn't propagate the `pos_prime_*` item fields a combo's components need.
- **Demo data**: `setup.py::setup_demo_menu(company, pos_profile)` seeds a small idempotent demo menu — including registering its three demo groups (Sopas, Segundos, Refrescos) under Restaurant Settings' Daily Menu section, as the reference config for the feature above; not wired into `hooks.fixtures` since it's one site's menu, not app data. Run via `bench --site <site> execute pos_prime.restaurant.setup.setup_demo_menu --kwargs "{'company': '...', 'pos_profile': '...'}"`. Resolves the root Item Group and default UOM by structure/setting rather than hardcoding English names ("All Item Groups"/"Nos") — both are themselves translations on a non-English site.
- **Frontend**: `stores/restaurant.ts` (session config via `get_restaurant_config`), `components/restaurant/` (`ComboCard` — rendered by `ItemGrid` as the first cells of the item grid, so combos and items share one grid and one virtualizer, `ComboBuilderDialog`, `ComboCartGroup`, `NoteDialog`, `ModifierPicker`). `utils/cartPayload.ts` is the one place a `CartItem` is built from a catalog `Item` or a server `InvoiceItem` and serialized back — every restaurant field has to be threaded through there for hold/resume and checkout to agree on its shape.
- **E2E**: `frontend/e2e/tests/13-restaurant.spec.ts` + `frontend/e2e/fixtures/restaurant-fixtures.ts`, which discovers a usable combo/modifier from whatever the site already has and `test.skip()`s if restaurant mode is off or nothing usable exists (same philosophy as `pos-fixtures.ts` for regular items).
