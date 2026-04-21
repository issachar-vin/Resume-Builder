from __future__ import annotations

import difflib
import logging
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import streamlit as st

from GUI.app_context import TailoringAppContext
from GUI.session_keys import SessionKeys
from models.job import JobCacheEntry
from services.cache_manager import CacheManager, TailoredHistoryItem

logger = logging.getLogger(__name__)


def _tailored_history_label(item: TailoredHistoryItem) -> str:
    return f"{item.company} — {item.title} · {item.updated_at:%Y-%m-%d %H:%M} UTC"


def latest_output_tex_path(cache_manager: CacheManager, entry: JobCacheEntry) -> Path:
    company_slug = cache_manager.safe_slug(entry.summary.company or "company")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return cache_manager.output_dir / f"{company_slug}_{stamp}.tex"


def _pop_job_posting_notices() -> None:
    """Show one-shot messages from fetch/history (after rerun)."""
    if SessionKeys.NOTICE_JOB_SUMMARY in st.session_state:
        kind, text = st.session_state.pop(SessionKeys.NOTICE_JOB_SUMMARY)
        if kind == "info":
            st.info(text)
        else:
            st.success(text)
    if SessionKeys.NOTICE_TAILORED_LOADED in st.session_state:
        st.success(st.session_state.pop(SessionKeys.NOTICE_TAILORED_LOADED))
    if SessionKeys.NOTICE_HISTORY_LOADED in st.session_state:
        st.success(st.session_state.pop(SessionKeys.NOTICE_HISTORY_LOADED))


