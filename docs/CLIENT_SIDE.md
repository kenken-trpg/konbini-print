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

## 推奨ロードマップ

1. **本線（このリポジトリ）**: サーバー変換 + アップロード + 公開 URL 取得（現行）
2. **スパイクブランチ** `spike/client-side`: ブラウザでフィット＆圧縮を再現  
   ※ `client/` は本線ツリーに置かない（デプロイ対象・レビュー範囲を曖昧にしない）  
   ※ 置き場・起動手順: ブランチ上の [`client/README.md`](../client/README.md)  
   ※ スパイク済み: JPEG/PNG/WebP + **ZIP** + **HEIC** + **PDF 3a（ページ→JPEG）**（URL 取得なし）  
   ※ 本線との比較チェックリスト: [`client/README.md`](../client/README.md#本線との比較チェックリスト)（**1〜8 検証完了 / Go**）
3. 比較は **Go（検証完了）**。最終形は**別リポジトリ分離 → GitHub Pages**。  
   UX 等の追加はこのブランチでも可。区切り後に分離する

共有契約は本線の `src/domain/domain.json` をコピー／参照する（スパイクでは `client/domain.json`）。

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
