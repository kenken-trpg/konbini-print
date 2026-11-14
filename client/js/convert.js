/**
 * 本線 src/image_convert.py のブラウザ移植（JPEG/PNG/WebP/GIF 先頭コマ 等）。
 * 上限値は limits.js（domain.json 適用後）を参照する。
 *
 * 注: アニメ GIF はブラウザデコード都合で先頭フレームのみ扱う。
 */

import { limits } from "./limits.js";

/**
 * EXIF 向きを反映した ImageBitmap / HTMLImageElement を返す。
 * @param {Blob|File} blob
 * @returns {Promise<ImageBitmap|HTMLImageElement>}
 */
export async function loadImageElement(blob) {
  if (typeof createImageBitmap === "function") {
    try {
      const bmp = await createImageBitmap(blob, { imageOrientation: "from-image" });
      const pixels = bmp.width * bmp.height;
      if (pixels > limits.maxImagePixels) {
        bmp.close?.();
        throw new Error(
          `画像ピクセル数が上限を超えています（最大 ${limits.maxImagePixels.toLocaleString()}、現在 ${pixels.toLocaleString()}）。`
        );
      }
      return bmp;
    } catch (err) {
      if (String(err?.message || "").includes("ピクセル数")) throw err;
    }
  }

  const url = URL.createObjectURL(blob);
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () =>
        reject(new Error("画像を読み込めませんでした（JPEG/PNG/WebP/GIF 等）"));
      el.src = url;
    });
    const pixels = img.naturalWidth * img.naturalHeight;
    if (pixels > limits.maxImagePixels) {
      throw new Error(
        `画像ピクセル数が上限を超えています（最大 ${limits.maxImagePixels.toLocaleString()}、現在 ${pixels.toLocaleString()}）。`
      );
    }
    return img;
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * @param {ImageBitmap|HTMLImageElement} img
 * @param {[number, number, number]} bg
 * @returns {HTMLCanvasElement}
 */
function toRgbCanvas(img, bg = limits.defaultBg) {
  const w = "naturalWidth" in img ? img.naturalWidth : img.width;
  const h = "naturalHeight" in img ? img.naturalHeight : img.height;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0);
  if (typeof img.close === "function") img.close();
  return canvas;
}

/**
 * @param {HTMLCanvasElement} src
 * @param {number} maxSide
 */
function clampMaxSide(src, maxSide = limits.maxSide) {
  const w = src.width;
  const h = src.height;
  const longSide = Math.max(w, h);
  if (longSide <= maxSide) return src;
  const scale = maxSide / longSide;
  return resizeCanvas(src, Math.max(1, Math.round(w * scale)), Math.max(1, Math.round(h * scale)));
}

/**
 * @param {HTMLCanvasElement} src
 * @param {number} tw
 * @param {number} th
 */
function resizeCanvas(src, tw, th) {
  const out = document.createElement("canvas");
  out.width = tw;
  out.height = th;
  const ctx = out.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(src, 0, 0, tw, th);
  return out;
}

/**
 * @param {HTMLCanvasElement} src
 * @param {[number, number]} canvasSize 縦向き基準 (短辺, 長辺)
 * @param {"fit"|"crop"} mode
 * @param {[number, number, number]} bg
 */
export function fitToCanvas(src, canvasSize, mode = "fit", bg = limits.defaultBg) {
  const [short, long] = canvasSize;
  const srcW = src.width;
  const srcH = src.height;
  const landscape = srcW >= srcH;
  const targetW = landscape ? long : short;
  const targetH = landscape ? short : long;

  if (mode === "crop") {
    const scale = Math.max(targetW / srcW, targetH / srcH);
    const sw = Math.round(srcW * scale);
    const sh = Math.round(srcH * scale);
    const ox = Math.floor((sw - targetW) / 2);
    const oy = Math.floor((sh - targetH) / 2);
    const scaled = resizeCanvas(src, sw, sh);
    const out = document.createElement("canvas");
    out.width = targetW;
    out.height = targetH;
    const ctx = out.getContext("2d");
    ctx.drawImage(scaled, -ox, -oy);
    return out;
  }

  const scale = Math.min(targetW / srcW, targetH / srcH);
  const fw = Math.max(1, Math.round(srcW * scale));
  const fh = Math.max(1, Math.round(srcH * scale));
  const fitted = resizeCanvas(src, fw, fh);
  const out = document.createElement("canvas");
  out.width = targetW;
  out.height = targetH;
  const ctx = out.getContext("2d");
  ctx.fillStyle = `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`;
  ctx.fillRect(0, 0, targetW, targetH);
  const ox = Math.floor((targetW - fw) / 2);
  const oy = Math.floor((targetH - fh) / 2);
  ctx.drawImage(fitted, ox, oy);
  return out;
}

/**
 * @param {HTMLCanvasElement} img
 * @param {number} insetRatio
 * @param {[number, number, number]} bg
 */
