import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { uniquifyArcname } from "../js/arcname.js";
import { buildFilename, charLength, fitFilename, truncateChars } from "../js/filenames.js";
import { applyDomain, limits, resetLimits } from "../js/limits.js";
import { sanitizeFilename } from "../js/pipeline.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const domain = JSON.parse(readFileSync(join(root, "domain.json"), "utf8"));

// ネットワークプリントは 100 文字超のファイル名でアップロード失敗する
const MAX = 100;

describe("filename length limit", () => {
  it("domain.json の上限が limits に反映される", () => {
    resetLimits();
    applyDomain(domain);
    assert.equal(limits.maxFilenameChars, MAX);
    resetLimits();
    assert.equal(limits.maxFilenameChars, MAX);
  });

  it("truncateChars はサロゲートペアを途中で切らない", () => {
    assert.equal(truncateChars("𠮷𠮷𠮷", 2), "𠮷𠮷");
    assert.equal(charLength("𠮷野家"), 3);
  });

  it("buildFilename は stem だけを削り suffix と拡張子を残す", () => {
    const name = buildFilename("あ".repeat(200), "_001_plain_A4", ".jpg");
    assert.equal(charLength(name), MAX);
    assert.ok(name.endsWith("_001_plain_A4.jpg"));
    assert.equal(buildFilename("写真", "_001", ".jpg"), "写真_001.jpg");
  });

  it("buildFilename は削った後の末尾の区切りを落とす", () => {
    assert.equal(buildFilename("aaaaa" + " ".repeat(10), "_1", ".jpg", 12), "aaaaa_1.jpg");
  });

  it("buildFilename は収まらない suffix を拒否する", () => {
    assert.throws(() => buildFilename("a", "_".repeat(10), ".jpg", 12));
  });

  it("fitFilename は拡張子を残す", () => {
    const name = fitFilename("x".repeat(150) + ".pdf");
    assert.equal(charLength(name), MAX);
    assert.ok(name.endsWith(".pdf"));
    assert.equal(fitFilename("short.pdf"), "short.pdf");
  });

  it("sanitizeFilename は長い名前・拡張漢字・大きい連番でも上限内", () => {
    for (const stem of ["あ".repeat(300), "𠮷".repeat(300), "a".repeat(300)]) {
      const name = sanitizeFilename(`${stem}_p001.jpg`, ".jpg", 12345);
      assert.ok(charLength(name) <= MAX, name);
      assert.ok(name.endsWith("_12345.jpg"));
    }
  });

  it("sanitizeFilename の stem は拡張漢字でも壊れない", () => {
    const name = sanitizeFilename("𠮷".repeat(100) + ".jpg", ".jpg", 1);
    assert.equal(name, "𠮷".repeat(80) + "_001.jpg");
  });

  it("uniquifyArcname は _n を付けても上限内", () => {
    const used = new Set();
    const long = "あ".repeat(MAX - 4) + ".jpg";
    const first = uniquifyArcname(long, used);
    const second = uniquifyArcname(long, used);
    const third = uniquifyArcname(long, used);
    assert.equal(first, long);
    assert.equal(new Set([first, second, third]).size, 3);
    for (const n of [second, third]) {
      assert.ok(charLength(n) <= MAX, n);
      assert.ok(n.endsWith(".jpg"));
    }
    assert.ok(second.endsWith("_2.jpg"));
    assert.ok(third.endsWith("_3.jpg"));
  });

  it("uniquifyArcname は 100 文字超の入力も切り詰める", () => {
    const name = uniquifyArcname("x".repeat(150) + ".png", new Set());
    assert.equal(charLength(name), MAX);
    assert.ok(name.endsWith(".png"));
  });
});
