/**
 * UI 配線（表示・イベント）。変換本体は pipeline.js。
 */

import { applyDomain } from "./limits.js";
import {
  parseBg,
  runBatchConvert,
  softLoadTips,
  validateInputBatch,
} from "./pipeline.js";
import { setVendorLoadHook } from "./vendor_status.js";
import { zipArtifacts } from "./zip.js";

/** 画面用のやさしいプリセット名 */
const PRESET_LABELS = {
  both_l: "写真 L（いちばんよく使う）",
  both_2l: "写真 2L（少し大きい）",
  both_plain_a4: "普通紙 A4",
  both_hagaki: "はがき",
  both_safe: "大きさはそのまま（安全め）",
  nw_l: "写真 L（ネットワークプリント向け）",
  nw_2l: "写真 2L（ネットワークプリント向け）",
  nw_square: "スクエア（四角い写真）",
  seven_l: "写真 L（セブン向け）",
  seven_2l: "写真 2L（セブン向け）",
};

/** @type {object|null} */
let domain = null;
/** @type {File[]} */
let selectedFiles = [];
/** @type {Array<{name:string, blob:Blob, mime:string, meta:string, checks:any[], warnings:string[], sourceName:string}>} */
let outputs = [];
/** @type {string[]} */
let objectUrls = [];

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function revokeObjectUrls() {
  for (const url of objectUrls) {
    try {
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  }
  objectUrls = [];
}

function trackObjectUrl(blob) {
  const url = URL.createObjectURL(blob);
  objectUrls.push(url);
  return url;
}

function populatePresets() {
  const sel = $("preset");
  while (sel.firstChild) sel.removeChild(sel.firstChild);
  for (const id of domain.preset_order) {
    const p = domain.presets.find((x) => x.id === id);
    if (!p || p.pipeline !== "image") continue;
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = PRESET_LABELS[p.id] || p.label;
    sel.appendChild(opt);
  }
  sel.value = "both_l";
}

function currentPreset() {
  return domain.presets.find((p) => p.id === $("preset").value);
}

function setSelectedFiles(files) {
  selectedFiles = Array.from(files || []);
  const list = $("fileList");
  const title = $("dropTitle");
  const input = $("files");
  if (!selectedFiles.length) {
    list.hidden = true;
    list.textContent = "";
    title.textContent = "ここに写真を置く / タップして選ぶ";
    return;
  }
  title.textContent = `${selectedFiles.length} 個選べています`;
  const names = selectedFiles.map((f) => f.name);
  const shown = names.slice(0, 5).join("、");
  const more = names.length > 5 ? ` ほか ${names.length - 5} 個` : "";
  list.textContent = shown + more;
  list.hidden = false;
  try {
    const dt = new DataTransfer();
    for (const f of selectedFiles) dt.items.add(f);
    input.files = dt.files;
  } catch {
    /* selectedFiles を正とする */
  }
}

function setProgress({ done, total, text }) {
  const box = $("progress");
  const fill = $("progressFill");
  const label = $("progressText");
  if (!total || total <= 0) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  const pct = Math.min(100, Math.round((done / total) * 100));
  fill.style.width = `${pct}%`;
  label.textContent = text || `${done} / ${total}`;
}

function clearProgress() {
  $("progress").hidden = true;
  $("progressFill").style.width = "0%";
  $("progressText").textContent = "";
}

function renderIssues(messages) {
  const box = $("issues");
  while (box.firstChild) box.removeChild(box.firstChild);
  if (!messages.length) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  box.appendChild(el("p", "issues-title", `うまくいかなかったもの（${messages.length}）`));
  const ul = document.createElement("ul");
  for (const msg of messages) {
    ul.appendChild(el("li", null, msg));
  }
  box.appendChild(ul);
}

function plainCheckLabel(label) {
  const map = {
    "容量 ≤10MB": "ファイルの重さ（10MB以内）",
    "最小サイズ目安（ネットワークプリント）": "小さすぎないか",
    "フォト縦横比 1.3〜1.5": "写真の縦横のバランス",
    "スクエア縦横比 ≈1.0": "四角い写真のバランス",
    "最大辺 ≤6144px": "大きすぎないか",
    "最小サイズ目安（セブン）": "セブン向けの最小サイズ",
  };
  return map[label] || label;
}

function renderResults() {
  const box = $("results");
  const heading = $("resultsHeading");
  revokeObjectUrls();
  while (box.firstChild) box.removeChild(box.firstChild);

  if (!outputs.length) {
    heading.hidden = true;
    box.appendChild(el("p", "muted", "整えた写真がここに出ます。まだ何もありません。"));
    $("downloadZip").disabled = true;
    return;
  }

  heading.hidden = false;
  $("downloadZip").disabled = false;

  for (const art of outputs) {
    const url = trackObjectUrl(art.blob);
    const card = el("article", "result");
    const preview = el("div", "result-preview");
    const img = document.createElement("img");
    img.src = url;
    img.alt = art.name;
    preview.appendChild(img);

    const body = el("div", "result-body");
    body.appendChild(el("h3", null, art.name));
    body.appendChild(el("p", "meta", art.meta));

    const allOk = art.checks.every((c) => c.ok);
    body.appendChild(
      el(
        "p",
        `verdict ${allOk ? "ok" : "ng"}`,
        allOk ? "目安チェック：問題なさそう" : "目安チェック：気になる点あり"
      )
    );

    const checks = el("ul", "checks");
    for (const c of art.checks) {
      const li = el(
        "li",
        c.ok ? "ok" : "ng",
        `${c.ok ? "✓" : "✗"} ${plainCheckLabel(c.label)} `
      );
      li.appendChild(el("span", null, c.detail));
      checks.appendChild(li);
    }
    body.appendChild(checks);

    if (art.warnings.length) {
      const warns = el("ul", "warns");
      for (const w of art.warnings) {
        warns.appendChild(el("li", null, w));
      }
      body.appendChild(warns);
    }

    const a = el("a", "btn secondary", "この写真を保存");
    a.href = url;
    a.download = art.name;
    body.appendChild(a);

    card.appendChild(preview);
    card.appendChild(body);
    box.appendChild(card);
  }
}

async function runConvert() {
  const files = selectedFiles;
  const status = $("status");
  const preset = currentPreset();
  renderIssues([]);
  clearProgress();

  if (!files.length) {
    status.textContent = "先に写真を選んでください。";
    return;
  }
  if (!preset) {
    status.textContent = "用紙の大きさを選び直してください。";
    return;
  }

  const batchErrors = validateInputBatch(files);
  if (batchErrors.length) {
    status.textContent = "入れすぎのため、作業を止めました。";
    renderIssues(batchErrors);
    return;
  }

  const tips = softLoadTips(files);
  status.textContent = tips[0] || "整えています…（写真は外に送っていません）";

  $("convertBtn").disabled = true;
  try {
    const result = await runBatchConvert({
      domain,
      preset,
      files,
      fitMode: $("fitMode").value,
      safeInset: $("safeInset").checked,
      bg: parseBg($("bg").value),
      onProgress: setProgress,
    });
    outputs = result.outputs;
    const skipped = result.skipped;

    setProgress({
      done: 1,
      total: 1,
      text: outputs.length ? `${outputs.length} 枚できました` : "1枚もできませんでした",
    });

    let msg = outputs.length
      ? `${outputs.length} 枚できました。下から保存できます。`
      : "1枚もできませんでした。";
    if (skipped.length) msg += ` うまくいかなかったもの ${skipped.length} 件あり。`;
    status.textContent = msg;
    renderIssues(skipped);
    renderResults();
  } catch (err) {
    console.error(err);
    status.textContent = err?.message || String(err);
    renderIssues([err?.message || String(err)]);
    clearProgress();
  } finally {
    $("convertBtn").disabled = false;
  }
}

async function downloadZip() {
  if (!outputs.length) return;
  const status = $("status");
  status.textContent = "まとめファイルを作っています…";
  $("downloadZip").disabled = true;
  let zipUrl = null;
  try {
    const blob = await zipArtifacts(outputs.map((o) => ({ name: o.name, blob: o.blob })));
    zipUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = zipUrl;
    a.download = "konbini-print.zip";
    a.click();
    status.textContent = `まとめファイルを保存しました（${outputs.length} 枚入り）。`;
  } catch (err) {
    console.error(err);
    status.textContent = `まとめ保存に失敗しました: ${err?.message || err}`;
    renderIssues([`まとめ保存: ${err?.message || err}`]);
  } finally {
    if (zipUrl) URL.revokeObjectURL(zipUrl);
    $("downloadZip").disabled = false;
  }
}

/**
 * ネイティブ file input をフォーカス可能にし、label で操作する。
 * role=button + 全面透明 input はやめて、キーボード差を減らす。
 */
function wireDropzone() {
  const zone = $("dropzone");
  const input = $("files");

  input.addEventListener("change", () => {
    if (input.files?.length) setSelectedFiles(input.files);
  });

  const prevent = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };
  ["dragenter", "dragover", "dragleave", "drop"].forEach((type) => {
    zone.addEventListener(type, prevent);
  });
  zone.addEventListener("dragenter", () => zone.classList.add("is-dragover"));
  zone.addEventListener("dragover", () => zone.classList.add("is-dragover"));
  zone.addEventListener("dragleave", (e) => {
    if (!zone.contains(e.relatedTarget)) zone.classList.remove("is-dragover");
  });
  zone.addEventListener("drop", (e) => {
    zone.classList.remove("is-dragover");
    const files = e.dataTransfer?.files;
    if (files?.length) setSelectedFiles(files);
  });
}

async function main() {
  const res = await fetch("./domain.json");
  if (!res.ok) {
    throw new Error(
      "設定ファイルを読めませんでした。アプリを http で開いているか確認してください。"
    );
  }
  domain = await res.json();
  applyDomain(domain);

  setVendorLoadHook(({ label, phase }) => {
    const status = $("status");
    if (!status) return;
    if (phase === "start") {
      status.textContent = `${label}を読み込んでいます（初回だけ・この端末内）。少し待ってください…`;
      setProgress({ done: 0, total: 1, text: `${label}を準備中…` });
    } else if (phase === "done") {
      status.textContent = `${label}の準備ができました。続けて整えます…`;
    } else if (phase === "error") {
      status.textContent = `${label}を読めませんでした。ページを再読み込みして試してください。`;
    }
  });

  populatePresets();
  renderIssues([]);
  renderResults();
  wireDropzone();

  $("convertBtn").addEventListener("click", runConvert);
  $("downloadZip").addEventListener("click", downloadZip);
}

main().catch((err) => {
  const status = $("status");
  if (status) status.textContent = err?.message || String(err);
});
