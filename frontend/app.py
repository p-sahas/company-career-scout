"""
Company Career Scout — Main Streamlit Application.
Aggregates and analyzes public company reputation data for Sri Lankan companies.
"""

import sys
import os
import asyncio
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from frontend.sidebar import render_sidebar
from frontend.components.score_gauge import (
    render_score_gauge,
    render_source_pie_chart,
    render_sentiment_overview,
)
from frontend.components.source_tab import render_source_tab
from frontend.components.export import render_export_buttons
from core.cache import CacheManager


# --- Page Config ---
st.set_page_config(
    page_title="Company Career Scout — Sri Lanka",
    page_icon=":mag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global dark theme */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Hero section */
    .hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-top: 4px;
    }

    /* Status cards */
    .status-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }

    /* Crisis banner */
    .crisis-banner {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
        border: 1px solid #ef4444;
        border-radius: 12px;
        padding: 16px 24px;
        margin: 16px 0;
    }
    .crisis-banner h4 {
        color: #ef4444;
        margin: 0 0 8px 0;
    }
    .crisis-banner p {
        color: #fca5a5;
        margin: 4px 0;
    }

    /* Demo buttons */
    .demo-btn {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        cursor: pointer;
        margin: 4px;
        font-size: 0.85em;
        transition: all 0.2s;
    }
    .demo-btn:hover {
        background: #334155;
        border-color: #3b82f6;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Sidebar ---
sidebar_config = render_sidebar()
model_router = sidebar_config["model_router"]


# --- Main Content ---
st.markdown(
    '<h1 class="hero-title">Company Career Scout</h1>'
    '<p class="hero-subtitle">'
    "AI-powered company reputation analysis — exclusively for Sri Lankan companies"
    "</p>",
    unsafe_allow_html=True,
)

st.divider()

# --- Search Section ---
col_search, col_btn = st.columns([4, 1])

with col_search:
    company_input = st.text_input(
        "Enter company name",
        placeholder="e.g. WSO2, Axiata Digital Labs, PickMe...",
        label_visibility="collapsed",
        key="company_input",
    )

with col_btn:
    scout_clicked = st.button(
        ":mag: Scout",
        type="primary",
        use_container_width=True,
        disabled=model_router is None,
    )

# Demo company quick-select
st.markdown("**Quick select a demo company:**")

# Load demo companies
demo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "demo_companies.json",
)
try:
    with open(demo_path, "r") as f:
        demo_companies = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    demo_companies = []

# Render demo buttons in columns
demo_cols = st.columns(5)
demo_selected = None
for i, demo in enumerate(demo_companies):
    with demo_cols[i % 5]:
        if st.button(demo["name"], key=f"demo_{i}", use_container_width=True):
            demo_selected = demo["name"]

# Persist active search in session state to handle Streamlit re-runs
if scout_clicked and company_input:
    st.session_state["active_company"] = company_input
elif demo_selected:
    st.session_state["active_company"] = demo_selected

search_company = st.session_state.get("active_company")


