import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  isImageName,
  parseBg,
  sanitizeFilename,
  softLoadTips,
  validateInputBatch,
} from "../js/pipeline.js";
import { applyDomain, limits, resetLimits } from "../js/limits.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const domain = JSON.parse(readFileSync(join(root, "domain.json"), "utf8"));

describe("pipeline helpers", () => {
  it("parseBg accepts #rrggbb", () => {
    assert.deepEqual(parseBg("#0f5c4c"), [15, 92, 76]);
    assert.deepEqual(parseBg("ffffff"), [255, 255, 255]);
    assert.deepEqual(parseBg("bad"), [255, 255, 255]);
  });

  it("sanitizeFilename adds index and strips unsafe", () => {
    assert.equal(sanitizeFilename("a<b>.webp", ".jpg", 1), "a_b_001.jpg");
  });

  it("isImageName recognizes common types", () => {
    assert.equal(isImageName("x.HEIC"), true);
    assert.equal(isImageName("x.pdf"), false);
  });

  it("validateInputBatch uses limits from domain", () => {
    resetLimits();
    applyDomain(domain);
    const tooMany = Array.from({ length: limits.maxInputFiles + 1 }, (_, i) => ({
      name: `f${i}.jpg`,
      size: 10,
    }));
    const errs = validateInputBatch(tooMany);
    assert.ok(errs.some((e) => e.includes("個まで")));
    resetLimits();
  });

  it("softLoadTips warns on many files", () => {
    const files = Array.from({ length: 12 }, (_, i) => ({
      name: `f${i}.jpg`,
      size: 100,
    }));
    const tips = softLoadTips(files);
    assert.ok(tips.some((t) => t.includes("枚数が多い")));
  });

  it("softLoadTips with PDF does not throw without navigator (Node)", () => {
    const files = [{ name: "doc.pdf", size: 9 * 1024 * 1024 }];
    const tips = softLoadTips(files);
    assert.ok(tips.some((t) => t.includes("重めの PDF")));
  });

  it("isLikelyMobile accepts explicit UA and empty env", async () => {
    const { isLikelyMobile } = await import("../js/pipeline.js");
    assert.equal(isLikelyMobile("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"), true);
    assert.equal(isLikelyMobile("Mozilla/5.0 (Macintosh)"), false);
    assert.equal(isLikelyMobile(""), false);
  });
});
