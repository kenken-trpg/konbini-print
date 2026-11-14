/**
 * 本線 src/ziputil.py 相当（vendor/jszip）。
 * ライブラリは「まとめて保存」時だけ読み込む（約 0.1MB）。
 */

import { uniquifyArcname } from "./arcname.js";
import { loadScript } from "./load_script.js";
import { notifyVendorLoad } from "./vendor_status.js";

export { uniquifyArcname };

const JSZIP_SRC = new URL("../vendor/jszip.min.js", import.meta.url).href;

async function loadJSZip() {
  if (typeof window.JSZip === "function") return window.JSZip;
  notifyVendorLoad("jszip", "まとめ保存用の部品", "start");
  try {
    await loadScript(JSZIP_SRC);
    if (typeof window.JSZip !== "function") {
      throw new Error("まとめ保存用の部品の準備に失敗しました。");
    }
    notifyVendorLoad("jszip", "まとめ保存用の部品", "done");
    return window.JSZip;
  } catch (err) {
    notifyVendorLoad("jszip", "まとめ保存用の部品", "error", err?.message);
    throw err;
  }
}

/**
 * @param {Array<{name: string, blob: Blob}>} files
 * @returns {Promise<Blob>}
 */
export async function zipArtifacts(files) {
  const JSZip = await loadJSZip();
  const zip = new JSZip();
  const used = new Set();
  for (const f of files) {
    const arcname = uniquifyArcname(f.name, used);
    zip.file(arcname, f.blob);
  }
  return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
}
