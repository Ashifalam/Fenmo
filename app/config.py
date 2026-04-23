import os


def get_database_url() -> str:
    """Resolve DATABASE_URL from Streamlit secrets, env var, or fallback to SQLite."""
    # 1. Try Streamlit secrets (for Streamlit Cloud deployment)
    try:
        import streamlit as st

        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass

    # 2. Try environment variable
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # 3. Fallback to SQLite for local dev
    return "sqlite:///./femo.db"
