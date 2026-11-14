import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { afterEach, describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { applyDomain, limits, resetLimits } from "../js/limits.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const domain = JSON.parse(readFileSync(join(root, "domain.json"), "utf8"));

afterEach(() => {
  resetLimits();
});

describe("applyDomain", () => {
  it("mirrors print_limits and resource_limits", () => {
    applyDomain(domain);
    assert.equal(limits.maxFileBytes, domain.print_limits.max_file_bytes);
    assert.equal(limits.minJpegQuality, domain.print_limits.min_jpeg_quality);
    assert.equal(limits.defaultJpegQuality, domain.print_limits.default_jpeg_quality);
    assert.deepEqual(limits.defaultBg, domain.print_limits.default_bg);
    assert.equal(limits.maxSide, domain.print_limits.seven_photo.max_side);
    assert.equal(limits.maxImagePixels, domain.resource_limits.max_image_pixels);
    assert.equal(limits.maxInputFiles, domain.resource_limits.max_input_files);
    assert.equal(limits.maxInputTotalBytes, domain.resource_limits.max_input_total_bytes);
    assert.equal(limits.maxSessionOutputs, domain.resource_limits.max_session_outputs);
  });

  it("caps maxPdfPages at 20 even if domain is higher", () => {
    applyDomain(domain);
    assert.ok((domain.resource_limits.max_pdf_pages || 0) >= 20);
    assert.equal(limits.maxPdfPages, 20);
  });
});
