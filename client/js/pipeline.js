/**
 * 変換オーケストレーション（DOM 非依存）。
 * UI は app.js が担当する。
 */

import { convertImage } from "./convert.js";
import { buildFilename, truncateChars } from "./filenames.js";
import { decodeHeicIfNeeded, isHeicName } from "./heic.js";
import { limits } from "./limits.js";
import { isPdfName, rasterizePdfPages } from "./pdf_raster.js";
import { validateByProfile } from "./validate.js";

const IMAGE_EXTS = new Set([
  ".jpg",
  ".jpeg",
  ".jpe",
  ".png",
  ".webp",
  ".bmp",
  ".gif",
  ".heic",
  ".heif",
]);

export function isImageName(name) {
  const lower = name.toLowerCase();
  const i = lower.lastIndexOf(".");
  if (i < 0) return false;
  return IMAGE_EXTS.has(lower.slice(i));
}

/** サフィックスを付ける前の stem の上限（本線 MAX_STEM_CHARS 相当） */
const MAX_STEM_CHARS = 80;

export function sanitizeFilename(name, ext, index) {
  const base = name.replace(/\.[^.]+$/, "") || `file_${index}`;
  let cleaned = base
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\p{Extended_Pictographic}/gu, "")
    .replace(/_+/g, "_")
    .replace(/^[ ._]+|[ ._]+$/g, "");
  cleaned = truncateChars(cleaned, MAX_STEM_CHARS).replace(/[ ._]+$/, "");
  if (!cleaned) cleaned = `file_${index}`;
  return buildFilename(cleaned, `_${String(index).padStart(3, "0")}`, ext);
}

