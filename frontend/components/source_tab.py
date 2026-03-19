"""
Source tab component — Renders per-source result cards.
"""

import streamlit as st


SENTIMENT_COLORS = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
}

REVIEWER_BADGES = {
    "employee": (":bust_in_silhouette: Employee", "#3b82f6"),
    "customer": (":shopping_trolley: Customer", "#f59e0b"),
    "press": (":newspaper: Press", "#8b5cf6"),
    "job_seeker": (":briefcase: Job Seeker", "#06b6d4"),
    "general": (":globe_with_meridians: General", "#64748b"),
}

THEME_LABELS = {
    "salary_benefits": ":moneybag: Salary & Benefits",
    "work_life_balance": ":balance_scale: Work-Life Balance",
    "management_culture": ":office: Management Culture",
    "product_quality": ":star: Product Quality",
    "customer_service": ":headphones: Customer Service",
    "pricing": ":label: Pricing",
    "delivery": ":package: Delivery",
    "job_security": ":shield: Job Security",
    "office_environment": ":house: Office Environment",
    "career_growth": ":chart_with_upwards_trend: Career Growth",
    "ethical_practices": ":handshake: Ethical Practices",
    "layoffs_restructuring": ":warning: Layoffs/Restructuring",
}


def render_sentiment_bar(breakdown: dict) -> None:
    """Render a proportional sentiment bar."""
    total = sum(breakdown.values())
    if total == 0:
        st.caption("No sentiment data available")
        return

    pos_pct = (breakdown.get("positive", 0) / total) * 100
    neg_pct = (breakdown.get("negative", 0) / total) * 100
    neu_pct = (breakdown.get("neutral", 0) / total) * 100

    st.markdown(
        f"""
        <div style="display: flex; height: 24px; border-radius: 12px; overflow: hidden; margin: 8px 0;">
            <div style="width: {pos_pct}%; background: {SENTIMENT_COLORS['positive']};"></div>
            <div style="width: {neu_pct}%; background: {SENTIMENT_COLORS['neutral']};"></div>
            <div style="width: {neg_pct}%; background: {SENTIMENT_COLORS['negative']};"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #94a3b8;">
            <span style="color: {SENTIMENT_COLORS['positive']};">Positive: {breakdown.get('positive', 0)}</span>
            <span style="color: {SENTIMENT_COLORS['neutral']};">Neutral: {breakdown.get('neutral', 0)}</span>
            <span style="color: {SENTIMENT_COLORS['negative']};">Negative: {breakdown.get('negative', 0)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_tab(source_key: str, source_data: dict, results: list) -> None:
    """
    Render a complete source tab with sentiment bar and result cards.

    Args:
        source_key: Source identifier (e.g. "reddit", "glassdoor").
        source_data: Per-source report data from report_builder.
        results: Analyzed results for this source.
    """
    platform_name = source_data.get("platform", source_key.title())
    result_count = source_data.get("result_count", 0)

    # Header with badge
    st.markdown(
        f"### {platform_name} "
        f'<span style="background: #1e293b; color: #94a3b8; padding: 2px 10px; '
        f'border-radius: 12px; font-size: 0.7em;">{result_count} results</span>',
        unsafe_allow_html=True,
    )

    if result_count == 0:
        st.info(f"No results found from {platform_name}.")
        return

    # Sentiment bar
    sentiment = source_data.get("sentiment_breakdown", {})
    if sentiment:
        render_sentiment_bar(sentiment)

    # Source-specific extras
    _render_source_extras(source_key, source_data)

    # Sort controls
    sort_options = [
        "Most Recent",
        "Most Negative",
        "Most Positive",
        "Highest Severity",
    ]
    sort_by = st.selectbox(
        "Sort by",
        sort_options,
        key=f"sort_{source_key}",
        label_visibility="collapsed",
    )

    # Sort results
    sorted_results = _sort_results(results, sort_by)

    # Render cards
    for i, result in enumerate(sorted_results):
        _render_result_card(result, f"{source_key}_{i}")


def _render_source_extras(source_key: str, data: dict) -> None:
    """Render source-specific extra info (ratings, job counts, etc.)"""
    if source_key == "google_maps" and data.get("avg_rating"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Rating", f"{data['avg_rating']} / 5.0")
        with col2:
            st.metric("Total Reviews", data.get("review_count", "N/A"))

    elif source_key == "glassdoor":
        cols = st.columns(3)
        with cols[0]:
            st.metric("Avg Rating", data.get("avg_rating", "N/A"))
        with cols[1]:
            st.metric("Reviews", data.get("employee_count", 0))
        with cols[2]:
            roles = data.get("roles_represented", [])
            st.metric("Roles", len(roles))

        if data.get("top_pros"):
            with st.expander("Top Pros"):
                for pro in data["top_pros"]:
                    st.markdown(f"- :white_check_mark: {pro}")

        if data.get("top_cons"):
            with st.expander("Top Cons"):
                for con in data["top_cons"]:
                    st.markdown(f"- :x: {con}")

    elif source_key == "topjobs_ikman":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Jobs", data.get("active_job_count", 0))
        with col2:
            trend = data.get("hiring_trend", "unknown")
            trend_icons = {
                "growing": ":chart_with_upwards_trend:",
                "stable": ":left_right_arrow:",
                "shrinking": ":chart_with_downwards_trend:",
                "none": ":no_entry:",
            }
            st.metric("Hiring Trend", f"{trend_icons.get(trend, '')} {trend.title()}")
        with col3:
            salary = data.get("salary_range_lkr", "N/A")
            st.metric("Salary Range (LKR)", salary or "N/A")

    elif source_key == "linkedin":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Followers", data.get("followers", "N/A"))
        with col2:
            st.metric("Employees", data.get("employees", "N/A"))

    elif source_key == "facebook":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Rating", data.get("avg_rating", "N/A"))
        with col2:
            st.metric("Page Likes", data.get("page_likes", "N/A"))

    elif source_key == "sl_news":
        articles = data.get("articles", [])
        if articles:
            st.markdown("#### Recent Articles")
            for article in articles[:5]:
                sentiment = article.get("sentiment", "neutral")
                color = SENTIMENT_COLORS.get(sentiment, "#94a3b8")
                url = article.get("url", "")
                headline = article.get("headline", "Untitled")
                source = article.get("source", "Unknown")
                date = article.get("date", "")

                st.markdown(
                    f'<div style="border-left: 3px solid {color}; padding-left: 12px; margin: 8px 0;">'
                    f'<strong><a href="{url}" target="_blank">{headline}</a></strong><br>'
                    f'<small style="color: #94a3b8;">{source} • {date}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _render_result_card(result: dict, key: str) -> None:
    """Render a single result card."""
    sentiment = result.get("sentiment", "neutral")
    color = SENTIMENT_COLORS.get(sentiment, "#94a3b8")
    reviewer_type = result.get("reviewer_type", "general")
    badge_text, badge_color = REVIEWER_BADGES.get(
        reviewer_type, REVIEWER_BADGES["general"]
    )

    with st.container():
        st.markdown(
            f"""<div style="border: 1px solid #334155; border-left: 4px solid {color};
                border-radius: 8px; padding: 16px; margin: 8px 0;
                background: #0f172a;">""",
            unsafe_allow_html=True,
        )

        # Top row: URL + badge + date
        cols = st.columns([3, 1, 1])
        with cols[0]:
            url = result.get("source_url", "")
            if url:
                st.markdown(f"[:link: Source]({url})", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(badge_text)
        with cols[2]:
            date = result.get("date", "")
            if date:
                st.caption(date[:10])

        # Text content
        text = result.get("raw_text", "")
        if len(text) > 300:
            text = text[:300] + "..."
        st.markdown(f">{text}")

        # Themes as pills
        themes = result.get("themes", [])
        if themes:
            pills_html = " ".join(
                f'<span style="background: #1e293b; color: #e2e8f0; '
                f'padding: 2px 8px; border-radius: 12px; font-size: 0.75em; '
                f'margin-right: 4px;">{THEME_LABELS.get(t, t)}</span>'
                for t in themes
            )
            st.markdown(pills_html, unsafe_allow_html=True)

        # Severity
        severity = result.get("severity", "low")
        severity_colors = {
            "low": "#22c55e",
            "medium": "#f59e0b",
            "high": "#ef4444",
            "critical": "#dc2626",
        }
        st.markdown(
            f'<span style="color: {severity_colors.get(severity, "#94a3b8")}; '
            f'font-size: 0.8em;">Severity: {severity.upper()}</span>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)


def _sort_results(results: list, sort_by: str) -> list:
    """Sort results by the selected criteria."""
    if sort_by == "Most Recent":
        return sorted(
            results,
            key=lambda r: r.get("date", "") or "",
            reverse=True,
        )
    elif sort_by == "Most Negative":
        sentiment_order = {"negative": 0, "neutral": 1, "positive": 2}
        return sorted(
            results,
            key=lambda r: sentiment_order.get(r.get("sentiment", "neutral"), 1),
        )
    elif sort_by == "Most Positive":
        sentiment_order = {"positive": 0, "neutral": 1, "negative": 2}
        return sorted(
            results,
            key=lambda r: sentiment_order.get(r.get("sentiment", "neutral"), 1),
        )
    elif sort_by == "Highest Severity":
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            results,
            key=lambda r: severity_order.get(r.get("severity", "low"), 3),
        )
    return results
