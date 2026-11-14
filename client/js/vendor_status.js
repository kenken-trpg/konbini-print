/**
 * 大きな vendor（HEIC / PDF / ZIP）を初めて読むときの UI 通知フック。
 * 初期表示では読まない（遅延読込）。
 */

/** @type {null | ((info: { id: string, label: string, phase: "start"|"done"|"error", detail?: string }) => void)} */
let hook = null;

/**
 * @param {typeof hook} fn
 */
export function setVendorLoadHook(fn) {
  hook = fn;
}

/**
 * @param {string} id
 * @param {string} label
 * @param {"start"|"done"|"error"} phase
 * @param {string} [detail]
 */
export function notifyVendorLoad(id, label, phase, detail) {
  if (typeof hook === "function") {
    try {
      hook({ id, label, phase, detail });
    } catch {
      /* ignore */
    }
  }
}
