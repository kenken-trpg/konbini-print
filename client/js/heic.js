/**
 * HEIC → PNG Blob（vendor/heic2any）。
 * JPEG はフィット後の encode で1回だけ行い、品質の二度漬けを避ける。
 * マルチ画像 HEIC は全枚展開する。
 * ライブラリは初回 HEIC 時だけ読み込む（約 1.3MB）。
 */

import { loadScript } from "./load_script.js";
import { notifyVendorLoad } from "./vendor_status.js";

const HEIC_SRC = new URL("../vendor/heic2any.min.js", import.meta.url).href;

let heicReady = null;

async function loadHeic2any() {
  if (typeof window.heic2any === "function") return window.heic2any;
  if (!heicReady) {
    notifyVendorLoad("heic2any", "iPhone写真用の部品", "start");
    heicReady = loadScript(HEIC_SRC)
      .then(() => {
        if (typeof window.heic2any !== "function") {
          throw new Error("iPhone写真用の部品の準備に失敗しました。");
        }
        notifyVendorLoad("heic2any", "iPhone写真用の部品", "done");
        return window.heic2any;
      })
      .catch((err) => {
        heicReady = null;
        notifyVendorLoad("heic2any", "iPhone写真用の部品", "error", err?.message);
        throw err;
      });
  }
  return heicReady;
}

/**
 * @param {string} filename
 */
export function isHeicName(filename) {
  const lower = filename.toLowerCase();
  return lower.endsWith(".heic") || lower.endsWith(".heif");
}

/**
 * HEIC なら PNG Blob 群に展開。それ以外は入力をそのまま1件で返す。
 * @param {Blob|File} blob
 * @param {string} filename
 * @returns {Promise<Array<{blob: Blob, filename: string, warnings: string[]}>>}
 */
export async function decodeHeicIfNeeded(blob, filename) {
  if (!isHeicName(filename)) {
    return [{ blob, filename, warnings: [] }];
  }

  try {
    const heic2any = await loadHeic2any();
    let converted = await heic2any({
      blob,
      toType: "image/png",
    });
    const list = Array.isArray(converted) ? converted : [converted];
    if (!list.length || !(list[0] instanceof Blob)) {
      throw new Error("変換結果がおかしいです");
    }

    const stem = filename.replace(/\.(heic|heif)$/i, "") || "heic";
    const shared = ["iPhone の写真形式を読み込みました。"];
    if (list.length > 1) {
      shared.push(`1つのファイルに写真が ${list.length} 枚入っていたので、全部使います。`);
    }

    return list.map((item, i) => {
      if (!(item instanceof Blob)) {
        throw new Error(`${i + 1} 枚目の変換に失敗しました`);
      }
      const outName =
        list.length === 1
          ? `${stem}.png`
          : `${stem}_p${String(i + 1).padStart(3, "0")}.png`;
      return {
        blob: item,
        filename: outName,
        warnings: i === 0 ? [...shared] : [],
      };
    });
  } catch (err) {
    const msg = err?.message || String(err);
    throw new Error(
      `この iPhone 写真を読めませんでした（${msg}）。「JPEG で保存」し直すか、別の写真で試してください。`
    );
  }
}
