/**
 * 変換の「薄い回帰」: Canvas は使わず、both_l 相当の px・比・チェック合否だけ固定する。
 * （実変換の黄金値は本線 pytest + 人手比較チェックリスト側）
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { aspectRatio, validateByProfile } from "../js/validate.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const domain = JSON.parse(readFileSync(join(root, "domain.json"), "utf8"));

/** 比較チェックリストで確認した L フィット結果（landscape） */
const L_LANDSCAPE = { width: 1500, height: 1051, sizeBytes: 14_000 };
/** 同・縦向き（PDF ラスタ後などに出る） */
const L_PORTRAIT = { width: 1051, height: 1500, sizeBytes: 12_000 };

describe("thin regression: both_l check outcomes", () => {
  it("L landscape: ratio in 1.3–1.5 and all photo checks ok", () => {
    const ratio = aspectRatio(L_LANDSCAPE.width, L_LANDSCAPE.height);
    assert.ok(ratio >= 1.3 && ratio <= 1.5);
    const checks = validateByProfile(domain, "photo", L_LANDSCAPE);
    assert.deepEqual(
      checks.map((c) => [c.label, c.ok]),
      [
        ["容量 ≤10MB", true],
        ["最小サイズ目安（ネットワークプリント）", true],
        ["フォト縦横比 1.3〜1.5", true],
        ["最大辺 ≤6144px", true],
        ["最小サイズ目安（セブン）", true],
      ]
    );
  });

  it("L portrait: same profile all ok", () => {
    const checks = validateByProfile(domain, "photo", L_PORTRAIT);
    assert.ok(checks.every((c) => c.ok));
    assert.equal(checks.find((c) => c.label.includes("縦横比"))?.detail, "1.427");
  });

  it("canvas sizes in domain match L short/long", () => {
    assert.deepEqual(domain.canvases.L, [1051, 1500]);
  });
});
