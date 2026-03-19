"""
Score gauge and overview chart components.
"""

import streamlit as st
import plotly.graph_objects as go


def render_score_gauge(score: int) -> None:
    """
    Render a Plotly gauge chart for the overall score.

    Args:
        score: Overall reputation score (0–100).
    """
    # Determine color
    if score >= 70:
        color = "#22c55e"
        label = "Good"
    elif score >= 40:
        color = "#f59e0b"
        label = "Mixed"
    else:
        color = "#ef4444"
        label = "Poor"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            title={"text": f"Overall Reputation Score", "font": {"size": 18, "color": "#e2e8f0"}},
            number={"font": {"size": 48, "color": color}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 2,
                    "tickcolor": "#475569",
                    "tickfont": {"color": "#94a3b8"},
                },
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": "#1e293b",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 30], "color": "rgba(239, 68, 68, 0.15)"},
                    {"range": [30, 50], "color": "rgba(245, 158, 11, 0.1)"},
                    {"range": [50, 70], "color": "rgba(245, 158, 11, 0.15)"},
                    {"range": [70, 100], "color": "rgba(34, 197, 94, 0.15)"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 4},
                    "thickness": 0.8,
                    "value": score,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0"},
        height=280,
        margin=dict(l=30, r=30, t=60, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Rating: **{label}** ({score}/100)")


def render_source_pie_chart(by_source: dict) -> None:
    """
    Render a pie chart showing result distribution by source.

    Args:
        by_source: Dict mapping source names to their data.
    """
    labels = []
    values = []
    colors = [
        "#3b82f6", "#22c55e", "#f59e0b", "#ef4444",
        "#8b5cf6", "#06b6d4", "#ec4899", "#64748b",
    ]

    for source_key, source_data in by_source.items():
        platform = source_data.get("platform", source_key)
        count = source_data.get("result_count", 0)
        if count > 0:
            labels.append(platform)
            values.append(count)

    if not values:
        st.info("No source data to display.")
        return

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker_colors=colors[: len(labels)],
            textinfo="label+value",
            textposition="outside",
            textfont={"color": "#e2e8f0", "size": 12},
            hovertemplate="%{label}: %{value} results<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0"},
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        title={
            "text": "Results by Source",
            "font": {"size": 16, "color": "#e2e8f0"},
        },
        showlegend=True,
        legend={"font": {"color": "#94a3b8"}},
    )

    st.plotly_chart(fig, use_container_width=True)


def render_sentiment_overview(analyzed_results: list) -> None:
    """
    Render a stacked bar chart showing sentiment by reviewer type.
    """
    from collections import Counter, defaultdict

    type_sentiments = defaultdict(Counter)
    for r in analyzed_results:
        rtype = r.get("reviewer_type", "general")
        sentiment = r.get("sentiment", "neutral")
        type_sentiments[rtype][sentiment] += 1

    if not type_sentiments:
        return

    types = sorted(type_sentiments.keys())
    positive = [type_sentiments[t]["positive"] for t in types]
    neutral = [type_sentiments[t]["neutral"] for t in types]
    negative = [type_sentiments[t]["negative"] for t in types]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(name="Positive", x=types, y=positive, marker_color="#22c55e")
    )
    fig.add_trace(
        go.Bar(name="Neutral", x=types, y=neutral, marker_color="#94a3b8")
    )
    fig.add_trace(
        go.Bar(name="Negative", x=types, y=negative, marker_color="#ef4444")
    )

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0"},
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        title={
            "text": "Sentiment by Reviewer Type",
            "font": {"size": 16, "color": "#e2e8f0"},
        },
        legend={"font": {"color": "#94a3b8"}},
        xaxis={"gridcolor": "#1e293b"},
        yaxis={"gridcolor": "#1e293b"},
    )

    st.plotly_chart(fig, use_container_width=True)
