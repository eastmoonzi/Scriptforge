"""
Streamlit Compatibility Layer
=============================
When root-level modules (director_system.py, memory_rag.py, etc.) do
``import streamlit as st``, this shim lets them run outside Streamlit
by providing a mock ``st`` object that routes UI calls to logging.
"""

import logging
import sys

_logger = logging.getLogger("scriptforge.compat")


class _MockSessionState(dict):
    """Behaves like st.session_state — a dict with attribute access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


class _MockStreamlit:
    """Drop-in replacement for the ``streamlit`` module."""

    session_state = _MockSessionState()

    # UI feedback → logging
    @staticmethod
    def error(msg, *a, **kw):
        _logger.error(msg)

    @staticmethod
    def warning(msg, *a, **kw):
        _logger.warning(msg)

    @staticmethod
    def info(msg, *a, **kw):
        _logger.info(msg)

    @staticmethod
    def success(msg, *a, **kw):
        _logger.info(msg)

    @staticmethod
    def toast(msg, *a, **kw):
        _logger.info(msg)

    @staticmethod
    def write(*a, **kw):
        _logger.info(str(a))

    @staticmethod
    def spinner(text=""):
        """Context manager that does nothing."""
        from contextlib import nullcontext
        return nullcontext()

    # Allow ``st.cache_data`` etc. as no-op decorators
    @staticmethod
    def cache_data(func=None, **kw):
        return func if func is not None else lambda f: f

    @staticmethod
    def cache_resource(func=None, **kw):
        return func if func is not None else lambda f: f


def install():
    """Inject the mock ``streamlit`` into ``sys.modules`` if not already present."""
    if "streamlit" not in sys.modules:
        sys.modules["streamlit"] = _MockStreamlit()  # type: ignore[assignment]
