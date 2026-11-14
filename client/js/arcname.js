/**
 * ZIP 内ファイル名の重複回避（本線 filenames.uniquify_arcname 相当）。
 * _n を付けた後も limits.maxFilenameChars 以内に収める。
 */

import { buildFilename, fitFilename } from "./filenames.js";

/**
 * @param {string} name
 * @param {Set<string>} used
 */
export function uniquifyArcname(name, used) {
  const base = fitFilename(name || "file.bin");
  if (!used.has(base)) {
    used.add(base);
    return base;
  }
  const i = base.lastIndexOf(".");
  const stem = i > 0 ? base.slice(0, i) : base;
  const ext = i > 0 ? base.slice(i) : "";
  let n = 2;
  while (true) {
    const candidate = buildFilename(stem, `_${n}`, ext);
    if (!used.has(candidate)) {
      used.add(candidate);
      return candidate;
    }
    n += 1;
  }
}