def render_tailor_page(app: TailoringAppContext) -> None:
    st.title("Tailor Resume")
    st.write(
        "Fetch a job posting, run Claude tailoring, edit the markdown, then generate LaTeX and PDF."
    )

    st.subheader("Resume Source")
    if app.cache_manager.resume_exists():
        st.success("Using cache/resume.md as source of truth.")
    else:
        tex_file = st.file_uploader("Upload resume .tex (first run only)", type=["tex"])
        if tex_file and st.button("Parse .tex to resume.md", type="primary"):
            try:
                content = tex_file.read().decode("utf-8", errors="ignore")
                logger.info(
                    "[LaTeX UI] Parse button: uploaded file %r, %s chars — calling parser",
                    getattr(tex_file, "name", "upload"),
                    len(content),
                )
                parsed_md = app.latex_parser.get_or_create_resume_markdown(content)
                st.session_state[SessionKeys.RESUME_EDITOR_VALUE] = parsed_md
                st.success("Created cache/resume.md")
            except Exception as exc:
                logger.exception("LaTeX parse failed")
                st.error(str(exc))

    st.divider()
    st.subheader("Job Posting")
    pending_url = st.session_state.pop(SessionKeys.JOB_URL_PENDING, None)
    if pending_url is not None:
        st.session_state[SessionKeys.JOB_POSTING_URL] = pending_url
    _pop_job_posting_notices()

    st.text_input("Job posting URL", placeholder="https://...", key=SessionKeys.JOB_POSTING_URL)

    url_for_fetch = (st.session_state.get(SessionKeys.JOB_POSTING_URL) or "").strip()
    if st.button("Fetch / Summarize Job", disabled=not bool(url_for_fetch)):
        try:
            logger.info("Fetch job: url=%s", url_for_fetch)
            fetched_entry, from_cache = app.job_scraper.get_job_data(url_for_fetch)
            st.session_state[SessionKeys.JOB_ENTRY] = fetched_entry
            cached_tailored = app.cache_manager.load_tailored_markdown(fetched_entry.hash)
            if cached_tailored is not None:
                st.session_state[SessionKeys.TAILORED_MARKDOWN] = cached_tailored
                st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = ""
                st.session_state[SessionKeys.NOTICE_TAILORED_LOADED] = (
                    "Loaded saved tailored markdown from disk for this posting."
                )
            else:
                st.session_state[SessionKeys.TAILORED_MARKDOWN] = ""
                st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = ""
            if from_cache:
                st.session_state[SessionKeys.NOTICE_JOB_SUMMARY] = (
                    "info",
                    f"Loaded cached job summary ({fetched_entry.hash}).",
                )
            else:
                st.session_state[SessionKeys.NOTICE_JOB_SUMMARY] = (
                    "success",
                    f"Fetched and cached job summary ({fetched_entry.hash}).",
                )
            st.session_state[SessionKeys.JOB_URL_PENDING] = fetched_entry.url
            st.rerun()
        except Exception as exc:
            logger.exception("Job fetch/summarize failed")
            st.error(str(exc))

    job_entry: JobCacheEntry | None = st.session_state.get(SessionKeys.JOB_ENTRY)
    if job_entry:
        st.markdown("### Job Summary")
        st.json(job_entry.model_dump(mode="json"))

    tailored_hist = app.cache_manager.list_tailored_history()
    if tailored_hist:
        st.markdown("#### Past tailored postings")
        labels = {h.job_hash: _tailored_history_label(h) for h in tailored_hist}
        st.selectbox(
            "Select a posting",
            options=[h.job_hash for h in tailored_hist],
            format_func=lambda jh: labels[jh],
            key=SessionKeys.TAILOR_HISTORY_PICK,
        )
        if st.button("Load selected posting & tailored markdown"):
            pick = st.session_state.get(SessionKeys.TAILOR_HISTORY_PICK)
            if isinstance(pick, str) and pick:
                loaded = app.cache_manager.load_job_by_hash(pick)
                if loaded:
                    st.session_state[SessionKeys.JOB_ENTRY] = loaded
                    st.session_state[SessionKeys.JOB_URL_PENDING] = loaded.url
                md = app.cache_manager.load_tailored_markdown(pick)
                st.session_state[SessionKeys.TAILORED_MARKDOWN] = md or ""
                st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = ""
                st.session_state[SessionKeys.NOTICE_HISTORY_LOADED] = (
                    "Loaded posting and tailored markdown."
                )
                st.rerun()

    st.divider()
    st.subheader("Tailor with Claude")
    can_tailor = app.cache_manager.resume_exists() and job_entry is not None
    tailor_busy = bool(st.session_state.get(SessionKeys.TAILOR_BUSY))

    if st.button(
        "Tailor Resume with Claude",
        type="primary",
        disabled=not can_tailor or tailor_busy,
        key="tailor_resume_claude",
    ):
        st.session_state[SessionKeys.TAILOR_BUSY] = True
        st.rerun()

    loading_slot = st.empty()
    if tailor_busy and can_tailor:
        with loading_slot:
            with st.spinner("Tailoring with Claude…"):
                try:
                    resume_md = app.cache_manager.read_resume_markdown()
                    entry = job_entry
                    if entry is None:
                        st.warning(
                            'No job loaded. Click "Fetch / Summarize Job" first, then tailor again.'
                        )
                    else:
                        logger.info(
                            "Tailor with Claude: job_hash=%s company=%s",
                            entry.hash,
                            entry.summary.company,
                        )
                        tailored_md, usage = app.resume_writer.tailor_with_claude(
                            resume_markdown=resume_md,
                            job_data=entry.summary,
                            job_hash=entry.hash,
                        )
                        st.session_state[SessionKeys.TAILORED_MARKDOWN] = tailored_md
                        st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = ""
                        st.success(
                            "Tailored markdown saved. Review below, then generate LaTeX/PDF."
                        )
                        st.caption(
                            f"Tokens - input: {usage.input_tokens}, output: {usage.output_tokens}, "
                            f"cache read: {usage.cache_read_input_tokens}, "
                            f"cache create: {usage.cache_creation_input_tokens}"
                        )
                except anthropic.BadRequestError as exc:
                    logger.exception("Tailor resume failed")
                    detail = str(exc).lower()
                    if "credit" in detail and "balance" in detail:
                        st.error(
                            "Anthropic API: credit balance is too low for this key. Open "
                            "[Anthropic billing](https://console.anthropic.com/settings/plans) "
                            "to add credits or upgrade, then retry."
                        )
                    else:
                        st.error(str(exc))
                except Exception as exc:
                    logger.exception("Tailor resume failed")
                    st.error(str(exc))
                finally:
                    st.session_state[SessionKeys.TAILOR_BUSY] = False
    elif tailor_busy and not can_tailor:
        st.session_state[SessionKeys.TAILOR_BUSY] = False

    if job_entry:
        st.markdown("#### Review & edit tailored markdown")
        st.caption("Changes here are written to disk when you click **Generate LaTeX & PDF**.")
        st.text_area(
            "Tailored resume",
            height=400,
            key=SessionKeys.TAILORED_MARKDOWN,
            label_visibility="collapsed",
        )

        can_export = bool((st.session_state.get(SessionKeys.TAILORED_MARKDOWN) or "").strip())
        if st.button(
            "Generate LaTeX & PDF",
            type="secondary",
            disabled=not can_export,
            key="generate_tex_pdf",
        ):
            with st.spinner("Generating LaTeX and PDF…"):
                try:
                    output_path = app.resume_writer.build_tex_and_pdf(
                        st.session_state[SessionKeys.TAILORED_MARKDOWN],
                        job_entry.summary,
                        job_entry.hash,
                    )
                    st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = str(output_path)
                    st.success(f"Wrote {output_path.name} (and PDF if `pdflatex` is available).")
                except Exception as exc:
                    logger.exception("Generate LaTeX/PDF failed")
                    st.error(str(exc))

    if (st.session_state.get(SessionKeys.TAILORED_MARKDOWN) or "").strip():
        resume_snapshot = app.cache_manager.read_resume_markdown()
        before = resume_snapshot.splitlines()
        after = (st.session_state[SessionKeys.TAILORED_MARKDOWN] or "").splitlines()
        diff = "\n".join(
            difflib.unified_diff(
                before, after, fromfile="resume.md", tofile="tailored.md", lineterm=""
            )
        )

        with st.expander("Compare to original (read-only)"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Original")
                st.text_area(
                    "Original",
                    resume_snapshot,
                    height=320,
                    disabled=True,
                    label_visibility="collapsed",
                    key="tailor_compare_orig",
                )
            with col2:
                st.markdown("##### Tailored (current editor)")
                st.text_area(
                    "Tailored snapshot",
                    st.session_state[SessionKeys.TAILORED_MARKDOWN],
                    height=320,
                    disabled=True,
                    label_visibility="collapsed",
                    key="tailor_compare_tail",
                )
            st.code(diff or "No textual differences detected.", language="diff")

        dl_job = st.session_state.get(SessionKeys.JOB_ENTRY)
        if isinstance(dl_job, JobCacheEntry):
            last_tex = (st.session_state.get(SessionKeys.LAST_TAILORED_TEX_PATH) or "").strip()
            if last_tex:
                latest_tex = Path(last_tex)
                if not latest_tex.exists():
                    latest_tex = latest_output_tex_path(app.cache_manager, dl_job)
            else:
                latest_tex = latest_output_tex_path(app.cache_manager, dl_job)
            if latest_tex.exists():
                st.download_button(
                    "Download Tailored .tex",
                    data=latest_tex.read_text(encoding="utf-8"),
                    file_name=latest_tex.name,
                    mime="text/x-tex",
                    key="download_tailored_tex",
                )
                pdf_path = latest_tex.with_suffix(".pdf")
                if pdf_path.is_file():
                    st.download_button(
                        "Download Tailored PDF",
                        data=pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key="download_tailored_pdf",
                    )
                else:
                    st.caption(
                        "No PDF yet — put `pdflatex` on your PATH (e.g. MacTeX) or run "
                        "`make build` on the saved `.tex`."
                    )
