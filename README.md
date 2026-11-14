# コンビニプリント一括変換

ネットワークプリント / セブンネットプリント向けに、画像・PDF を登録しやすい形式へ一括変換するツールです。
**Streamlit 版**（サーバー変換・公開 URL 取得あり）と、**ブラウザ版** `client/`（ファイルを端末の外に出さない）の 2 つを同じリポジトリで並行して維持します。

## 構成

```text
app.py                 # Streamlit UI のみ
src/
  __init__.py          # 公開 API（process_files / ProcessOptions / load_domain 等）
  domain/              # ドメイン層（domain.json・プリセット・制限・検証）
  convert/             # 変換層（画像・PDF・pipeline の再エクスポート）
  io/                  # I/O 層（URL・ZIP・ファイル名・ログ）
  pipeline.py / handlers/ / image_convert.py / ...
client/                # ブラウザ版（静的ファイルのみ。client/README.md）
docs/
```

変換ロジックは次のように UI なしでも利用できます。

```python
from src import InputFile, ProcessOptions, process_files, PRESETS, load_domain, setup_logging

setup_logging()
batch = process_files(
    [InputFile("photo.webp", data)],
    PRESETS["both_l"],
    options=ProcessOptions(fit_mode="fit"),
)
```

プリセットは `pipeline`（`image` / `pdf` / `images_to_pdf` / `pack`）と自己完結の `variants` でテーブル駆動です。
ブラウザ版の構成・起動・Streamlit 版との対応は [`client/README.md`](client/README.md)、2 つを並行維持する運用ルールは [`docs/CLIENT_SIDE.md`](docs/CLIENT_SIDE.md#並行維持の方針) を参照してください。


- HEIC / WebP 含む画像の一括変換
- フォト用紙（L / 2L）・スクエア・はがき・普通紙 A4 プリセット
- 全用途パックの出力選択（L / 2L / A4）
- 変換前チェック・適合マトリクス・変換前後比較
- セーフエリア（端カット対策）とプレビュー枠
- ファイル名は日本語・記号をなるべく維持（危険文字と絵文字のみ整理）。拡張子・連番込みで 100 文字以内に切り詰める（ネットワークプリントの制限）
- デフォルトは「切れず余白あり（フィット）」
- 10MB 以内への JPEG 品質自動調整
- PDF 互換化（書き直し / ラスタライズ）
- 画像まとめ PDF
- 適合チェック表示 + ZIP ダウンロード

## ローカル起動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## テスト

```bash
pip install -r requirements-dev.txt
pytest

# ブラウザ版（Node 18+、依存なし）
cd client && npm test
```

CI（`.github/workflows/ci.yml`）は push / PR ごとに両方を実行します。

## ログ

例外は `logs/konbini-print.log` に記録されます（ローテーション付き）。

| 項目 | 既定 | 環境変数 |
|------|------|----------|
| ディレクトリ | `logs/` | `KONBINI_LOG_DIR` |
| 1ファイル上限 | 2MB | `KONBINI_LOG_MAX_BYTES` |
| 世代数 | 5（合計おおよそ 10MB 前後） | `KONBINI_LOG_BACKUP_COUNT` |
| レベル | INFO | `KONBINI_LOG_LEVEL` |

ファイル本体やバイナリは記録しません。Streamlit Cloud ではディスクが揮発的な点に注意してください。

## ドメイン知識（単一ソース）

印刷制限・プリセット・向き先・サービス説明・リソース上限の既定値は
`src/domain/domain.json` に集約されています。Python 側の `config` / `targets` /
`service_info` / `validate` / `limits` はこれをロードする薄い層です。

クライアントフォーク時は、この JSON を共有してください。

## リソース上限・URL 取得

DoS / OOM / SSRF 対策の既定上限（環境変数で上書き可）:

| 項目 | 既定 | 環境変数 |
|------|------|----------|
| 入力ファイル数 | 20 | `KONBINI_MAX_INPUT_FILES` |
| 入力合計サイズ | 40MB | `KONBINI_MAX_INPUT_TOTAL_BYTES` |
| Streamlit 1ファイル Upload | 40MB（`.streamlit/config.toml`） | `server.maxUploadSize` |
| URL 件数 | 10 | `KONBINI_MAX_URLS_PER_REQUEST` |
| 1URL ダウンロード | 25MB | `KONBINI_MAX_DOWNLOAD_BYTES` |
| 画像ピクセル | 2500万 | `KONBINI_MAX_IMAGE_PIXELS` |
| PDF ページ数 | 100 | `KONBINI_MAX_PDF_PAGES` |
| ラスタライズ DPI | 200 | `KONBINI_MAX_RASTERIZE_DPI` |
| URL 取得の有効化 | on | `KONBINI_ALLOW_URL_FETCH`（`0`/`false`/`off` で無効） |
| セッション結果保持 | 30件 / 50MB | `KONBINI_MAX_SESSION_OUTPUTS` / `KONBINI_MAX_SESSION_RESULT_BYTES` |

公開 URL 取得は http/https のみ、プライベート IP・メタデータホストを拒否し、DNS 解決後に IP をピン留めして接続、リダイレクトは各ホップで再検証します。

macOS で HEIC を使う場合:

```bash
brew install libheif
```

## Streamlit Community Cloud

1. このリポジトリを GitHub に push
2. [Share.streamlit.io](https://share.streamlit.io/) でデプロイ
3. Main file path: `app.py`
4. `packages.txt` で `libheif` を入れて HEIC 対応

## 注意

- **非公式**の変換ツールです。各ネットプリント公式サービスではありません
- 公式サービスへの自動アップロードは行いません
- アップロードファイルは永続保存しません
- 公式仕様は変更され得ます。詳細は `docs/REQUIREMENTS.md` およびアプリ内の制限表・公式リンクを参照

公式:
- [ネットワークプリント](https://networkprint.ne.jp/)
- [セブンネットプリント](https://www.printing.ne.jp/)
