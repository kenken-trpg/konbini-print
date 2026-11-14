# クライアント側変換の検討メモ

## 結論（現実性）

| 方式 | 判定 | 理由 |
|------|------|------|
| 現行 Streamlit（サーバー変換） | 現実的（現行） | Python 資産をそのまま使える。Cloud で動かしやすい |
| Streamlit のままクライアント変換 | **あまり現実的でない** | Streamlit はサーバー実行が前提。真のクライアント処理は custom component / 別フロントが必要で、Streamlit の旨味が薄い |
| ブラウザ完結（SPA / PWA） | **画像主体なら現実的** | Canvas / WASM で JPEG・PNG・WebP・リサイズ・圧縮は十分可能。プライバシーと Cloud コストに有利 |
| ハイブリッド（取得だけサーバー／変換はクライアント） | 中程度 | URL 取得の CORS 問題をサーバーで吸収しつつ、画像本体はブラウザ処理、という分担はあり |

**大幅変更になる**ため、本線（Streamlit サーバー変換）とは別ブランチ／別リポジトリでスパイクするのがよい。

## クライアント側でできること / 難しいこと

### 比較的容易
- JPEG / PNG / WebP のデコード・リサイズ・フィット余白・JPEG 品質調整
- 10MB 制限への圧縮ループ
- 複数ファイル → ZIP（JSZip 等）
- 結果プレビュー

### 追加コストあり
- **HEIC**: `libheif` WASM / `heic2any` 等が必要。バンドルサイズ・互換性に注意
- **PDF**: `pdf.js`（描画）+ `pdf-lib`（生成）。ラスタライズ互換は重いが可能
- **公開 URL 取得**: ブラウザからは **CORS** で失敗しやすい。  
  - 対策A: ユーザーがファイルを落とす／拡張機能  
  - 対策B: 薄いプロキシ（サーバー）で取得のみ代行（SSRF 対策必須）  
  - 対策C: サーバー変換のまま URL 取得（現行アプリの拡張＝実装済み）

## Streamlit Community Cloud との関係

- クライアント変換の本体は **静的ホスティング**（GitHub Pages / Cloudflare Pages / Netlify）の方が合う
- Streamlit Cloud に静的フロントを無理に載せるメリットは小さい
- 「公式っぽい変換ツール」を Cloud で出すなら、当面はサーバー変換＋URL 取得で十分

## これまでの経緯

1. Streamlit 版（サーバー変換 + アップロード + 公開 URL 取得）を先に整備した
2. ブランチ `spike/client-side` でブラウザ版を試作した。この間は「`client/` は master に置かない（デプロイ対象・レビュー範囲を曖昧にしない）」としていた  
   ※ 試作の範囲: JPEG/PNG/WebP + **ZIP** + **HEIC** + **PDF 3a（ページ→JPEG）**（URL 取得なし）  
   ※ Streamlit 版との比較: [`client/README.md`](../client/README.md#本線との比較チェックリスト)（**1〜8 検証完了 / Go**）
3. 当初は「別リポジトリに分離して GitHub Pages で公開」を最終形としていたが、2026-11-14 に下記の方針へ変更した

## 並行維持の方針

**決定（2026-11-14）**: Streamlit 版とブラウザ版を**両方長く維持する**。そのため `client/` を **同じリポジトリの master に置く**（別リポジトリには分けない）。

理由:

- `domain.json` と、ファイル名の整え方などのルールを 2 つの実装で共有しているため。同じリポジトリなら、ずれの検知と両方の修正を 1 つの PR で済ませられる（例: ファイル名 100 文字制限は Python と JS の両方に入れる必要があった）
- 長く残るブランチや別リポジトリでは、手作業の同期と cherry-pick が続く

運用ルール:

| 項目 | ルール |
|------|--------|
| `domain.json` | 正本は `src/domain/domain.json`。変更したら `client/domain.json` にもコピーする。`tests/test_client_domain_sync.py` が一致しないと失敗する |
| 共通ルールの変更 | ファイル名・上限値・適合チェックなど両方に関わる変更は、**同じ PR で Python と JS の両方**を直し、両方にテストを付ける |
| 片方だけの変更 | PR は片方に閉じる（`client/` だけ／`src/`・`app.py` だけ）。範囲が混ざる大きな変更は PR を分ける |
| CI | `.github/workflows/ci.yml` が `pytest` と `client` の `npm test` を両方実行する |
| デプロイ | Streamlit Cloud は `app.py` だけを動かすので、`client/` は影響しない。ブラウザ版は GitHub Pages（https://kenken-trpg.github.io/konbini-print/）で公開する。`.github/workflows/pages.yml` が master への push（`client/` か `src/domain/domain.json` の変更時）でテスト → `client/` 配下だけを配信する |
| 意図的な差 | 機能差（URL 取得はブラウザ版なし、PDF の扱いなど）は [`client/README.md`](../client/README.md#仕様メモバグではない差分運用) に記録する |

## 本線コア API（フォーク起点）

Streamlit 非依存で呼べます。ドメイン知識は `src/domain/domain.json` が単一ソースです。

層:
- `src.domain` … プリセット・制限・検証
- `src.convert` … 変換
- `src.io` … 取得・ZIP・ログ

```python
from src import InputFile, ProcessOptions, process_files, PRESETS, load_domain

_ = load_domain()  # クライアント共有用 JSON と同じ定義をロード

batch = process_files(
    [InputFile("photo.webp", data_bytes)],
    preset=PRESETS["both_l"],
    options=ProcessOptions(fit_mode="fit"),
)
for art in batch.outputs:
    art.name, art.data, art.mime, art.targets, art.checks
```

クライアント側スパイクは、同じ `domain.json` 契約と `InputFile` / `OutputArtifact` を JS 側で再現するのが目標です。