# --- Run Pipeline ---
if search_company:
    if model_router is None:
        st.error(":warning: Please enter an API key in the sidebar to proceed.")
    else:
        st.divider()
        st.markdown(f"### :mag: Scouting **{search_company}** ...")

        # Check for cached analysis first
        cache_mgr = CacheManager()
        cached_report = cache_mgr.get_analysis(search_company)

        if cached_report:
            st.info(":file_cabinet: **Using cached results.** Click 'Clear Cache' in the sidebar to refresh.")
            report = cached_report
        else:
            # Run the full pipeline
            progress = st.progress(0, text="Initializing...")

            try:
                from agents.orchestrator import run_scout

                # Run with progress updates
                progress.progress(10, text="Validating input...")

                # Fix Windows asyncio loop policy for Playwright subprocesses
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

                # Use asyncio to run the async pipeline
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                progress.progress(20, text="Crawling sources (this may take a minute)...")

                report = loop.run_until_complete(
                    run_scout(
                        company_name=search_company,
                        model_router=model_router,
                        cache_manager=cache_mgr,
                    )
                )
                loop.close()

                progress.progress(100, text="Complete!")

                # Update session state with usage
                usage = model_router.get_usage_stats()
                st.session_state["total_tokens"] = usage["total_tokens"]
                st.session_state["total_calls"] = usage["total_calls"]

            except Exception as e:
                st.error(f":x: Pipeline error: {e}")
                st.exception(e)
                report = None

        # --- Display Results ---
        if report and isinstance(report, dict) and report.get("company"):
            # Store report in session state
            st.session_state["current_report"] = report
            st.session_state["analyzed_results"] = report.get("analyzed_results", [])

            by_source = report.get("by_source", {})
            summary = report.get("aggregated_summary", {})

            # --- Tabs ---
            tab_names = ["Overview"]
            source_tab_mapping = {
                "reddit": "Reddit",
                "google_maps": "Google Maps",
                "glassdoor": "Glassdoor",
                "topjobs_ikman": "SL Job Boards",
                "linkedin": "LinkedIn",
                "facebook": "Facebook",
                "sl_news": "SL News",
                "web_general": "Web",
            }

            for key, label in source_tab_mapping.items():
                if key in by_source:
                    tab_names.append(label)

            tab_names.append("Raw Data")
            tabs = st.tabs(tab_names)

            # --- Overview Tab ---
            with tabs[0]:
                # Score gauge
                col1, col2 = st.columns([1, 1])
                with col1:
                    render_score_gauge(report.get("overall_score", 50))
                with col2:
                    render_source_pie_chart(by_source)

                # Crisis flags
                crisis_flags = summary.get("crisis_flags", [])
                if crisis_flags:
                    crisis_html = "".join(
                        f"<p>⚠️ {flag}</p>" for flag in crisis_flags
                    )
                    st.markdown(
                        f'<div class="crisis-banner">'
                        f"<h4>🚨 Crisis Flags Detected</h4>"
                        f"{crisis_html}</div>",
                        unsafe_allow_html=True,
                    )

                # Side-by-side views
                st.markdown("---")
                view_cols = st.columns(3)

                with view_cols[0]:
                    st.markdown("#### 👤 Employee View")
                    st.markdown(summary.get("what_employees_say", "No data."))

                with view_cols[1]:
                    st.markdown("#### 🛒 Customer View")
                    st.markdown(summary.get("what_customers_say", "No data."))

                with view_cols[2]:
                    st.markdown("#### 📰 Press View")
                    st.markdown(summary.get("what_press_says", "No data."))

                # Pros & Cons
                st.markdown("---")
                pros_col, cons_col = st.columns(2)

                with pros_col:
                    st.markdown("#### ✅ Top Pros")
                    for pro in summary.get("top_5_pros", ["No data available"]):
                        st.markdown(f"- {pro}")

                with cons_col:
                    st.markdown("#### ❌ Top Cons")
                    for con in summary.get("top_5_cons", ["No data available"]):
                        st.markdown(f"- {con}")

                # Recommendation
                st.markdown("---")
                st.markdown("#### :bulb: Recommendation")
                st.info(summary.get("recommendation", "No recommendation available."))

                # Export
                st.markdown("---")
                analyzed = st.session_state.get("analyzed_results", [])
                render_export_buttons(report, analyzed)

            # --- Source Tabs ---
            tab_idx = 1
            for source_key, label in source_tab_mapping.items():
                if source_key in by_source:
                    with tabs[tab_idx]:
                        source_data = by_source[source_key]
                        # Filter analyzed results for this source
                        source_results = [
                            r
                            for r in st.session_state.get("analyzed_results", [])
                            if r.get("source_platform") == source_key.split("_")[0]
                        ]
                        render_source_tab(source_key, source_data, source_results)
                    tab_idx += 1

            # --- Raw Data Tab ---
            with tabs[-1]:
                st.markdown("### :page_facing_up: Raw Report Data")
                st.json(report)

                # Model info
                st.markdown("---")
                st.markdown(f"**Model used:** {report.get('model_used', 'N/A')}")
                st.markdown(f"**Generated at:** {report.get('generated_at', 'N/A')}")
                st.markdown(f"**Total results:** {report.get('total_results', 0)}")

                # Cache info
                cache_hits = report.get("cache_hits", {})
                if cache_hits:
                    st.markdown("**Cache hits:**")
                    for source, hit in cache_hits.items():
                        icon = ":white_check_mark:" if hit else ":x:"
                        st.markdown(f"- {source}: {icon}")

elif not search_company:
    # Landing state
    st.markdown("---")

    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            """
            <div class="status-card">
                <h3>🌍 Sri Lanka Focused</h3>
                <p style="color: #94a3b8;">Every search is geo-scoped to Sri Lanka.
                Only verified SL data makes it to your report.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            """
            <div class="status-card">
                <h3>🤖 Multi-Source AI</h3>
                <p style="color: #94a3b8;">Crawls Reddit, Google Maps, Glassdoor,
                LinkedIn, Facebook, SL news, and more.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.markdown(
            """
            <div class="status-card">
                <h3>⚡ Cost Effective</h3>
                <p style="color: #94a3b8;">Uses free-tier LLMs by default (Groq, Gemini).
                Results cached for 48 hours.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #475569;">'
        "Enter a company name above or select a demo company to get started."
        "</p>",
        unsafe_allow_html=True,
    )
