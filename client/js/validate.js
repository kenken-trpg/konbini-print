/**
 * 本線 src/validate.py のブラウザ移植（画像チェックのみ）。
 */

/**
 * @param {number} width
 * @param {number} height
 */
export function aspectRatio(width, height) {
  const longSide = Math.max(width, height);
  const shortSide = Math.min(width, height);
  if (shortSide === 0) return 0;
  return longSide / shortSide;
}

/**
 * @param {object} domain
 * @param {string} checkId
 * @param {{width:number,height:number,sizeBytes:number}} ctx
 */
function runCheck(domain, checkId, { width, height, sizeBytes }) {
  const limits = domain.print_limits;
  const ratio = aspectRatio(width, height);
  const longSide = Math.max(width, height);
  const shortSide = Math.min(width, height);
  const sevenMin = limits.seven_photo.min_px;
  const sevenMinLong = Math.max(...sevenMin);
  const sevenMinShort = Math.min(...sevenMin);

  switch (checkId) {
    case "max_file_bytes":
      return {
        label: "容量 ≤10MB",
        ok: sizeBytes <= limits.max_file_bytes,
        detail: `${(sizeBytes / 1024 / 1024).toFixed(2)} MB`,
      };
    case "nw_min_size":
      return {
        label: "最小サイズ目安（ネットワークプリント）",
        ok:
          longSide >= limits.network.min_long_px &&
          shortSide >= limits.network.min_short_px,
        detail: `${width}×${height}`,
      };
    case "photo_ratio":
      return {
        label: "フォト縦横比 1.3〜1.5",
        ok:
          ratio >= limits.seven_photo.ratio_min &&
          ratio <= limits.seven_photo.ratio_max,
        detail: ratio.toFixed(3),
      };
    case "square_ratio":
      return {
        label: "スクエア縦横比 ≈1.0",
        ok: ratio >= 0.95 && ratio <= 1.05,
        detail: ratio.toFixed(3),
      };
    case "max_side":
      return {
        label: "最大辺 ≤6144px",
        ok: longSide <= limits.seven_photo.max_side,
        detail: `${width}×${height}`,
      };
    case "seven_min_size":
      return {
        label: "最小サイズ目安（セブン）",
        ok: shortSide >= sevenMinShort && longSide >= sevenMinLong,
        detail: `${width}×${height}`,
      };
    default:
      return null;
  }
}

/**
 * @param {object} domain
 * @param {string} checkProfile
 * @param {{width:number,height:number,sizeBytes:number}} ctx
 */
export function validateByProfile(domain, checkProfile, ctx) {
  const profile =
    domain.check_profiles[checkProfile] || domain.check_profiles.plain || [];
  const checks = [];
  for (const id of profile) {
    if (id === "pdf_pages_ref") continue;
    const item = runCheck(domain, id, ctx);
    if (item) checks.push(item);
  }
  return checks;
}
