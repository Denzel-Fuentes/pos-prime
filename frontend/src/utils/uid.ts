// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

/**
 * Generate a client-side unique id for a cart line (CartItem.uid).
 *
 * `crypto.randomUUID()` requires a secure context. Chrome treats
 * `*.localhost` as trustworthy; Safari does not — so the fallback below
 * is not decorative, it's load-bearing for Safari-based kiosks/tablets.
 */
export function newUid(): string {
  const c = globalThis.crypto as Crypto | undefined
  if (c?.randomUUID) return c.randomUUID()
  return 'u' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
}
