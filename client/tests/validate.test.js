import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { aspectRatio, validateByProfile } from "../js/validate.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const domain = JSON.parse(readFileSync(join(root, "domain.json"), "utf8"));

describe("aspectRatio", () => {
  it("L canvas landscape ≈ 1.427", () => {
    assert.ok(Math.abs(aspectRatio(1500, 1051) - 1.427) < 1e-3);
  });

  it("zero short side → 0", () => {
    assert.equal(aspectRatio(0, 10), 0);
  });
});

describe("validateByProfile", () => {
  it("photo / L size passes all checks", () => {
    const checks = validateByProfile(domain, "photo", {
      width: 1500,
      height: 1051,
      sizeBytes: 100_000,
    });
    assert.ok(checks.length >= 4);
    assert.ok(checks.every((c) => c.ok));
  });

  it("photo rejects square ratio", () => {
    const checks = validateByProfile(domain, "photo", {
      width: 1000,
      height: 1000,
      sizeBytes: 1000,
    });
    const ratio = checks.find((c) => c.label.includes("縦横比"));
    assert.ok(ratio);
    assert.equal(ratio.ok, false);
  });

  it("plain rejects over 10MB", () => {
    const checks = validateByProfile(domain, "plain", {
      width: 800,
      height: 600,
      sizeBytes: 11 * 1024 * 1024,
    });
    const size = checks.find((c) => c.label.includes("10MB"));
    assert.ok(size);
    assert.equal(size.ok, false);
  });

  it("unknown profile falls back to plain", () => {
    const checks = validateByProfile(domain, "no_such_profile", {
      width: 800,
      height: 600,
      sizeBytes: 1000,
    });
    assert.ok(checks.some((c) => c.label.includes("10MB")));
    assert.ok(!checks.some((c) => c.label.includes("フォト縦横比")));
  });
});
