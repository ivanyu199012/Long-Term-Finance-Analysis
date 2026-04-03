"""Chart rendering for FinAnalysis.

Builds an interactive Plotly figure with price + moving-average panels
on top and RSI panels on the bottom, one column per ticker.  A summary
header with buy-in scores is rendered as HTML above the chart.  The
result is saved as a self-contained HTML file.
"""

from __future__ import annotations

from typing import Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import MA_STYLES, DRAWDOWN_MAX_SCORE, OUTPUT_FILE, RSI_MAX_SCORE
from data import TickerData


def generate_chart(
    tickers: Sequence[TickerData],
    output_path: str = OUTPUT_FILE,
) -> str:
    """Render the interactive chart and save it to *output_path*.

    Parameters
    ----------
    tickers:
        One :class:`TickerData` per column in the figure.
    output_path:
        File path for the saved HTML file.

    Returns
    -------
    str
        The path the file was written to.
    """
    n_cols = len(tickers)
    subplot_titles = []
    for td in tickers:
        subplot_titles.append(f"{td.label} — {len(td.tail)} Day View")
        subplot_titles.append(f"{td.label} RSI")
        subplot_titles.append(f"{td.label} Score")

    fig = make_subplots(
        rows=3,
        cols=n_cols,
        shared_xaxes=True,
        row_heights=[0.55, 0.20, 0.25],
        vertical_spacing=0.06,
        subplot_titles=subplot_titles,
    )

    for col, td in enumerate(tickers, start=1):
        _add_price_traces(fig, td, row=1, col=col)
        _add_rsi_traces(fig, td, row=2, col=col)
        _add_score_traces(fig, td, row=3, col=col)

    fig.update_layout(
        height=900,
        autosize=True,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(font=dict(size=9)),
        margin=dict(t=40, b=30),
    )

    # Build the full HTML: score header + plotly chart
    header_html = _build_score_header(tickers)
    chart_html = fig.to_html(include_plotlyjs=True, full_html=False)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(_wrap_html(header_html, chart_html))

    return output_path


# ── HTML builders ───────────────────────────────────────────────────


def _build_score_header(tickers: Sequence[TickerData]) -> str:
    """Build an HTML summary bar with one card per ticker."""
    cards = []
    for td in tickers:
        bs = td.buy_score
        bg = _score_color(bs.score)
        latest_rsi = float(td.rsi.iloc[-1])

        # Per-MA score breakdown lines
        ma_detail = "".join(
            f"MA{w}: {v:,.2f} ({td.ma_pct_diffs[w]:+.2f}%) "
            f"→ +{bs.ma_breakdown[w]:.1f}/{td.ma_weights[w]:.1f}<br>"
            for w, v in td.moving_averages.items()
        )

        ma_max = sum(td.ma_weights.values())
        dd_display = min(td.buy_score.current_drawdown, 0)
        cards.append(
            f"<div style='flex:1;background:{bg};color:#fff;border-radius:10px;"
            f"padding:18px 24px;margin:0 8px;min-width:300px;"
            f"display:grid;grid-template-columns:auto 1fr;gap:0 24px;"
            f"align-items:center'>"
            # Left column: name, score, suggestion
            f"<div style='text-align:center'>"
            f"<div style='font-size:20px;font-weight:700'>{td.label}</div>"
            f"<div style='font-size:42px;font-weight:800;line-height:1.1'>"
            f"{bs.score:.1f}<span style='font-size:18px'>/10</span></div>"
            f"<div style='font-size:14px'>{bs.suggestion}</div>"
            f"</div>"
            # Right column: breakdown figures
            f"<div style='font-size:12px;line-height:1.7;"
            f"border-left:1px solid rgba(255,255,255,0.3);padding-left:20px'>"
            f"Price: {td.current_price:,.2f}<br>"
            f"<b>MA score: {bs.ma_score:.1f}/{ma_max:.1f}</b><br>"
            f"{ma_detail}"
            f"<b>RSI score: {bs.rsi_score:.1f}/{RSI_MAX_SCORE:.1f}</b> "
            f"(RSI: {latest_rsi:.1f})<br>"
            f"<b>DD score: {bs.drawdown_score:.1f}/{DRAWDOWN_MAX_SCORE:.1f}</b> "
            f"(DD: {dd_display:.1%}, max: {bs.max_drawdown:.1%})"
            f"</div>"
            f"</div>"
        )

    disclaimer = (
        "<div style='text-align:center;font-size:11px;color:#888;"
        "margin-top:8px'>⚠ Technical indicator score only — "
        "not financial advice</div>"
    )
    return (
        f"<div style='display:flex;justify-content:center;"
        f"flex-wrap:wrap;margin:16px 8px 8px'>"
        f"{''.join(cards)}</div>{disclaimer}"
    )


