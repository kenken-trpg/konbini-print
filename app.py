"""コンビニネットプリント向け Streamlit UI（変換ロジックは src.pipeline）."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.config import (
    DOMAIN_VERIFIED_AS_OF,
    IMAGE_EXTENSIONS,
    PDF_SPLIT_PAGE_CHOICES,
    PRESET_ORDER,
    PRESETS,
    SERVICE_LABELS,
)
from src.dto import BatchResult, InputFile, OutputArtifact
from src.filenames import SEVEN_FILENAME_CAUTION
from src.fetch_url import UrlFetchError, fetch_public_url, parse_url_list, redact_url_for_log
from src.image_convert import HEIC_AVAILABLE
from src.limits import (
    ALLOW_URL_FETCH,
    MAX_DOWNLOAD_BYTES,
    MAX_INPUT_FILES,
    MAX_INPUT_TOTAL_BYTES,
    MAX_SESSION_OUTPUTS,
    MAX_SESSION_RESULT_BYTES,
    MAX_URLS_PER_REQUEST,
    ResourceLimitError,
    session_result_within_limits,
    would_exceed_input_total,
)
from src.logging_config import get_logger, log_exception, setup_logging
from src.matrix import compatibility_matrix, matrix_as_table_rows
from src.options import ProcessOptions
from src.pipeline import process_files
from src.precheck import probe_inputs
from src.preview import add_safe_area_guide, preview_bytes_for_artifact
from src.service_info import DISCLAIMER_MD, SERVICE_SPECS
from src.targets import PDF_COMPAT_HONEST
from src.validate import CheckItem
from src.ziputil import zip_artifacts

_SESSION_BATCH = "batch"
_SESSION_THUMBS = "batch_thumbs"
_SESSION_SOURCE_THUMBS = "source_thumbs"
_SESSION_ZIP = "batch_zip"
_SESSION_ZIP_ONLY = "batch_zip_only"


def _clear_results() -> None:
    st.session_state.pop(_SESSION_BATCH, None)
    st.session_state.pop(_SESSION_THUMBS, None)
    st.session_state.pop(_SESSION_SOURCE_THUMBS, None)
    st.session_state.pop(_SESSION_ZIP, None)
    st.session_state.pop(_SESSION_ZIP_ONLY, None)


def _store_batch(
    batch: BatchResult,
    source_thumbs: dict[str, bytes | None] | None = None,
) -> None:
    """結果をセッションに保存。大きすぎる場合は ZIP のみ保持してメモリを抑える."""
    total = sum(len(o.data) for o in batch.outputs)
    thumbs = [preview_bytes_for_artifact(o.data, o.mime) for o in batch.outputs]
    st.session_state[_SESSION_THUMBS] = thumbs

    within = session_result_within_limits(len(batch.outputs), total)
    if within:
        st.session_state[_SESSION_BATCH] = batch
        st.session_state[_SESSION_ZIP_ONLY] = False
        st.session_state.pop(_SESSION_ZIP, None)
        # 変換前後比較用ソースサムネは、結果の半分予算を超えないときだけ保持
        if source_thumbs is not None and total * 2 <= MAX_SESSION_RESULT_BYTES:
            st.session_state[_SESSION_SOURCE_THUMBS] = source_thumbs
        else:
            st.session_state.pop(_SESSION_SOURCE_THUMBS, None)
        return

    # メモリ圧迫回避: 個別 bytes を捨て、ZIP + メタ + サムネのみ
    zip_bytes = zip_artifacts(batch.outputs)
    light = BatchResult(
        outputs=[
            OutputArtifact(
                name=o.name,
                data=b"",
                mime=o.mime,
                meta=o.meta,
                checks=o.checks,
                warnings=list(o.warnings)
                + [
                    "セッションメモリ上限のため本体は ZIP のみ保持しています。"
                    "個別ダウンロードは ZIP を利用してください。"
                ],
                targets=list(o.targets),
                source_name=o.source_name,
                width=o.width,
                height=o.height,
                page_count=o.page_count,
                content_bytes=len(o.data),
            )
            for o in batch.outputs
        ],
        errors=list(batch.errors),
        skipped=list(batch.skipped),
    )
    st.session_state[_SESSION_BATCH] = light
    st.session_state[_SESSION_ZIP] = zip_bytes
    st.session_state[_SESSION_ZIP_ONLY] = True
    st.session_state.pop(_SESSION_SOURCE_THUMBS, None)


def _bg_from_hex(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _render_checks(checks: list[CheckItem]) -> None:
    for c in checks:
        icon = "✅" if c.ok else "⚠️"
        st.write(f"{icon} **{c.label}**: {c.detail}")


def _render_service_specs() -> None:
    with st.expander("対応入力詳細（サービス別の制限目安）", expanded=False):
        st.caption(
            "数値は公式仕様を参考にしています。変更されている場合があるため、リンク先で最新を確認してください。"
            f"（ドメイン定義の確認日: {DOMAIN_VERIFIED_AS_OF}）"
        )

        for spec in SERVICE_SPECS:
            st.markdown(f"**{spec['name']}**")
            link_parts = [f"[{link.label}]({link.url})" for link in spec["links"]]
            st.markdown("公式: " + " ｜ ".join(link_parts))
            rows = [
                {
                    "印刷選択肢": o.option,
                    "形式": o.formats,
                    "容量": o.size_limit,
                    "サイズ・ページ": o.dimensions,
                    "補足": o.notes,
                }
                for o in spec["options"]
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True)
            for line in spec["common"]:
                st.markdown(f"- {line}")
            st.divider()


def _collect_inputs(
    uploads,
    url_text: str,
) -> tuple[list[InputFile], list[tuple[str, str]]]:
    """アップロードと URL 取得結果を InputFile に正規化する.

    URL 取得は 1 件ずつ行い、入力合計バイトが上限に達したら打ち切る
    （取得完了後の validate まで待たない）。
    """
    inputs: list[InputFile] = []
    errors: list[tuple[str, str]] = []
    total_bytes = 0

    for u in uploads or []:
        data = u.getvalue()
        if would_exceed_input_total(total_bytes, len(data)):
            errors.append(
                (
                    u.name,
                    f"入力合計サイズが上限を超えるため取り込みを打ち切りました"
                    f"（最大 {MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB）。",
                )
            )
            break
        inputs.append(InputFile(name=u.name, data=data))
        total_bytes += len(data)

    urls: list[str] = []
    try:
        urls = parse_url_list(url_text)
    except UrlFetchError as exc:
        errors.append(("(URL一覧)", str(exc)))

    if urls:
        if not ALLOW_URL_FETCH:
            errors.append(
                (
                    "(URL取得)",
                    "URL 取得は無効化されています（KONBINI_ALLOW_URL_FETCH=0）。",
                )
            )
        elif total_bytes >= MAX_INPUT_TOTAL_BYTES:
            errors.append(
                (
                    "(URL取得)",
                    f"入力合計が既に上限（{MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB）"
                    "のため URL 取得をスキップしました。",
                )
            )
        else:
            with st.spinner(f"URL から取得中（{len(urls)} 件）..."):
                for url in urls:
                    if total_bytes >= MAX_INPUT_TOTAL_BYTES:
                        errors.append(
                            (
                                "(URL取得)",
                                f"入力合計サイズ上限（"
                                f"{MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB）に達したため"
                                "以降の URL 取得を打ち切りました。",
                            )
                        )
                        break
                    try:
                        fetched = fetch_public_url(url)
                        if would_exceed_input_total(total_bytes, len(fetched.data)):
                            errors.append(
                                (
                                    redact_url_for_log(url),
                                    f"取得ファイルを加えると入力合計上限（"
                                    f"{MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB）を超えるため"
                                    "スキップしました。",
                                )
                            )
                            break
                        inputs.append(InputFile(name=fetched.name, data=fetched.data))
                        total_bytes += len(fetched.data)
                    except UrlFetchError as exc:
                        log_exception(
                            "URL取得失敗", exc, source=redact_url_for_log(url)
                        )
                        errors.append((redact_url_for_log(url), str(exc)))
                    except Exception as exc:  # noqa: BLE001
                        log_exception(
                            "URL取得で予期しない例外",
                            exc,
                            source=redact_url_for_log(url),
                        )
                        errors.append((redact_url_for_log(url), str(exc)))

    return inputs, errors


def main() -> None:
    setup_logging()
    log = get_logger()
    log.info("アプリ起動")

    st.set_page_config(
        page_title="コンビニプリント変換",
        page_icon="🖨️",
        layout="wide",
    )
    st.title("コンビニプリント一括変換")
    st.caption(
        "ネットワークプリント / セブンネットプリント向けに、画像・PDF を登録しやすい形式へ変換します。"
    )

    st.info(
        "本アプリは**非公式**の変換ツールです。"
        "各ネットプリント公式サービスではありません。"
    )

    with st.expander("非公式サービスである旨・プライバシー", expanded=True):
        st.markdown(DISCLAIMER_MD)

    st.markdown(
        "公式サービス: "
        "[ネットワークプリント](https://networkprint.ne.jp/) ｜ "
        "[セブンネットプリント](https://www.printing.ne.jp/)"
    )

    _render_service_specs()

    if not HEIC_AVAILABLE:
        st.warning(
            "HEIC 対応ライブラリを検出できませんでした。WebP/JPEG/PNG 等は利用できます。"
            " Streamlit Cloud では `packages.txt` の libheif が必要です。"
        )

    st.markdown("### 変換")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        preset_id = st.selectbox(
            "プリセット",
            options=PRESET_ORDER,
            format_func=lambda k: PRESETS[k].label,
            index=0,
            help="迷ったら【両サービス】から選んでください。両サービスの厳しい側に合わせています。",
        )
        preset = PRESETS[preset_id]
        fit_disabled = preset.pipeline in {"pdf"} or (
            preset.pipeline == "image" and preset.canvas is None
        )
        with st.expander("オプション", expanded=False):
            fit_mode = st.radio(
                "フィット方式",
                options=["fit", "crop"],
                format_func=lambda x: (
                    "切れず余白あり（フィット）" if x == "fit" else "中央クロップ"
                ),
                index=0,
                horizontal=True,
                disabled=fit_disabled,
            )
            bg_hex = st.color_picker("余白・透過の塗りつぶし色", value="#FFFFFF")
            st.markdown("**セーフエリア**")
            safe_inset = st.checkbox(
                "セーフエリア確保（端から約3%内側・セブン端カット対策）",
                value=False,
                help="変換時に内容を内側へ寄せ、余白を作ります。プレビュー枠とは別オプションです。",
                disabled=preset.pipeline in {"pdf"} and preset.kind == "pdf",
            )
            show_safe_guide = st.checkbox(
                "プレビューにセーフエリア枠を表示",
                value=True,
                help="結果プレビューに端カット目安の枠を重ねます（ダウンロード画像には入りません）。",
            )
            st.markdown("**PDFラスタライズ**")
            rasterize_pdf = st.checkbox(
                "PDF をラスタライズして再構成（互換性優先・画質低下）",
                value=False,
                help=(
                    "通常の「再保存」では注釈・フォント問題は解消しません。"
                    "登録できない場合にラスタライズを試してください。"
                ),
            )
            st.markdown("**PDFページ分割**")
            split_pdf = st.checkbox(
                "PDF をページ分割する（ユーザー選択）",
                value=False,
                help=(
                    "PDF 出力を指定ページ数ごとに分割します。"
                    "ネットワークプリント A4 系は 50、セブンは 99 が上限目安です。"
                ),
            )
            pages_per_file = st.selectbox(
                "1ファイルあたりのページ数",
                options=list(PDF_SPLIT_PAGE_CHOICES),
                index=list(PDF_SPLIT_PAGE_CHOICES).index(50),
                disabled=not split_pdf,
                help="分割単位。小さいほど登録しやすい一方、ファイル数は増えます。",
            )
            pack_suffixes: tuple[str, ...] | None = None
            if preset.pipeline == "pack" and preset.variants:
                st.markdown("**パック出力（必要な用途だけ）**")
                selected: list[str] = []
                cols = st.columns(len(preset.variants))
                for col, variant in zip(cols, preset.variants, strict=True):
                    with col:
                        label = {
                            "photo_L": "フォト L",
                            "photo_2L": "フォト 2L",
                            "plain_A4": "普通紙 A4",
                        }.get(variant.suffix, variant.suffix)
                        if st.checkbox(
                            label, value=True, key=f"pack_out_{variant.suffix}"
                        ):
                            selected.append(variant.suffix)
                pack_suffixes = tuple(selected)
                st.caption(
                    "オプションを閉じたままなら全用途を出力します。"
                    "不要な用途だけ外してください。"
                )
            else:
                pack_suffixes = None

    with col_r:
        st.markdown("**このプリセット**")
        st.write(f"- 対象: **{SERVICE_LABELS[preset.service]}**")
        st.write(
            f"- pipeline: `{preset.pipeline}` / 種別: `{preset.kind}` / 出力: `{preset.output}`"
        )
        if preset.canvas:
            if preset.canvas[0] == preset.canvas[1]:
                st.write(f"- キャンバス: `{preset.canvas[0]} × {preset.canvas[1]}`（スクエア）")
            else:
                st.write(
                    f"- キャンバス（短辺×長辺）: `{preset.canvas[0]} × {preset.canvas[1]}`"
                )
        elif preset.pipeline == "pack":
            with st.expander("出力バリアント", expanded=False):
                labels = " / ".join(v.suffix for v in preset.variants)
                st.write(f"**{labels}**")
                st.caption("左の「オプション」内のパック出力で用途を選べます。")
        elif preset.id == "both_safe":
            st.write("- キャンバス: なし（比率維持・RGB JPEG・長辺≤6144・≤10MB）")
        if preset.id == "nw_square":
            st.caption("スクエア／シール紙は対応機のみ。店舗により利用できない場合があります。")
        if preset.id == "both_hagaki":
            st.caption("はがきは対応機・備え付けはがき用紙のみ。登録時にはがきとして選んでください。")
        if preset.pipeline in {"pdf", "images_to_pdf"} or preset.kind == "pdf":
            st.caption(PDF_COMPAT_HONEST)
        targets = list(preset.targets)
        if targets:
            st.markdown("**想定する印刷向き先**")
            for t in targets:
                st.write(f"- {t}")
        with st.expander("対応入力", expanded=False):
            st.write("JPEG / PNG / WebP / HEIC / TIFF / BMP / GIF / PDF")

    st.caption(
        f"入力上限: 最大 {MAX_INPUT_FILES} ファイル / "
        f"合計 {MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB"
        f"（1ファイルのアップロード上限も同 {MAX_INPUT_TOTAL_BYTES // 1024 // 1024}MB）"
    )
    uploads = st.file_uploader(
        "ファイルを選択（複数可）",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
            "heic",
            "heif",
            "tif",
            "tiff",
            "bmp",
            "gif",
            "pdf",
        ],
        accept_multiple_files=True,
    )

    url_help = (
        f"一般公開の http/https のみ。最大 {MAX_URLS_PER_REQUEST} URL。"
        "認証付き・ローカル／社内アドレスは不可。"
        f"1URLあたり最大 {MAX_DOWNLOAD_BYTES // 1024 // 1024}MB。"
    )
    if not ALLOW_URL_FETCH:
        url_help = "現在 URL 取得はサーバー設定で無効化されています。"

    url_text = st.text_area(
        "公開 URL（改行またはカンマ区切り・複数可）",
        height=100,
        placeholder="https://example.com/photo.jpg",
        help=url_help,
        disabled=not ALLOW_URL_FETCH,
    )

    # 変換前チェック（アップロード分のみ・URL は変換時に取得）
    if uploads:
        with st.expander("変換前チェック（アップロードファイル）", expanded=True):
            pre_inputs = [InputFile(name=u.name, data=u.getvalue()) for u in uploads]
            probes = probe_inputs(pre_inputs)
            rows = [
                {
                    "ファイル": p.name,
                    "種別": p.kind,
                    "形式": p.format_hint or "—",
                    "容量": p.size_label,
                    "寸法": p.dim_label,
                    "出力名(予定)": p.sanitized_stem,
                    "注意": " / ".join(p.notes) if p.notes else "—",
                }
                for p in probes
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(
                "ファイル名は日本語・多くの記号を維持します。"
                "パスに使えない文字（\\ / : * ? \" < > |）だけ _ に置換し、絵文字は除去します。"
            )
            st.caption(SEVEN_FILENAME_CAUTION)

    has_input = bool(uploads) or bool(url_text.strip())
    if st.button("変換する", type="primary", disabled=not has_input):
        inputs, fetch_errors = _collect_inputs(uploads, url_text)

        if not inputs and fetch_errors:
            for src, msg in fetch_errors:
                st.error(f"**{src}**: {msg}")
            st.stop()

        if not inputs:
            st.warning("変換するファイルがありません。")
            st.stop()

        source_thumbs = {
            f.name: preview_bytes_for_artifact(
                f.data,
                "image/jpeg"
                if Path(f.name).suffix.lower() in IMAGE_EXTENSIONS
                else "application/pdf",
            )
            for f in inputs
        }

        with st.spinner("変換中..."):
            try:
                batch = process_files(
                    inputs,
                    preset=preset,
                    options=ProcessOptions(
                        fit_mode=fit_mode,  # type: ignore[arg-type]
                        bg=_bg_from_hex(bg_hex),
                        rasterize_pdf=rasterize_pdf,
                        split_pdf=split_pdf,
                        pages_per_file=int(pages_per_file),
                        pack_variant_suffixes=pack_suffixes,
                        safe_inset=safe_inset,
                    ),
                )
            except ResourceLimitError as exc:
                get_logger().warning("リソース上限: %s", exc)
                st.error(str(exc))
                st.stop()
            except Exception as exc:  # noqa: BLE001
                log_exception(
                    "変換処理で予期しない例外",
                    exc,
                    extra={"preset": preset.id, "input_count": len(inputs)},
                )
                st.error(f"変換中に予期しないエラーが発生しました: {exc}")
                st.stop()
        batch.extend_errors(fetch_errors)
        get_logger().info(
            "変換完了 preset=%s inputs=%s outputs=%s errors=%s skipped=%s",
            preset.id,
            len(inputs),
            len(batch.outputs),
            len(batch.errors),
            len(batch.skipped),
        )
        _store_batch(batch, source_thumbs)
        st.session_state["show_safe_guide"] = show_safe_guide

    batch: BatchResult | None = st.session_state.get(_SESSION_BATCH)
    if not batch:
        return

    thumbs: list[bytes | None] = st.session_state.get(_SESSION_THUMBS) or []
    if len(thumbs) != len(batch.outputs):
        thumbs = [preview_bytes_for_artifact(o.data, o.mime) for o in batch.outputs]
        st.session_state[_SESSION_THUMBS] = thumbs
    source_thumbs_map: dict[str, bytes | None] = (
        st.session_state.get(_SESSION_SOURCE_THUMBS) or {}
    )
    guide_on = bool(st.session_state.get("show_safe_guide", True))

    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.subheader("変換結果")
        st.write(
            f"成功 **{len(batch.outputs)}** 件 ／ "
            f"失敗 **{len(batch.errors)}** 件 ／ "
            f"スキップ **{len(batch.skipped)}** 件"
        )
    with head_r:
        if st.button("結果をクリア", use_container_width=True):
            _clear_results()
            st.rerun()

    for source, message in batch.errors:
        st.error(f"**{source}**: {message}")
    for name in batch.skipped:
        st.info(f"スキップ: {name}")

    if not batch.outputs:
        return

    zip_only = bool(st.session_state.get(_SESSION_ZIP_ONLY))
    st.caption("プレビューは縮小表示です。ダウンロードはフル解像度です。")
    if zip_only:
        st.warning(
            f"結果がセッション上限（最大 {MAX_SESSION_OUTPUTS} 件 / "
            f"{MAX_SESSION_RESULT_BYTES // 1024 // 1024}MB）を超えたため、"
            "本体は ZIP のみ保持しています（同時多数セッション時のメモリ対策）。"
        )
        zip_data = st.session_state.get(_SESSION_ZIP) or b""
        st.download_button(
            "成功分を ZIP ダウンロード",
            data=zip_data,
            file_name="konbini_print_converted.zip",
            mime="application/zip",
        )
    else:
        st.download_button(
            "成功分を ZIP ダウンロード",
            data=zip_artifacts(batch.outputs),
            file_name="konbini_print_converted.zip",
            mime="application/zip",
        )

    for i, item in enumerate(batch.outputs):
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                thumb = thumbs[i] if i < len(thumbs) else None
                src_thumb = source_thumbs_map.get(item.source_name)
                if item.is_image and (thumb or src_thumb):
                    if src_thumb and thumb:
                        b1, b2 = st.columns(2)
                        with b1:
                            st.caption("変換前")
                            st.image(src_thumb, use_container_width=True)
                        with b2:
                            st.caption("変換後")
                            shown = thumb
                            if guide_on and shown:
                                try:
                                    shown = add_safe_area_guide(shown)
                                except Exception:  # noqa: BLE001
                                    pass
                            st.image(shown, use_container_width=True)
                    elif thumb:
                        shown = thumb
                        if guide_on:
                            try:
                                shown = add_safe_area_guide(shown)
                            except Exception:  # noqa: BLE001
                                pass
                        st.image(shown, caption=item.name, use_container_width=True)
                    st.caption(item.name)
                elif item.is_image:
                    st.caption("（プレビュー生成不可）")
                    st.caption(item.name)
                else:
                    st.write("📄 PDF")
                    st.caption(item.name)
            with c2:
                st.write(f"**{item.name}**")
                if item.source_name:
                    if item.source_name != item.name:
                        st.caption(f"元ファイル: {item.source_name} → 出力名: {item.name}")
                    else:
                        st.caption(f"元ファイル: {item.source_name}")
                st.write(item.meta)
                st.write(f"サイズ: {item.size_bytes / 1024:.1f} KB")
                if item.targets:
                    st.markdown("**向き先**")
                    for t in item.targets:
                        st.write(f"- {t}")
                _render_checks(item.checks)
                for w in item.warnings:
                    st.warning(w)

                with st.expander("適合マトリクス（印刷選択肢 × OK/NG）", expanded=False):
                    if item.is_pdf:
                        cells = compatibility_matrix(
                            size_bytes=item.size_bytes,
                            page_count=item.page_count or 1,
                            is_pdf=True,
                        )
                    else:
                        cells = compatibility_matrix(
                            width=item.width or 0,
                            height=item.height or 0,
                            size_bytes=item.size_bytes,
                            is_pdf=False,
                        )
                    st.dataframe(
                        matrix_as_table_rows(cells),
                        hide_index=True,
                        use_container_width=True,
                    )

                if item.data:
                    st.download_button(
                        "ダウンロード",
                        data=item.data,
                        file_name=item.name,
                        mime=item.mime,
                        key=f"dl_{i}",
                    )
                else:
                    st.caption("個別 DL 不可（上の ZIP を利用）")


if __name__ == "__main__":
    main()
