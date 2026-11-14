# クライアント側スパイク（spike/client-side）

ブラウザ完結で画像をフィット＆圧縮する試作です。  
ファイル本体は **サーバーに送りません**（ローカル Canvas のみ）。プライバシーと Cloud 負荷低減の検証用です。

本線（Streamlit サーバー変換）とは別ブランチです。  
モノレポ内の検討メモ: [`docs/CLIENT_SIDE.md`](../docs/CLIENT_SIDE.md)（**Pages 公開時は本 README のみ**を参照。`../docs` は配信対象外）

## スコープ（このスパイク）

| 対応 | 未対応（意図的） |
|------|------------------|
| JPEG / PNG / WebP | 公開 URL 取得（CORS） |
| GIF（**先頭フレームのみ**） | アニメ GIF の全コマ |
| HEIC（heic2any → PNG 中間 → フィット後 JPEG） | PDF 再保存・まとめ PDF |
| PDF 3a: pdf.js でページ→JPEG（先頭最大20頁） | Streamlit 連携 |
| キャンバスフィット（fit / crop）・セーフエリア | |
| 10MB 以内への JPEG 品質／解像度調整 | |
| ZIP 一括ダウンロード（JSZip・同名リネーム） | |
| `domain.json` プリセット・適合チェック | |

共有契約: [`domain.json`](./domain.json)（本線 `src/domain/domain.json` のコピー）  
上限値は起動時に `js/limits.js` へ反映し、`convert.js` と共有する。

HEIC / PDF / ZIP 用ライブラリは [`vendor/`](./vendor/) に **ピン留め同梱**（CDN 非依存）。  
**初回にその機能を使うときだけ**読み込む（JPEG/PNG/WebP だけなら vendor を読まない）。合計およそ 3MB。  
フォントも外部配信を使わない（端末の日本語フォント）。

## 起動

```bash
# リポジトリルートから
cd client
python3 -m http.server 8765
```

