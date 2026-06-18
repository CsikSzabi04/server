// idb.ts — tiny promise-based IndexedDB key/value store, dependency-free.
// AI-3 (BODY) persistence for the LARGE brain snapshot: localStorage caps at ~5 MB,
// which the 200k-vocab learner can exceed; IndexedDB has no such practical limit.
// One DB ('auri'), one object store ('kv'). Gracefully falls back to localStorage
// when IndexedDB is unavailable (private mode / old browsers).
//
// AI-1's useBrainLearning can move off localStorage with a 1-line swap:
//   const snap = await migrateFromLocalStorage<BrainPersistState>('auri.brainLearn');
//   ... // on observe:
//   void idbSet('auri.brainLearn', learner.toState());

const DB_NAME = 'auri';
const STORE = 'kv';
const VERSION = 1;

function hasIDB(): boolean {
  try {
    return typeof indexedDB !== 'undefined';
  } catch {
    return false;
  }
}

let dbPromise: Promise<IDBDatabase> | null = null;
function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function run<T>(mode: IDBTransactionMode, op: (store: IDBObjectStore) => IDBRequest): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const req = op(tx.objectStore(STORE));
        req.onsuccess = () => resolve(req.result as T);
        req.onerror = () => reject(req.error);
      }),
  );
}

/** Read a value by key (IndexedDB, then localStorage fallback). null if absent. */
export async function idbGet<T = unknown>(key: string): Promise<T | null> {
  if (hasIDB()) {
    try {
      const v = await run<T | undefined>('readonly', (s) => s.get(key));
      if (v !== undefined && v !== null) return v as T;
    } catch {
      /* fall through to localStorage */
    }
  }
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

/** Write a value by key (IndexedDB; localStorage fallback when IDB is missing). */
export async function idbSet(key: string, value: unknown): Promise<void> {
  if (hasIDB()) {
    try {
      await run('readwrite', (s) => s.put(value, key));
      return;
    } catch {
      /* fall through to localStorage */
    }
  }
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota / blocked */
  }
}

/** Delete a key from both stores. */
export async function idbDel(key: string): Promise<void> {
  if (hasIDB()) {
    try {
      await run('readwrite', (s) => s.delete(key));
    } catch {
      /* ignore */
    }
  }
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

/**
 * One-time migration: returns the IndexedDB value if present; otherwise copies an
 * existing localStorage value into IndexedDB and returns it. So the big snapshot
 * escapes the ~5 MB localStorage cap seamlessly, without losing existing progress.
 */
export async function migrateFromLocalStorage<T = unknown>(key: string): Promise<T | null> {
  if (hasIDB()) {
    try {
      const existing = await run<T | undefined>('readonly', (s) => s.get(key));
      if (existing !== undefined && existing !== null) return existing as T;
    } catch {
      /* ignore — try localStorage below */
    }
  }
  let value: T | null = null;
  try {
    const raw = localStorage.getItem(key);
    value = raw ? (JSON.parse(raw) as T) : null;
  } catch {
    value = null;
  }
  if (value !== null) await idbSet(key, value); // persist into IndexedDB once
  return value;
}
