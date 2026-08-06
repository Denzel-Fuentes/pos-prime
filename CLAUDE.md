# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

POS Prime is a custom Frappe app (`pos_prime`) that replaces ERPNext's built-in Point of Sale with a Vue 3 SPA. It has two halves that live in one repo:

- **Backend** (`pos_prime/`) — a Frappe Python app: whitelisted API endpoints under `pos_prime/api/*.py`, hooks in `pos_prime/hooks.py`, a Desk page (`pos_prime/pos_prime/page/pos_terminal`), and a website route (`pos_prime/www/pos_prime.*`) that serves the SPA.
- **Frontend** (`frontend/`) — Vue 3 + TypeScript + Pinia + Tailwind, built with Vite, using `frappe-ui` for the Frappe API client.

**Critical rule (also stated in CONTRIBUTING.md): POS Prime makes zero modifications to ERPNext's schema.** There are no custom doctypes and no custom fields anywhere in this app — `pos_prime/pos_prime/` only contains a workspace, a Desk page, and number cards. All data is read/written through ERPNext's standard doctypes (POS Invoice, POS Opening/Closing Entry, POS Profile, Item, Item Price, Customer, Bin, etc.). Keep it that way — do not add a `doctype/` folder or custom field patches without this being an explicit, deliberate exception.

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
- `stores/` — one Pinia store per domain: `cart`, `items`, `customer`, `customerDisplay`, `drafts`, `orders`, `payment`, `posSession`, `session`, `settings`. `posSession` gates shift-scoped routes (see `router.ts`'s `requiresShift` meta + `beforeEach` guard, which redirects to `OpenShift` if there's no open POS Opening Entry).
- `composables/` — hardware/UX integrations: `useBarcodeScanner`, `useSerialDisplay` + `useBroadcastDisplay` (customer pole display, both VFD-serial and second-screen variants), `usePaymentTerminal`, `useKioskMode`, `useKeyboardShortcuts` (F1–F10), `useFocusTrap`, `useRTL`, `useTouchDevice`.
- `views/` — one per route: `POS`, `OpenShift`, `CloseShift`, `Orders`, `CustomerPoleDisplay` (`/display`), `CustomerDisplay` (`/customers`, `/customers/:id`), `SelfCheckout` (`/kiosk`).
- Path alias `@` → `frontend/src` (see `vite.config.ts` / `tsconfig.json`).
