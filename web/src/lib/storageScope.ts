// storageScope.ts — which identity the browser-local stores belong to right now.
//
// PRIVACY RULE (SECURITY.md §4.4): data a signed-in user creates on this device is
// stored under a key that includes THEIR user id, so after logout (or when someone
// else signs in on the same browser) the app never reads it as guest or as another
// account. useAuth sets the scope as soon as the session is known.
//
// Older builds wrote everything under one shared, unscoped key. That "legacy" data
// can't be attributed to anyone, so it is handed ONCE to the first account that
// signs in on this device (on a personal device that is the owner), never to a guest.

let scope: string | null = null;

/** Set the current identity (user id, or null for a guest). Called by useAuth. */
export function setStorageScope(userId: string | null): void {
  scope = userId;
}

/** The current identity: user id, or null for a guest. */
export function storageScope(): string | null {
  return scope;
}

/** `base` for a guest, `base.u.<userId>` for a signed-in user. */
export function scopedKey(base: string, userId: string | null = scope): string {
  return userId ? `${base}.u.${userId}` : base;
}

/**
 * localStorage only: move the unscoped legacy value `legacyKey` into the user's own
 * key the first time any account signs in, if that account has nothing there yet.
 * Afterwards a flag stops it from ever claiming again (later guest data stays guest).
 */
export function claimLegacyLocal(legacyKey: string, userId: string): void {
  try {
    const flag = `${legacyKey}.claimed`;
    if (localStorage.getItem(flag)) return;
    const legacy = localStorage.getItem(legacyKey);
    const mine = scopedKey(legacyKey, userId);
    if (legacy !== null && localStorage.getItem(mine) === null) localStorage.setItem(mine, legacy);
    if (legacy !== null) localStorage.removeItem(legacyKey);
    localStorage.setItem(flag, '1');
  } catch {
    /* storage blocked */
  }
}
