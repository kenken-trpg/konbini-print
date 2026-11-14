import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { uniquifyArcname } from "../js/arcname.js";

describe("uniquifyArcname", () => {
  it("keeps first name", () => {
    const used = new Set();
    assert.equal(uniquifyArcname("a.jpg", used), "a.jpg");
    assert.ok(used.has("a.jpg"));
  });

  it("suffixes duplicates _2, _3", () => {
    const used = new Set();
    assert.equal(uniquifyArcname("a.jpg", used), "a.jpg");
    assert.equal(uniquifyArcname("a.jpg", used), "a_2.jpg");
    assert.equal(uniquifyArcname("a.jpg", used), "a_3.jpg");
  });

  it("handles names without extension", () => {
    const used = new Set();
    assert.equal(uniquifyArcname("raw", used), "raw");
    assert.equal(uniquifyArcname("raw", used), "raw_2");
  });
});
