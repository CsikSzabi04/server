// stage6Wipe.ts — remove the in-browser Stage-6 network (model weights + vocabulary)
// from this device on sign-out / account deletion (SECURITY.md §4.4). It is trained on
// the active identity's learner, so it must not stay behind for the next person.
// Deliberately WITHOUT importing TensorFlow.js (large): tfjs keeps 'indexeddb://<path>'
// models in the 'tensorflowjs' database (stores 'models_store' + 'model_info_store',
// keyed by <path>). The next identity simply retrains it.
const MODEL_PATH = 'auri-stage6'; // = MODEL_URL 'indexeddb://auri-stage6' in brain/stage6/net.ts
const VOCAB_KEY = 'auri.stage6.vocab';

export async function wipeStage6Local(): Promise<void> {
  try {
    localStorage.removeItem(VOCAB_KEY);
  } catch {
    /* storage blocked */
  }
  if (typeof indexedDB === 'undefined') return;
  await new Promise<void>((resolve) => {
    try {
      const req = indexedDB.open('tensorflowjs');
      // the database doesn't exist → don't create it, just stop
      req.onupgradeneeded = () => req.transaction?.abort();
      req.onerror = () => resolve();
      req.onsuccess = () => {
        const db = req.result;
        const stores = ['models_store', 'model_info_store'].filter((s) => db.objectStoreNames.contains(s));
        if (!stores.length) {
          db.close();
          resolve();
          return;
        }
        const tx = db.transaction(stores, 'readwrite');
        for (const s of stores) tx.objectStore(s).delete(MODEL_PATH);
        tx.oncomplete = tx.onerror = tx.onabort = () => {
          db.close();
          resolve();
        };
      };
    } catch {
      resolve();
    }
  });
}
