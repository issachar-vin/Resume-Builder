from __future__ import annotations

import logging

import streamlit as st

from GUI.app_context import TailoringAppContext

logger = logging.getLogger(__name__)


def render_cache_manager_page(app: TailoringAppContext) -> None:
    st.title("Cache Manager")

    st.subheader("resume.md")
    st.text_area(
        "Current resume.md",
        app.cache_manager.read_resume_markdown(),
        height=260,
        disabled=True,
    )

    st.divider()
    st.subheader("Job Caches")
    entries = app.cache_manager.list_job_caches()
    if not entries:
        st.info("No cached jobs yet.")
    else:
        for entry in entries:
            with st.container(border=True):
                st.write(f"**Hash:** {entry.hash}")
                st.write(f"**URL:** {entry.url}")
                st.write(f"**Source:** {entry.source} (url = HTTP fetch, manual = pasted text)")
                st.write(f"**Company / Title:** {entry.summary.company} / {entry.summary.title}")
                st.write(f"**Cached at:** {entry.cached_at}")
                if st.button(f"Delete {entry.hash}", key=f"del_{entry.hash}"):
                    deleted = app.cache_manager.delete_job_cache(entry.hash)
                    logger.info("Delete job cache hash=%s ok=%s", entry.hash, deleted)
                    st.success("Deleted." if deleted else "Not found.")
                    st.rerun()

    st.divider()
    st.subheader("Token Usage")
    usage_logs = app.cache_manager.load_usage_logs()
    if usage_logs:
        total_input = sum(item.input_tokens for item in usage_logs)
        total_output = sum(item.output_tokens for item in usage_logs)
        total_cache_read = sum(item.cache_read_input_tokens for item in usage_logs)
        total_cache_create = sum(item.cache_creation_input_tokens for item in usage_logs)
        st.metric("Input Tokens", total_input)
        st.metric("Output Tokens", total_output)
        st.metric("Cache Read Tokens Saved", total_cache_read)
        st.metric("Cache Creation Tokens", total_cache_create)

        st.markdown("### Recent Requests")
        for item in sorted(usage_logs, key=lambda x: x.timestamp, reverse=True)[:20]:
            cr, cc = item.cache_read_input_tokens, item.cache_creation_input_tokens
            st.write(
                f"{item.timestamp} | {item.company or 'Unknown'} | hash={item.job_hash} | "
                f"in={item.input_tokens}, out={item.output_tokens}, cache_read={cr}, "
                f"cache_create={cc}"
            )
    else:
        st.info("No usage logs yet.")
