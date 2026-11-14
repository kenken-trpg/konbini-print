/**
 * ファイル名の長さ制限（本線 src/filenames.build_filename / fit_filename 相当）。
 *
 * ネットワークプリントは 100 文字超のファイル名でアップロードに失敗するため、
 * 出力名は拡張子・連番込みで limits.maxFilenameChars 以内に収める。
 * 削るのは本体（stem）だけで、サフィックスと拡張子は残す。
 * 文字数は Unicode コードポイント単位で数える（サロゲートペアを途中で切らない）。
 */

import { limits } from "./limits.js";

/** @param {string} s */
export function charLength(s) {
  return Array.from(s).length;
}

/**
 * @param {string} s
 * @param {number} n
 */
export function truncateChars(s, n) {
  return Array.from(s).slice(0, Math.max(0, n)).join("");
}

/**
 * stem + suffix + ext を maxChars 文字以内で組み立てる。
 * @param {string} stem
 * @param {string} [suffix]
 * @param {string} [ext]
 * @param {number} [maxChars]
 * @param {string} [fallback]
 */
export function buildFilename(
  stem,
  suffix = "",
  ext = "",
  maxChars = limits.maxFilenameChars,
  fallback = "file"
) {
  const budget = maxChars - charLength(suffix) - charLength(ext);
  if (budget < 1) {
    throw new Error(`suffix と拡張子だけで ${maxChars} 文字を超えます: ${suffix}${ext}`);
  }
  const trimmed =
    truncateChars(stem, budget).replace(/[ ._]+$/, "") || truncateChars(fallback, budget);
  return `${trimmed}${suffix}${ext}`;
}

/**
 * 拡張子付きのファイル名を、拡張子を残したまま maxChars 以内に収める。
 * @param {string} name
 * @param {number} [maxChars]
 */
export function fitFilename(name, maxChars = limits.maxFilenameChars) {
  const i = name.lastIndexOf(".");
  const ext = i > 0 ? name.slice(i) : "";
  const stem = i > 0 ? name.slice(0, i) : name;
  return buildFilename(stem, "", ext, maxChars);
}
