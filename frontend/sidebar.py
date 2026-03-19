"""
Sidebar component — Model selector and API key inputs.
"""

import streamlit as st
from core.model_router import ModelRouter, DEFAULT_MODELS, FREE_TIER_PROVIDERS


MODEL_OPTIONS = {
    "Groq — Llama 3.3 70B (free, default)": ("groq", DEFAULT_MODELS["groq"]),
    "Google Gemini — gemini-2.0-flash (free)": ("google", DEFAULT_MODELS["google"]),
    "Anthropic Claude — claude-haiku-4-5 (free credits)": ("anthropic", DEFAULT_MODELS["anthropic"]),
    "OpenAI — gpt-4o-mini (paid, fallback)": ("openai", DEFAULT_MODELS["openai"]),
}


def render_sidebar() -> dict:
    """
    Render the sidebar with AI Model Settings.

    Returns:
        Dict with 'model_router' (ModelRouter or None) and settings info.
    """
    with st.sidebar:
        st.markdown("## :gear: AI Model Settings")
        st.divider()

        # Model selector
        model_choice = st.selectbox(
            "Select AI Model",
            options=list(MODEL_OPTIONS.keys()),
            index=0,
            help="Choose the LLM provider. Groq and Gemini are free.",
        )

        provider, model_name = MODEL_OPTIONS[model_choice]

        # Display current model
        is_free = provider in FREE_TIER_PROVIDERS
        tier_badge = ":white_check_mark: Free Tier" if is_free else ":credit_card: Paid"
        st.info(f"**Currently using:** {model_choice}\n\n{tier_badge}")

        st.divider()
        st.markdown("### :key: API Keys")

        # API Key inputs per provider
        groq_key = st.text_input(
            "Groq API Key",
            type="password",
            value=st.session_state.get("groq_key", ""),
            key="groq_key_input",
            help="Get free key at console.groq.com",
        )
        if groq_key:
            st.session_state["groq_key"] = groq_key

        google_key = st.text_input(
            "Google AI Studio Key",
            type="password",
            value=st.session_state.get("google_key", ""),
            key="google_key_input",
            help="Get free key at aistudio.google.com",
        )
        if google_key:
            st.session_state["google_key"] = google_key

        anthropic_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=st.session_state.get("anthropic_key", ""),
            key="anthropic_key_input",
        )
        if anthropic_key:
            st.session_state["anthropic_key"] = anthropic_key

        openai_key = st.text_input(
            "OpenAI API Key (optional)",
            type="password",
            value=st.session_state.get("openai_key", ""),
            key="openai_key_input",
        )
        if openai_key:
            st.session_state["openai_key"] = openai_key

        # Get the appropriate key for selected provider
        key_mapping = {
            "groq": st.session_state.get("groq_key", ""),
            "google": st.session_state.get("google_key", ""),
            "anthropic": st.session_state.get("anthropic_key", ""),
            "openai": st.session_state.get("openai_key", ""),
        }

        api_key = key_mapping.get(provider, "")

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
