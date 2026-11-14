/**
 * 変換上限の単一ソース。app 起動時に domain.json で上書きする。
 * convert.js はここを参照し、ハードコード定数と二重管理しない。
 */

/** @type {{
 *   maxFileBytes: number,
 *   maxFilenameChars: number,
 *   minJpegQuality: number,
 *   defaultJpegQuality: number,
 *   defaultBg: [number, number, number],
 *   maxSide: number,
 *   maxImagePixels: number,
 *   maxInputFiles: number,
 *   maxInputTotalBytes: number,
 *   maxSessionOutputs: number,
 *   maxPdfPages: number,
 * }} */
const LIMIT_DEFAULTS = {
  maxFileBytes: 10 * 1024 * 1024,
  // ネットワークプリントは 100 文字超のファイル名でアップロード失敗（拡張子込み）
  maxFilenameChars: 100,
  minJpegQuality: 40,
  defaultJpegQuality: 90,
  defaultBg: /** @type {[number, number, number]} */ ([255, 255, 255]),
  maxSide: 6144,
  maxImagePixels: 25_000_000,
  maxInputFiles: 20,
  maxInputTotalBytes: 40 * 1024 * 1024,
  maxSessionOutputs: 30,
  maxPdfPages: 20,
};

export const limits = { ...LIMIT_DEFAULTS, defaultBg: [...LIMIT_DEFAULTS.defaultBg] };

/** テスト用: domain 適用前の既定値に戻す */
export function resetLimits() {
  Object.assign(limits, {
    ...LIMIT_DEFAULTS,
    defaultBg: [...LIMIT_DEFAULTS.defaultBg],
  });
}

/**
 * @param {object} domain domain.json
 */
export function applyDomain(domain) {
  const p = domain.print_limits;
  const r = domain.resource_limits || {};
  limits.maxFileBytes = p.max_file_bytes;
  limits.maxFilenameChars = p.max_filename_chars ?? limits.maxFilenameChars;
  limits.minJpegQuality = p.min_jpeg_quality;
  limits.defaultJpegQuality = p.default_jpeg_quality;
  limits.defaultBg = /** @type {[number, number, number]} */ ([...p.default_bg]);
  limits.maxSide = p.seven_photo.max_side;
  limits.maxImagePixels = r.max_image_pixels ?? limits.maxImagePixels;
  limits.maxInputFiles = r.max_input_files ?? limits.maxInputFiles;
  limits.maxInputTotalBytes = r.max_input_total_bytes ?? limits.maxInputTotalBytes;
  limits.maxSessionOutputs = r.max_session_outputs ?? limits.maxSessionOutputs;
  // スパイクではメモリ都合で 20 頁キャップ（domain の上限以下）
  const domainPdf = r.max_pdf_pages ?? 100;
  limits.maxPdfPages = Math.min(domainPdf, 20);
}