export function parseBg(text) {
  const m = String(text || "")
    .trim()
    .match(/^#?([0-9a-f]{6})$/i);
  if (!m) return [255, 255, 255];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function validateInputBatch(files) {
  const errors = [];
  if (files.length > limits.maxInputFiles) {
    errors.push(
      `一度に入れられるのは ${limits.maxInputFiles} 個までです（いま ${files.length} 個）。減らしてください。`
    );
  }
  const total = files.reduce((sum, f) => sum + (f.size || 0), 0);
  if (total > limits.maxInputTotalBytes) {
    const maxMb = (limits.maxInputTotalBytes / 1024 / 1024).toFixed(0);
    const nowMb = (total / 1024 / 1024).toFixed(1);
    errors.push(
      `全部合わせた重さが大きすぎます（目安 ${maxMb} MB まで、いま ${nowMb} MB）。数を減らすか、小さい写真にしてください。`
    );
  }
  return errors;
}

/**
 * @param {string} [userAgent]
 */
export function isLikelyMobile(userAgent) {
  const ua =
    userAgent ??
    (typeof navigator !== "undefined" ? navigator.userAgent || "" : "");
  return /Mobi|Android|iPhone|iPad/i.test(ua);
}

export function pdfWorkLimits() {
  const mobile = isLikelyMobile();
  return {
    maxPages: mobile ? Math.min(limits.maxPdfPages, 10) : limits.maxPdfPages,
    targetLongPx: mobile ? 1500 : 2000,
  };
}

/**
 * @param {File[]} files
 * @returns {string[]}
 */
export function softLoadTips(files) {
  const tips = [];
  const pdfs = files.filter((f) => isPdfName(f.name));
  const heavyPdf = pdfs.find((f) => f.size >= 8 * 1024 * 1024);
  if (heavyPdf) {
    tips.push(
      `「${heavyPdf.name}」は重めの PDF です。途中で止まったら、ページを分けた PDF で試してください。`
    );
  }
  if (files.length >= 12) {
    tips.push("枚数が多いと時間がかかり、まれに止まることがあります。分けて整えると安心です。");
  }
  if (isLikelyMobile() && pdfs.length) {
    tips.push("スマホでは PDF は先頭の最大10ページまで写真にします。");
  }
  return tips;
}

/**
 * @param {File} file
 * @param {(msg: string) => void} [onProgress]
 */
export async function expandInput(file, onProgress) {
  if (isPdfName(file.name)) {
    const { maxPages, targetLongPx } = pdfWorkLimits();
    onProgress?.(`PDF「${file.name}」を開いています…`);
    const pages = await rasterizePdfPages(file, file.name, {
      maxPages,
      targetLongPx,
      onPage: (page, pageCount) => {
        onProgress?.(
          `PDF「${file.name}」：${page} ページ目を写真にしています（全部で ${pageCount} ページ）`
        );
      },
    });
    return pages.map((p) => ({
      blob: p.blob,
      filename: p.filename,
      sourceName: file.name,
      extraWarnings: [
        p.warning,
        p.page === 1
          ? `PDF のページを写真にしました（${p.pageCount} ページ中、最大 ${Math.min(p.pageCount, maxPages)} ページまで）。元の PDF のままではありません。`
          : null,
      ].filter(Boolean),
    }));
  }

  if (isHeicName(file.name) || isImageName(file.name)) {
    const decodedList = await decodeHeicIfNeeded(file, file.name);
    const gifNote = file.name.toLowerCase().endsWith(".gif")
      ? ["動く GIF は、最初の1枚だけ使います。"]
      : [];
    return decodedList.map((decoded, i) => ({
      blob: decoded.blob,
      filename: decoded.filename,
      sourceName: file.name,
      extraWarnings: [...(i === 0 ? gifNote : []), ...(decoded.warnings || [])],
    }));
  }

  return [];
}

/**
 * @typedef {object} BatchConvertOptions
 * @property {object} domain
 * @property {object} preset
 * @property {File[]} files
 * @property {"fit"|"crop"} fitMode
 * @property {boolean} safeInset
 * @property {[number, number, number]} bg
 * @property {(p: {done:number, total:number, text:string}) => void} [onProgress]
 */

/**
 * @param {BatchConvertOptions} opts
 * @returns {Promise<{outputs: object[], skipped: string[]}>}
 */
export async function runBatchConvert({
  domain,
  preset,
  files,
  fitMode,
  safeInset,
  bg,
  onProgress,
}) {
  const outFmt = preset.output === "png" ? "PNG" : "JPEG";
  const maxOutputs = limits.maxSessionOutputs;
  const canvas = preset.canvas ? domain.canvases[preset.canvas] || null : null;
  const convertOpts = {
    canvas,
    mode: fitMode,
    bg,
    outputFormat: outFmt,
    maxBytes: limits.maxFileBytes,
    safeInset,
    maxSide: limits.maxSide,
  };

  const outputs = [];
  const skipped = [];
  let planned = files.length;
  let finishedFiles = 0;
  let idx = 0;

  for (const file of files) {
    onProgress?.({
      done: finishedFiles,
      total: Math.max(planned, 1),
      text: `ファイル ${finishedFiles + 1} / ${files.length}：「${file.name}」を準備中`,
    });

    let units;
    try {
      units = await expandInput(file, (msg) => {
        onProgress?.({
          done: finishedFiles,
          total: Math.max(planned, 1),
          text: msg,
        });
      });
    } catch (err) {
      skipped.push(`${file.name}: ${err?.message || err}`);
      finishedFiles += 1;
      continue;
    }
    if (!units.length) {
      skipped.push(`${file.name}（この種類は使えません）`);
      finishedFiles += 1;
      continue;
    }

    if (units.length > 1) planned += units.length - 1;

    let unitIndex = 0;
    for (const unit of units) {
      if (outputs.length >= maxOutputs) {
        skipped.push(`これ以上作れません（上限 ${maxOutputs} 枚）。残りは飛ばしました。`);
        break;
      }
      idx += 1;
      unitIndex += 1;
      const pageHint =
        units.length > 1 ? `（このファイルの ${unitIndex} / ${units.length} 枚目）` : "";
      onProgress?.({
        done: finishedFiles + (unitIndex - 1) / units.length,
        total: Math.max(planned, 1),
        text: `整えています ${idx} 枚目${pageHint}：${unit.filename}`,
      });

      try {
        const result = await convertImage(unit.blob, unit.filename, convertOpts);
        const ext = result.format === "JPEG" ? ".jpg" : ".png";
        const mime = result.format === "JPEG" ? "image/jpeg" : "image/png";
        const name = sanitizeFilename(unit.filename, ext, idx);
        const checks = validateByProfile(domain, preset.check_profile || "plain", {
          width: result.width,
          height: result.height,
          sizeBytes: result.blob.size,
        });
        const q = result.quality != null ? ` / 画質 ${result.quality}` : "";
        outputs.push({
          name,
          blob: result.blob,
          mime,
          meta: `${result.width}×${result.height} ピクセル / 約 ${(result.blob.size / 1024).toFixed(0)} KB${q}`,
          checks,
          warnings: [...unit.extraWarnings, ...result.warnings],
          sourceName: unit.sourceName,
        });
      } catch (err) {
        skipped.push(`${unit.filename}: ${err?.message || err}`);
      }
    }
    finishedFiles += 1;
    if (outputs.length >= maxOutputs && skipped.some((s) => s.includes("上限"))) {
      break;
    }
  }

  return { outputs, skipped };
}
