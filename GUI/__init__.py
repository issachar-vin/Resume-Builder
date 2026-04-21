"""Streamlit UI package for the resume tailoring app."""

# pylint: disable=invalid-name
# The import package directory is ``GUI`` (not ``gui``) to mirror common UI naming.

from GUI.main import ResumeTailoringApp, run_app

__all__ = ["ResumeTailoringApp", "run_app"]
