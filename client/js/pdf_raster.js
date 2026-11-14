/**
 * PDF 3a: pdf.js（vendor）で各ページをラスタライズ → 画像 Blob。
 * 再保存・まとめ PDF はスコープ外。
 * ライブラリは初回 PDF 時だけ読み込む（本体+worker で約 1.7MB）。
 */

import { limits } from "./limits.js";
import { notifyVendorLoad } from "./vendor_status.js";

const PDF_MAIN = new URL("../vendor/pdfjs/pdf.min.mjs", import.meta.url).href;
const PDF_WORKER = new URL("../vendor/pdfjs/pdf.worker.min.mjs", import.meta.url).href;

let pdfjsPromise = null;

async function loadPdfjs() {
  if (!pdfjsPromise) {
    notifyVendorLoad("pdfjs", "PDF用の部品", "start");
    pdfjsPromise = (async () => {
      try {
        const pdfjs = await import(PDF_MAIN);
        pdfjs.GlobalWorkerOptions.workerSrc = PDF_WORKER;
        notifyVendorLoad("pdfjs", "PDF用の部品", "done");
        return pdfjs;
      } catch (err) {
        pdfjsPromise = null;
        notifyVendorLoad("pdfjs", "PDF用の部品", "error", err?.message);
        throw new Error(
          `PDF用の部品を読み込めませんでした。ページを再読み込みして試してください。（${err?.message || err}）`
        );
      }
    })();
  }
  return pdfjsPromise;
}

/**
 * @param {string} filename
 */
export function isPdfName(filename) {
  return filename.toLowerCase().endsWith(".pdf");
}

function friendlyPdfError(err) {
  const msg = String(err?.message || err || "");
  if (/password|encrypt|暗号化/i.test(msg)) {
    return "パスワード付きの PDF は開けません。解除してからもう一度どうぞ。";
  }
  if (/memory|allocation|out of memory|Maximum call stack| QuotaExceeded/i.test(msg)) {
    return "端末のメモリが足りないようです。ページ数の少ない PDF にするか、枚数を減らして試してください。";
  }
  return `PDF を開けませんでした（${msg}）。壊れているか、非対応の形式かもしれません。`;
}

/**
 * @param {Blob|File} blob
 * @param {string} filename
 * @param {object} opts
 * @returns {Promise<Array<{blob: Blob, filename: string, page: number, pageCount: number, warning: string|null}>>}
 */
export async function rasterizePdfPages(
  blob,
  filename,
  { maxPages = limits.maxPdfPages, targetLongPx = 2000, onPage = null } = {}
) {
  let pdfjs;
  try {
    pdfjs = await loadPdfjs();
  } catch (err) {
    throw new Error(friendlyPdfError(err));
  }

  const data = new Uint8Array(await blob.arrayBuffer());
  let doc;
  try {
    doc = await pdfjs.getDocument({
      data,
      useSystemFonts: true,
      // 多層防御: フォント描画で eval / new Function を使わせない
      isEvalSupported: false,
    }).promise;
  } catch (err) {
    throw new Error(friendlyPdfError(err));
  }

  const pageCount = doc.numPages;
  const limit = Math.min(pageCount, maxPages);
  const stem = filename.replace(/\.pdf$/i, "") || "pdf";
  const pages = [];
  const warnParts = [];
  if (pageCount > maxPages) {
    warnParts.push(
      `PDF は ${pageCount} ページありますが、先頭 ${maxPages} ページだけ写真にします（これ以上は重いため）。`
    );
  }
  if (pageCount >= 8) {
    warnParts.push("ページが多いと、途中で重くなったり止まったりすることがあります。");
  }
  // ページが多いほど解像度を抑えてメモリを節約
  let longPx = targetLongPx;
  if (limit >= 12) longPx = Math.min(longPx, 1400);
  else if (limit >= 6) longPx = Math.min(longPx, 1700);

  try {
    for (let i = 1; i <= limit; i += 1) {
      if (typeof onPage === "function") {
        try {
          onPage(i, pageCount);
        } catch {
          /* ignore */
        }
      }
      let page = null;
      let canvas = null;
      try {
        page = await doc.getPage(i);
        const base = page.getViewport({ scale: 1 });
        const longSide = Math.max(base.width, base.height);
        const scale = longSide > 0 ? Math.min(2.5, longPx / longSide) : 1.5;
        const viewport = page.getViewport({ scale });

        canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.floor(viewport.width));
        canvas.height = Math.max(1, Math.floor(viewport.height));
        const ctx = canvas.getContext("2d", { willReadFrequently: false });
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const task = page.render({ canvasContext: ctx, viewport });
        await task.promise;

        const jpegBlob = await new Promise((resolve, reject) => {
          canvas.toBlob(
            (b) => (b ? resolve(b) : reject(new Error("ページを写真にできませんでした"))),
            "image/jpeg",
            0.9
          );
        });

        const pageName =
          pageCount === 1 ? `${stem}.jpg` : `${stem}_p${String(i).padStart(3, "0")}.jpg`;

        pages.push({
          blob: jpegBlob,
          filename: pageName,
          page: i,
          pageCount,
          warning: i === 1 && warnParts.length ? warnParts.join(" ") : null,
        });
      } catch (err) {
        throw new Error(
          friendlyPdfError(err) +
            `（${i} ページ目付近）。ページを分けた PDF で試してください。`
        );
      } finally {
        try {
          page?.cleanup?.();
        } catch {
          /* ignore */
        }
        if (canvas) {
          canvas.width = 0;
          canvas.height = 0;
        }
      }
    }
  } finally {
    try {
      await doc.cleanup?.();
    } catch {
      /* ignore */
    }
    try {
      await doc.destroy?.();
    } catch {
      /* ignore */
    }
  }

  return pages;
}