def _wrap_html(header: str, chart_div: str) -> str:
    """Wrap the header and chart div in a minimal HTML page."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>FinAnalysis</title>"
        "<style>body{margin:0;font-family:system-ui,sans-serif;"
        "background:#fafafa}</style></head><body>"
        f"{header}{chart_div}"
        "</body></html>"
    )


# ── Chart trace helpers ─────────────────────────────────────────────


def _add_price_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add closing-price line and horizontal MA reference lines."""
    show_legend = col == 1

    fig.add_trace(
        go.Scatter(
            x=td.tail.index,
            y=td.tail["Close"],
            mode="lines",
            name="Close",
            line=dict(color="black", width=1.5),
            legendgroup="close",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    for window, ma_value in td.moving_averages.items():
        style = MA_STYLES[window]
        pct = td.ma_pct_diffs[window]
        dash_map = {"--": "dash", "-.": "dashdot", ":": "dot"}
        fig.add_hline(
            y=ma_value,
            line_color=style.color,
            line_dash=dash_map.get(style.linestyle, "solid"),
            line_width=1.2,
            annotation_text=f"MA{window}: {ma_value:,.2f} ({pct:+.2f}%)",
            annotation_font_size=9,
            annotation_position="top left",
            row=row,
            col=col,
        )

    # Latest price marker
    last_date = td.tail.index[-1]
    fig.add_trace(
        go.Scatter(
            x=[last_date],
            y=[td.current_price],
            mode="markers+text",
            name=f"Latest: {td.current_price:,.2f}",
            marker=dict(color="crimson", size=9, symbol="diamond"),
            text=[f"{td.current_price:,.2f}"],
            textposition="top right",
            textfont=dict(size=10, color="crimson"),
            legendgroup=f"latest_{col}",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    fig.update_yaxes(title_text="Price", row=row, col=col)


def _add_rsi_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add RSI line with overbought / oversold bands."""
    rsi = td.rsi_tail
    show_legend = col == 1

    fig.add_trace(
        go.Scatter(
            x=rsi.index,
            y=rsi,
            mode="lines",
            name="RSI",
            line=dict(color="purple", width=1.2),
            legendgroup="rsi",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    for level, color, label in [
        (70, "red", "Overbought (70)"),
        (30, "green", "Oversold (30)"),
    ]:
        fig.add_hline(
            y=level,
            line_color=color,
            line_dash="dash",
            line_width=0.8,
            annotation_text=label,
            annotation_font_size=8,
            annotation_position="top left",
            row=row,
            col=col,
        )

    # Latest RSI marker
    last_date = rsi.index[-1]
    last_rsi = float(rsi.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[last_date],
            y=[last_rsi],
            mode="markers+text",
            name=f"RSI: {last_rsi:.1f}",
            marker=dict(color="purple", size=8, symbol="diamond"),
            text=[f"{last_rsi:.1f}"],
            textposition="top right",
            textfont=dict(size=10, color="purple"),
            legendgroup=f"rsi_latest_{col}",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    fig.update_yaxes(title_text="RSI", range=[0, 100], row=row, col=col)


def _add_score_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add historical buy-in score line with suggestion threshold bands."""
    score = td.score_tail
    show_legend = col == 1

    fig.add_trace(
        go.Scatter(
            x=score.index,
            y=score,
            mode="lines",
            name="Score",
            line=dict(color="darkorange", width=1.5),
            legendgroup="score",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    # Suggestion threshold lines
    for level, label in [
        (8.5, "Aggressive"),
        (6.5, "Increase"),
        (4.5, "Regular"),
        (2.5, "Reduce"),
    ]:
        fig.add_hline(
            y=level,
            line_color="gray",
            line_dash="dot",
            line_width=0.6,
            annotation_text=label,
            annotation_font_size=7,
            annotation_position="top left",
            row=row,
            col=col,
        )

    # Latest score marker
    last_date = score.index[-1]
    last_score = float(score.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[last_date],
            y=[last_score],
            mode="markers+text",
            name=f"Score: {last_score:.1f}",
            marker=dict(color="darkorange", size=8, symbol="diamond"),
            text=[f"{last_score:.1f}"],
            textposition="top right",
            textfont=dict(size=10, color="darkorange"),
            legendgroup=f"score_latest_{col}",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    fig.update_yaxes(title_text="Score", range=[0, 10], row=row, col=col)


def _score_color(score: float) -> str:
    """Return a background colour for the score badge.

    Green tones for high scores (buy), red tones for low (hold off).
    """
    if score >= 8:
        return "#1b7a2b"
    if score >= 6:
        return "#4caf50"
    if score >= 4:
        return "#ff9800"
    if score >= 2:
        return "#f44336"
    return "#b71c1c"
