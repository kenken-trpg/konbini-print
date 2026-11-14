# vendor（ピン留め）

CDN 非依存のため同梱。バージョンを上げるときはここを更新する。

| パッケージ | バージョン | ファイル |
|------------|------------|----------|
| jszip | 3.10.1 | `jszip.min.js` |
| heic2any | 0.0.4 | `heic2any.min.js` |
| pdfjs-dist | 4.10.38 | `pdfjs/pdf.min.mjs`, `pdfjs/pdf.worker.min.mjs` |

取得元（再取得時）:

```bash
cd client/vendor
curl -fsSL -o jszip.min.js "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"
curl -fsSL -o heic2any.min.js "https://cdn.jsdelivr.net/npm/heic2any@0.0.4/dist/heic2any.min.js"
curl -fsSL -o pdfjs/pdf.min.mjs "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs"
curl -fsSL -o pdfjs/pdf.worker.min.mjs "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs"
```