export function applySafeInset(img, insetRatio = 0.03, bg = limits.defaultBg) {
  if (insetRatio <= 0) return img;
  const w = img.width;
  const h = img.height;
  const ix = Math.max(1, Math.floor(w * insetRatio));
  const iy = Math.max(1, Math.floor(h * insetRatio));
  const innerW = Math.max(1, w - 2 * ix);
  const innerH = Math.max(1, h - 2 * iy);
  const scale = Math.min(innerW / w, innerH / h);
  const fw = Math.max(1, Math.round(w * scale));
  const fh = Math.max(1, Math.round(h * scale));
  const fitted = resizeCanvas(img, fw, fh);
  const out = document.createElement("canvas");
  out.width = w;
  out.height = h;
  const ctx = out.getContext("2d");
  ctx.fillStyle = `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`;
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(fitted, Math.floor((w - fw) / 2), Math.floor((h - fh) / 2));
  return out;
}

/**
 * @param {HTMLCanvasElement} canvas
 * @param {number} quality 0–1
 * @returns {Promise<Blob>}
 */
function canvasToJpegBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("JPEG エンコードに失敗しました"))),
      "image/jpeg",
      quality
    );
  });
}

/**
 * @param {HTMLCanvasElement} canvas
 * @returns {Promise<Blob>}
 */
function canvasToPngBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("PNG エンコードに失敗しました"))),
      "image/png"
    );
  });
}

/**
 * @param {HTMLCanvasElement} img
 * @param {object} opts
 */
export async function encodeUnderLimit(
  img,
  {
    fmt = "JPEG",
    maxBytes = limits.maxFileBytes,
    startQuality = limits.defaultJpegQuality,
    minQuality = limits.minJpegQuality,
    minLongSide = 640,
  } = {}
) {
  const warnings = [];
  let format = String(fmt).toUpperCase();
  if (format === "JPG") format = "JPEG";
  let current = img;

  if (format === "PNG") {
    const png = await canvasToPngBlob(current);
    if (png.size <= maxBytes) {
      return { blob: png, format: "PNG", quality: null, warnings, canvas: current };
    }
    warnings.push(
      `PNG が ${(png.size / 1024 / 1024).toFixed(1)}MB で上限超過のため JPEG に切替えます。`
    );
    format = "JPEG";
  }

  let scaleRound = 0;
  let data = null;
  let quality = startQuality;

  while (true) {
    quality = startQuality;
    while (quality >= minQuality) {
      data = await canvasToJpegBlob(current, quality / 100);
      if (data.size <= maxBytes) {
        if (quality < startQuality || scaleRound > 0) {
          const parts = [];
          if (quality < startQuality) parts.push(`JPEG 品質 ${quality}`);
          if (scaleRound > 0) parts.push(`解像度 ${current.width}×${current.height}`);
          warnings.push("容量制限のため " + parts.join(" / ") + " に調整しました。");
        }
        return { blob: data, format: "JPEG", quality, warnings, canvas: current };
      }
      quality -= 5;
    }

    const longSide = Math.max(current.width, current.height);
    if (longSide <= minLongSide) {
      warnings.push(
        `下限品質・最小解像度付近でも ${(data.size / 1024 / 1024).toFixed(1)}MB です。別プリセットを検討してください。`
      );
      return { blob: data, format: "JPEG", quality: minQuality, warnings, canvas: current };
    }

    current = resizeCanvas(
      current,
      Math.max(1, Math.round(current.width * 0.85)),
      Math.max(1, Math.round(current.height * 0.85))
    );
    scaleRound += 1;
  }
}

/**
 * @param {Blob|File} data
 * @param {string} filename
 * @param {object} options
 */
export async function convertImage(
  data,
  filename,
  {
    canvas = null,
    mode = "fit",
    bg = limits.defaultBg,
    outputFormat = "JPEG",
    maxBytes = limits.maxFileBytes,
    safeInset = false,
    safeInsetRatio = 0.03,
    maxSide = limits.maxSide,
  } = {}
) {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".heic") || lower.endsWith(".heif")) {
    throw new Error("HEIC は先に decodeHeicIfNeeded でデコードしてください。");
  }
  if (lower.endsWith(".pdf")) {
    throw new Error("PDF は先に rasterizePdfPages でラスタ化してください。");
  }

  const imgEl = await loadImageElement(data);
  const warnings = [];
  let out = toRgbCanvas(imgEl, bg);

  if (canvas == null) {
    const before = [out.width, out.height];
    out = clampMaxSide(out, maxSide);
    if (out.width !== before[0] || out.height !== before[1]) {
      warnings.push(`長辺が ${maxSide}px を超えていたため縮小しました。`);
    }
  } else {
    out = fitToCanvas(out, canvas, mode, bg);
  }

  if (safeInset) {
    out = applySafeInset(out, safeInsetRatio, bg);
    warnings.push(
      `セーフエリア（内側約 ${(safeInsetRatio * 100).toFixed(0)}%）を確保しました。セブンの端カット対策です。`
    );
  }

  const encoded = await encodeUnderLimit(out, {
    fmt: outputFormat,
    maxBytes,
  });
  warnings.push(...encoded.warnings);

  return {
    blob: encoded.blob,
    format: encoded.format,
    width: encoded.canvas.width,
    height: encoded.canvas.height,
    quality: encoded.quality,
    warnings,
  };
}