確認用 URL: [http://localhost:8765/](http://localhost:8765/)

`file://` だと `domain.json` の fetch が失敗することがあるため、HTTP で開いてください。

## テスト

依存追加なし（Node 18+ の `node:test`）。Canvas 変換の E2E は含まず、純関数＋チェック合否の薄い回帰。

```bash
cd client
npm test
```

本線との `domain.json` 同一は pytest 側でも検知する（リポジトリルート）:

```bash
pytest tests/test_client_domain_sync.py
```

| ファイル | 内容 |
|----------|------|
| `tests/validate.test.js` | aspectRatio / validateByProfile |
| `tests/arcname.test.js` | ZIP 同名リネーム |
| `tests/filenames.test.js` | ファイル名 100 文字制限（ネットワークプリント） |
| `tests/limits.test.js` | applyDomain |
| `tests/checks_regression.test.js` | L サイズの px・比・チェック合否（薄い回帰） |
| `../tests/test_client_domain_sync.py` | client ↔ 本線 domain.json 同一 |

## 構成

```text
client/
  index.html
  domain.json
  package.json      # npm test → node --test
  css/style.css
  js/
    app.js          # UI 配線のみ
    pipeline.js     # 変換オーケストレーション（DOM 非依存）
    limits.js / convert.js / validate.js
    arcname.js / zip.js / heic.js / pdf_raster.js
  tests/
  vendor/
```

## 本線との対応

| Python（本線） | このスパイク |
|----------------|--------------|
| `src.image_convert.convert_image` | `js/convert.js` → `convertImage` |
| `src.validate.validate_by_profile` | `js/validate.js` → `validateByProfile` |
| `src.ziputil.zip_artifacts` | `js/zip.js` → `zipArtifacts` |
| HEIC（pillow-heif） | `js/heic.js`（heic2any） |
| PDF ラスタ相当の一部 | `js/pdf_raster.js`（pdf.js・再保存なし） |
| `src.domain.domain.json` | `client/domain.json` |

## 本線との比較チェックリスト

条件: プリセット **both_l** / 余白 **#ffffff** / 入力 `sample.webp`（特記なき限り）。  
本線は `process_files`、スパイクはブラウザ `convertImage`（計測日: 2026-07-25）。  
**検証ステータス: 完了（このブランチの比較は一区切り）**

| # | 項目 | 本線 | スパイク | 判定 | メモ |
|---|------|------|----------|------|------|
| 1 | WebP fit | 1500×1051 / 14339 B | 1500×1051 / ~14–15 KB / q=90 | **近い** | px・比一致。JPEG 容量はエンコーダ差 |
| 2 | JPEG / PNG | 同 L サイズ帯 | 同 L サイズ帯 | **近い** | 透過 PNG も RGB 合成後フィット |
| 3 | HEIC | （リポ内サンプルなし） | `IMG_2145.HEIC` で成功 | **近い** | 2026-07-25 手元確認済み |
| 4 | PDF 1ページ | 画像プリセットでは **スキップ** | ラスタ JPEG（比 1.427） | **差あり（意図）** | 3a。再保存互換は期待しない |
| 5 | crop と fit | fit 余白 LTRB≈(47,0,49,0) / crop 余白(0,0,0,0)・フル塗り | 同: fit(47,0,49,0) / crop(0,0,0,0) | **近い** | 見え方の差（余白 vs 全面）が一致。容量は crop の方が小さい帯 |
| 6 | セーフエリア ON | fit+safe 余白≈(80,22,91,27) / 17591 B | ≈(80,19,91,27) / 17599 B | **近い** | 上下余白に数 px の丸め差のみ。用途上許容 |
| 7 | 適合チェック | photo プロファイルすべて ✓ | すべて ✓ | **近い** | ラベル・合否一致 |
| 8 | 複数出力 → ZIP | 衝突時 `sample.jpg` + `sample_2.jpg` | 同（`uniquifyArcname`） | **近い** | 複数ファイル名 `_001`/`_002` 付与も同趣旨 |

**Go / No-Go（別リポ化）**

- [x] 1〜3・5〜8 が「近い」
- [x] 4 の差は意図的（PDF 3a）でメモ済み・許容
- [x] → **Go**: 別リポジトリへ分離 → GitHub Pages  
- [ ] → **No-Go**

※ このブランチ上の本線比較検証はここで完了。次は Pages 前チェック → 別リポ分離。

## 仕様メモ（バグではない差分・運用）

| 内容 | 扱い |
|------|------|
| 本線は画像プリセットで PDF を**スキップ**、スパイクは**ラスタ化** | 意図どおり（3a）。再保存互換は期待しない |
| ブラウザ JPEG と Pillow で容量が数 % ずれる | 比較済みで許容 |
| `domain.json` は本線の**コピー** | 本線更新時にドリフトしうる。別リポ後はコピー運用で同期 |
| GIF | 先頭フレームのみ（UI・警告で明記） |
| GitHub Pages | `client/` 配下だけ公開。フッターは `./README.md` のみ（`../docs` は使わない） |
| 外部フォント | 使わない（システム日本語フォント） |
| vendor | 機能初回のみ遅延読込＋「読み込み中」表示 |
| 大 PDF / 多枚 | ソフト警告、スマホは PDF 最大10頁・解像度抑制、失敗時は分割を案内 |

## Pages 前チェック（手動）

### vendor 遅延

- [ ] JPEG/PNG/WebP だけで開く → Network に `vendor/heic2any` / `vendor/pdfjs` / `vendor/jszip` が**出ない**
- [x] HEIC（`IMG_2145.HEIC`）で「整える」→ 読める／保存できる（初回 heic2any 読込含む想定）
- [ ] PDF を選んで「整える」→ 初回だけ `pdf.min.mjs` + worker が読まれる
- [ ] 「まとめて保存」→ 初回だけ `jszip.min.js` が読まれる
- [ ] Google Fonts 等への通信が無い

### iPhone 実機 HEIC（必須・CI 不可）

手順:

1. iPhone Safari でこのページを開く（または Pages 公開 URL）
2. 写真アプリの HEIC を1枚選ぶ（ライブ写真でも可）
3. 用紙「写真 L」→「整える」
4. プレビューが出て「この写真を保存」できる

確認メモ（記入用）:

| 項目 | 結果 | サンプル / 端末 | 日付 |
|------|------|-----------------|------|
| HEIC 1枚が読める | **OK** | `IMG_2145.HEIC` | 2026-07-25 |
| マルチ枚 HEIC（あれば） | 未 | | |
| 失敗時メッセージが分かるか | 未 | | |

- [x] HEIC 1枚以上で実機（または手元端末）確認済み（`IMG_2145.HEIC`）

### その他

- [ ] ページ多め PDF：警告が出る／止まっても分かりやすいメッセージ
- [ ] Tab → ファイル選択にフォーカスが移り、Enter/Space でピッカーが開く（a11y）

## 方針（決定）

最終形: **別リポジトリ分離 → GitHub Pages で公開**。  
いまは分離せず、このブランチ（`spike/client-side`）で修正・機能拡大を続ける。  
本線 `master` には `client/` をマージしない。

## 次のステップ

1. ~~比較チェックリスト（1〜8）~~ → **検証完了 / Go**
2. ~~UX / Pages 前の中優先（vendor・フォント・大PDF・HEICメモ）~~
3. ~~HEIC 実機確認（`IMG_2145.HEIC`）~~ → OK。残り Pages 前チェックは任意
4. **別リポ分離** → **GitHub Pages** 公開

### このブランチでやりうる候補

- ~~レビュー / テスト / 比較 / UX / Pages前の中優先 / app分割・a11y・HEICメモ~~（対応済み）
- PDF 再保存（3b）は需要が出てから

本線ツリー（`master`）には `client/` を混ぜない方針です。
