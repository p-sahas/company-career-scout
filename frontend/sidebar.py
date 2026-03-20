"""
Sidebar component — Model selector, API key management, and usage stats.
Auto-loads API keys from .env file; allows override via frontend inputs.
"""

import streamlit as st
from config.settings import (
    DEFAULT_MODELS,
    FREE_TIER_PROVIDERS,
    MODEL_DISPLAY_NAMES,
    API_KEY_UI,
    get_api_key,
)
from core.model_router import ModelRouter


def _init_api_keys():
    """
    Initialize API keys in session_state from .env on first load.
    Keys entered via the frontend will override .env values.
    """
    if "api_keys_initialized" not in st.session_state:
        # Load from .env via config.settings.get_api_key()
        env_keys = {
            "groq_key": get_api_key("groq"),
            "google_key": get_api_key("google"),
            "anthropic_key": get_api_key("anthropic"),
            "openai_key": get_api_key("openai"),
            "tavily_key": get_api_key("tavily"),
            "serpapi_key": get_api_key("serpapi"),
        }
        for key_name, value in env_keys.items():
            if value and key_name not in st.session_state:
                st.session_state[key_name] = value

        st.session_state["api_keys_initialized"] = True


def render_sidebar() -> dict:
    """
    Render the sidebar with AI Model Settings and API keys.
    Keys found in .env are pre-filled; users can override via the UI.

    Returns:
        Dict with 'model_router' (ModelRouter or None) and settings info.
    """
    # Auto-load .env keys on first run
    _init_api_keys()

    with st.sidebar:
        st.markdown("## :gear: AI Model Settings")
        st.divider()

        # Model selector
        provider_order = ["groq", "google", "anthropic", "openai"]
        display_names = [MODEL_DISPLAY_NAMES[p] for p in provider_order]

        model_choice = st.selectbox(
            "Select AI Model",
            options=display_names,
            index=0,
            help="Choose the LLM provider. Groq and Gemini are free.",
        )

        # Reverse-map display name → provider key
        selected_idx = display_names.index(model_choice)
        provider = provider_order[selected_idx]
        model_name = DEFAULT_MODELS[provider]

        # Display current model
        is_free = provider in FREE_TIER_PROVIDERS
        tier_badge = ":white_check_mark: Free Tier" if is_free else ":credit_card: Paid"
        st.info(f"**Currently using:** {model_choice}\n\n{tier_badge}")

        st.divider()
        st.markdown("### :key: API Keys")

        # Show a hint about .env auto-loading
        st.caption(":file_folder: Keys from `.env` are auto-loaded. Override below if needed.")

        # ── LLM Provider Keys ──
        st.markdown("**LLM Providers**")

        groq_key = st.text_input(
            API_KEY_UI["groq"]["label"],
            type="password",
            value=st.session_state.get("groq_key", ""),
            key="groq_key_input",
            help=API_KEY_UI["groq"]["help"],
        )
        if groq_key:
            st.session_state["groq_key"] = groq_key

        google_key = st.text_input(
            API_KEY_UI["google"]["label"],
            type="password",
            value=st.session_state.get("google_key", ""),
            key="google_key_input",
            help=API_KEY_UI["google"]["help"],
        )
        if google_key:
            st.session_state["google_key"] = google_key

        anthropic_key = st.text_input(
            API_KEY_UI["anthropic"]["label"],
            type="password",
            value=st.session_state.get("anthropic_key", ""),
            key="anthropic_key_input",
            help=API_KEY_UI["anthropic"]["help"],
        )
        if anthropic_key:
            st.session_state["anthropic_key"] = anthropic_key

        openai_key = st.text_input(
            API_KEY_UI["openai"]["label"],
            type="password",
            value=st.session_state.get("openai_key", ""),
            key="openai_key_input",
            help=API_KEY_UI["openai"]["help"],
        )
        if openai_key:
            st.session_state["openai_key"] = openai_key

        # ── Search & Tool Keys ──
        st.markdown("**Search APIs**")

        tavily_key = st.text_input(
            API_KEY_UI["tavily"]["label"],
            type="password",
            value=st.session_state.get("tavily_key", ""),
            key="tavily_key_input",
            help=API_KEY_UI["tavily"]["help"],
        )
        if tavily_key:
            st.session_state["tavily_key"] = tavily_key
            # Also set in os.environ so crawlers can pick it up
            import os
            os.environ["TAVILY_API_KEY"] = tavily_key

        serpapi_key = st.text_input(
            API_KEY_UI["serpapi"]["label"],
            type="password",
            value=st.session_state.get("serpapi_key", ""),
            key="serpapi_key_input",
            help=API_KEY_UI["serpapi"]["help"],
        )
        if serpapi_key:
            st.session_state["serpapi_key"] = serpapi_key
            import os
            os.environ["SERPAPI_KEY"] = serpapi_key

        # Get the appropriate key for selected LLM provider
        key_mapping = {
            "groq": st.session_state.get("groq_key", ""),
            "google": st.session_state.get("google_key", ""),
            "anthropic": st.session_state.get("anthropic_key", ""),
            "openai": st.session_state.get("openai_key", ""),
        }

        api_key = key_mapping.get(provider, "")

        # Show which keys are configured
        st.divider()
        st.markdown("### :shield: Key Status")
        all_keys = {
            "Groq": st.session_state.get("groq_key", ""),
            "Google": st.session_state.get("google_key", ""),
            "Anthropic": st.session_state.get("anthropic_key", ""),
            "OpenAI": st.session_state.get("openai_key", ""),
            "Tavily": st.session_state.get("tavily_key", ""),
            "SerpAPI": st.session_state.get("serpapi_key", ""),
        }
        for name, key in all_keys.items():
            icon = ":white_check_mark:" if key else ":x:"
            st.caption(f"{icon} {name}")

        # Build ModelRouter if key is available
        model_router = None
        if api_key:
            try:
                model_router = ModelRouter(
                    provider=provider,
                    api_key=api_key,
                    model_name=model_name,
                )
                st.success(f":white_check_mark: {provider.title()} configured")
            except Exception as e:
                st.error(f"Error initializing model: {e}")
        else:
            st.warning(
                f":warning: Enter your {provider.title()} API key to proceed."
            )

        # Usage stats
        st.divider()
        st.markdown("### :bar_chart: Usage")

        if "total_tokens" not in st.session_state:
            st.session_state["total_tokens"] = 0
        if "total_calls" not in st.session_state:
            st.session_state["total_calls"] = 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tokens Used", f"{st.session_state['total_tokens']:,}")
        with col2:
            st.metric("LLM Calls", st.session_state["total_calls"])

        if is_free:
            st.caption(":sparkles: Free tier — no cost for this run")

        # Cache controls
        st.divider()
        st.markdown("### :file_cabinet: Cache")

        if st.button(":wastebasket: Clear Cache", use_container_width=True):
            from core.cache import CacheManager
            cm = CacheManager()
            cm.clear_all()
            st.success("Cache cleared!")

    return {
        "model_router": model_router,
        "provider": provider,
        "model_name": model_name,
        "is_free": is_free,
    }
