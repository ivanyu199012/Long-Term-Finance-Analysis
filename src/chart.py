"""Chart rendering for FinAnalysis.

Builds an interactive Plotly figure with price + moving-average panels
on top and RSI panels on the bottom, one column per ticker.  A summary
header with buy-in scores is rendered as HTML above the chart.  The
result is saved as a self-contained HTML file.
"""

from __future__ import annotations

import os
from typing import Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import MA_STYLES, BACKTEST_OUTPUT_FILE, DRAWDOWN_MAX_SCORE, MONTHLY_BUDGET, OUTPUT_FILE, RSI_MAX_SCORE
from src.models import Allocation, BacktestComparison, PortfolioComparison, TickerData


def generate_chart(
    tickers: Sequence[TickerData],
    allocations: Sequence[Allocation] | None = None,
    output_path: str = OUTPUT_FILE,
    tickers_intl: Sequence[TickerData] | None = None,
    tickers_kr: Sequence[TickerData] | None = None,
) -> str:
    """Render the interactive chart and save it to *output_path*.

    Parameters
    ----------
    tickers:
        Legacy: all tickers in one group (used if tickers_intl/tickers_kr not provided).
    allocations:
        Portfolio allocation (applies to KR group only when two-group mode).
    output_path:
        File path for the saved HTML file.
    tickers_intl:
        International tickers (USD reference). If provided, enables two-group mode.
    tickers_kr:
        Korean tickers (KRW investment). If provided, enables two-group mode.

    Returns
    -------
    str
        The path the file was written to.
    """
    # Two-group mode with tabs
    if tickers_intl is not None and tickers_kr is not None:
        tab_contents: list[tuple[str, str, str]] = []  # (id, label, html)

        # ── Korean tab (first/default) ──
        if tickers_kr:
            kr_cards = _build_score_header(tickers_kr, allocations=allocations)
            kr_chart = _build_chart_figure(tickers_kr)
            tab_contents.append(("kr", "Korea 🇰🇷", f"{kr_cards}{kr_chart}"))

        # ── International tab ──
        if tickers_intl:
            intl_cards = _build_score_header(tickers_intl, allocations=None)
            intl_chart = _build_chart_figure(tickers_intl)
            tab_contents.append(("intl", "International 🌐", f"{intl_cards}{intl_chart}"))

        body_html = _build_tabbed_layout(tab_contents)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(_wrap_html(body_html, ""))
        return output_path

    # Legacy single-group mode (backward compat)
    header_html = _build_score_header(tickers, allocations)
    chart_html = _build_chart_figure(tickers)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(_wrap_html(header_html, chart_html))
    return output_path


def _build_tabbed_layout(tabs: list[tuple[str, str, str]]) -> str:
    """Build an HTML tabbed interface.

    Parameters
    ----------
    tabs:
        List of (id, label, content_html) tuples.
        First tab is active by default.
    """
    if not tabs:
        return ""

    # Tab buttons
    buttons = []
    for i, (tab_id, label, _) in enumerate(tabs):
        active_class = " tab-active" if i == 0 else ""
        buttons.append(
            f"<button class='tab-btn{active_class}' "
            f"onclick='switchTab(\"{tab_id}\")' id='btn-{tab_id}'>{label}</button>"
        )
    tab_bar = (
        f"<div style='display:flex;justify-content:center;gap:8px;"
        f"margin:16px 0 8px'>{''.join(buttons)}</div>"
    )

    # Tab content panels
    panels = []
    for i, (tab_id, _, content) in enumerate(tabs):
        display = "block" if i == 0 else "none"
        panels.append(
            f"<div id='tab-{tab_id}' class='tab-panel' style='display:{display}'>"
            f"{content}</div>"
        )

    # JavaScript for tab switching
    script = """
    <script>
    function switchTab(tabId) {
        document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-active'));
        document.getElementById('tab-' + tabId).style.display = 'block';
        document.getElementById('btn-' + tabId).classList.add('tab-active');
        // Trigger Plotly resize for the newly visible charts
        window.dispatchEvent(new Event('resize'));
    }
    </script>
    """

    # Tab button styles
    style = """
    <style>
    .tab-btn {
        padding: 10px 24px;
        font-size: 15px;
        font-weight: 600;
        border: 2px solid #ddd;
        border-radius: 8px;
        background: #f5f5f5;
        color: #555;
        cursor: pointer;
        transition: all 0.2s;
    }
    .tab-btn:hover { background: #e8e8e8; }
    .tab-btn.tab-active {
        background: #1976D2;
        color: #fff;
        border-color: #1976D2;
    }
    </style>
    """

    return f"{style}{tab_bar}{''.join(panels)}{script}"


def _build_chart_figure(tickers: Sequence[TickerData]) -> str:
    """Build a Plotly chart HTML div for a group of tickers."""
    n_cols = len(tickers)
    row1_titles = [f"{td.label} — {len(td.tail)} Day View" for td in tickers]
    row2_titles = [f"{td.label} RSI" for td in tickers]
    row3_titles = [f"{td.label} Score" for td in tickers]
    subplot_titles = row1_titles + row2_titles + row3_titles

    fig = make_subplots(
        rows=3,
        cols=n_cols,
        shared_xaxes=False,
        row_heights=[0.55, 0.20, 0.25],
        vertical_spacing=0.08,
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
        margin=dict(t=40, b=50, r=120),
    )

    return fig.to_html(include_plotlyjs="cdn", full_html=False)


# ── HTML builders ───────────────────────────────────────────────────


def _build_score_header(
    tickers: Sequence[TickerData],
    allocations: Sequence[Allocation] | None = None,
) -> str:
    """Build an HTML summary bar with one card per ticker."""
    alloc_map: dict[str, Allocation] = {}
    if allocations:
        alloc_map = {a.label: a for a in allocations}

    cards = []
    for td in tickers:
        bs = td.buy_score
        bg = _score_color(bs.score)
        latest_rsi = float(td.rsi.iloc[-1])

        ma_detail = "".join(
            f"MA{w}: {v:,.2f} ({td.ma_pct_diffs[w]:+.2f}%) "
            f"→ +{bs.ma_breakdown[w]:.1f}/{td.ma_weights[w]:.1f}<br>"
            for w, v in td.moving_averages.items()
        )

        ma_max = sum(td.ma_weights.values())
        dd_display = min(td.buy_score.current_drawdown, 0)

        alloc = alloc_map.get(td.label)
        alloc_line = ""
        if alloc:
            alloc_line = (
                f"<br><b style='font-size:13px'>Allocation: {alloc.weight_pct:.1f}% "
                f"→ ₩{alloc.amount:,.0f}</b>"
            )

        cards.append(
            f"<div style='flex:1;background:{bg};color:#fff;border-radius:10px;"
            f"padding:18px 24px;margin:0 8px;min-width:300px'>"
            # Score section (top)
            f"<div style='text-align:center;margin-bottom:12px'>"
            f"<div style='font-size:20px;font-weight:700'>{td.label}</div>"
            f"<div style='font-size:42px;font-weight:800;line-height:1.1'>"
            f"{bs.score:.1f}<span style='font-size:18px'>/10</span></div>"
            f"<div style='font-size:14px'>{bs.suggestion}</div>"
            f"</div>"
            # Data section (below)
            f"<div style='font-size:14px;line-height:1.7;"
            f"background:rgba(0,0,0,0.25);border-radius:6px;padding:10px 14px'>"
            f"{_build_price_line(td)}"
            f"<b>MA score: {bs.ma_score:.1f}/{ma_max:.1f}</b><br>"
            f"{ma_detail}"
            f"<b>RSI score: {bs.rsi_score:.1f}/{RSI_MAX_SCORE:.1f}</b> "
            f"(RSI: {latest_rsi:.1f})<br>"
            f"<b>DD score: {bs.drawdown_score:.1f}/{DRAWDOWN_MAX_SCORE:.1f}</b> "
            f"(DD: {dd_display:.1%}, max: {bs.max_drawdown:.1%}, "
            f"full at {td.drawdown_full_pct:.0%})"
            f"{alloc_line}"
            f"</div>"
            f"</div>"
        )

    disclaimer = (
        "<div style='text-align:center;font-size:11px;color:#888;"
        "margin-top:8px'>⚠ Technical indicator score only — "
        "not financial advice</div>"
    )

    est_lines = []
    for td in tickers:
        if td.estimated_dates:
            dates = ", ".join(td.estimated_dates)
            est_lines.append(f"{td.label}: {dates}")
    est_warning = ""
    if est_lines:
        est_detail = " | ".join(est_lines)
        est_warning = (
            "<div style='text-align:center;font-size:11px;color:#c62828;"
            "margin-top:4px'>⚠ Estimated data (mean of prev close &amp; live price): "
            f"{est_detail}</div>"
        )

    budget_line = ""
    if allocations:
        budget_line = (
            f"<div style='text-align:center;font-size:13px;color:#333;"
            f"margin-top:10px;font-weight:600'>"
            f"Monthly Budget: ₩{MONTHLY_BUDGET:,.0f}</div>"
        )

    return (
        f"<div style='display:flex;justify-content:center;"
        f"flex-wrap:wrap;margin:16px 8px 8px'>"
        f"{''.join(cards)}</div>{budget_line}{disclaimer}{est_warning}"
    )


def _wrap_html(header: str, chart_div: str) -> str:
    """Wrap the header and chart div in a minimal HTML page."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>FinAnalysis</title>"
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>"
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
    import pandas as pd

    show_legend = col == 1

    # Extend the price line to include the live price point
    x_data = td.tail.index.tolist()
    y_data = td.tail["Close"].tolist()
    if td.is_live_price and td.live_price_time:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in td.tail.index:
            x_data.append(marker_date)
            y_data.append(td.current_price)

    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=y_data,
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

    # Place the latest price marker at today's date if live, otherwise at last data point
    if td.is_live_price and td.live_price_time:
        from datetime import datetime
        # Use today's date for the marker position
        import pandas as pd
        marker_date = pd.Timestamp.now().normalize()
    else:
        marker_date = td.tail.index[-1]

    fig.add_trace(
        go.Scatter(
            x=[marker_date],
            y=[td.current_price],
            mode="markers+text",
            name=f"Latest: {td.current_price:,.2f}",
            marker=dict(color="crimson", size=9, symbol="diamond"),
            text=[f"{td.current_price:,.2f}"],
            textposition="top left",
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
    import pandas as pd

    rsi = td.rsi_tail
    show_legend = col == 1

    # Extend RSI line to today if live price is available
    x_data = rsi.index.tolist()
    y_data = rsi.tolist()
    if td.is_live_price and td.live_price_time:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in rsi.index:
            # RSI should already include today if live price was appended to DataFrame
            # but if not, carry forward last value
            x_data.append(marker_date)
            y_data.append(float(rsi.iloc[-1]))

    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=y_data,
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
        (45, "orange", "RSI score 0 (45)"),
        (35, "teal", "RSI score full (35)"),
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

    # RSI marker at today if live, otherwise at last data point
    if td.is_live_price and td.live_price_time:
        rsi_marker_date = pd.Timestamp.now().normalize()
    else:
        rsi_marker_date = rsi.index[-1]
    last_rsi = float(rsi.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[rsi_marker_date],
            y=[last_rsi],
            mode="markers+text",
            name=f"RSI: {last_rsi:.1f}",
            marker=dict(color="purple", size=8, symbol="diamond"),
            text=[f"{last_rsi:.1f}"],
            textposition="top left",
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
    import pandas as pd

    score = td.score_tail
    show_legend = col == 1

    # Extend score line to today if live price is available
    x_data = score.index.tolist()
    y_data = score.tolist()
    if td.is_live_price and td.live_price_time and td.buy_score:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in score.index:
            x_data.append(marker_date)
            y_data.append(td.buy_score.score)  # use the live-computed score

    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=y_data,
            mode="lines",
            name="Score",
            line=dict(color="darkorange", width=1.5),
            legendgroup="score",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

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

    # Score marker at today if live, otherwise at last data point
    if td.is_live_price and td.live_price_time and td.buy_score:
        score_marker_date = pd.Timestamp.now().normalize()
        last_score = td.buy_score.score
    else:
        score_marker_date = score.index[-1]
        last_score = float(score.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[score_marker_date],
            y=[last_score],
            mode="markers+text",
            name=f"Score: {last_score:.1f}",
            marker=dict(color="darkorange", size=8, symbol="diamond"),
            text=[f"{last_score:.1f}"],
            textposition="top left",
            textfont=dict(size=10, color="darkorange"),
            legendgroup=f"score_latest_{col}",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    fig.update_yaxes(title_text="Score", range=[0, 10], row=row, col=col)


def _build_price_line(td: TickerData) -> str:
    """Build the price display line for a score card."""
    if td.is_live_price and td.close_price is not None:
        live_label = f"Live ({td.live_price_time})" if td.live_price_time else "Live"
        close_label = f"Close ({td.close_price_date})" if td.close_price_date else "Close"
        return (
            f"<b style='color:#FFEB3B'>{live_label}: {td.current_price:,.2f}</b><br>"
            f"{close_label}: {td.close_price:,.2f}<br>"
        )
    elif td.live_price_warning:
        close_label = f"Close ({td.close_price_date})" if td.close_price_date else "Price"
        return (
            f"{close_label}: {td.current_price:,.2f}<br>"
            f"<span style='color:#ffcdd2;font-size:10px'>⚠ {td.live_price_warning}</span><br>"
        )
    else:
        return f"Price: {td.current_price:,.2f}<br>"


def _score_color(score: float) -> str:
    """Return a background colour for the score badge."""
    if score >= 8:
        return "#1b7a2b"
    if score >= 6:
        return "#4caf50"
    if score >= 4:
        return "#ff9800"
    if score >= 2:
        return "#f44336"
    return "#b71c1c"


# ── Backtest dashboard ──────────────────────────────────────────────


def generate_backtest_chart(
    comparisons: Sequence[BacktestComparison],
    portfolio_comparisons: Sequence[PortfolioComparison] | None = None,
    output_path: str = BACKTEST_OUTPUT_FILE,
) -> str:
    """Render a backtest results dashboard as a static HTML table.

    No Plotly charts — just summary cards and comparison tables.
    The key question answered: does score-based DCA beat flat DCA?
    """
    title = (
        "<div style='text-align:center;font-size:22px;font-weight:700;"
        "margin:16px 0 8px;color:#333'>"
        "FinAnalysis — Backtest: Flat DCA vs Score-based DCA</div>"
    )

    # Per-ticker comparison tables
    tables_html = _build_backtest_tables(comparisons)

    # Portfolio comparison tables
    portfolio_html = ""
    if portfolio_comparisons:
        portfolio_html = _build_portfolio_tables(portfolio_comparisons)

    disclaimer = (
        "<div style='text-align:center;font-size:11px;color:#888;"
        "margin:16px 0'>⚠ Past performance does not guarantee future results. "
        "This is a simulation — not financial advice.</div>"
    )

    body = f"{title}{tables_html}{portfolio_html}{disclaimer}"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(_wrap_backtest_html(body))

    return output_path


def _wrap_backtest_html(body: str) -> str:
    """Wrap backtest content in a minimal HTML page (no Plotly needed)."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>FinAnalysis — Backtest</title>"
        "<style>"
        "body{margin:0;padding:20px;font-family:system-ui,sans-serif;background:#fafafa}"
        "table{border-collapse:collapse;width:100%;margin:8px 0}"
        "th,td{padding:8px 12px;text-align:right;border-bottom:1px solid #e0e0e0}"
        "th{background:#f5f5f5;font-weight:600;font-size:12px;color:#555}"
        "td{font-size:13px}"
        "td:first-child,th:first-child{text-align:left}"
        ".edge-pos{color:#388E3C;font-weight:700}"
        ".edge-neg{color:#F44336;font-weight:700}"
        ".section{max-width:900px;margin:0 auto 24px}"
        ".section-title{font-size:16px;font-weight:700;color:#333;"
        "margin:20px 0 8px;padding-bottom:6px;border-bottom:2px solid #ddd}"
        "</style></head><body>"
        f"{body}"
        "</body></html>"
    )


def _build_backtest_tables(comparisons: Sequence[BacktestComparison]) -> str:
    """Build HTML tables comparing flat vs score DCA per ticker."""
    # Group by period
    by_period: dict[str, list[BacktestComparison]] = {}
    for comp in comparisons:
        by_period.setdefault(comp.period, []).append(comp)

    html_parts: list[str] = []
    period_order = sorted(by_period.keys(), key=lambda p: int(p.replace("y", "")))

    for period in period_order:
        comps = by_period[period]
        html_parts.append(
            f"<div class='section'>"
            f"<div class='section-title'>Per-Ticker Backtest — {period}</div>"
            f"<table>"
            f"<tr><th>Ticker</th><th>Months</th>"
            f"<th>Flat DCA Return</th><th>Score (norm) Return</th><th>Edge</th>"
            f"<th>Flat Max DD</th><th>Score Max DD</th></tr>"
        )

        for comp in comps:
            flat = comp.flat
            norm = comp.score_normalized
            edge = norm.total_return_pct - flat.total_return_pct
            edge_class = "edge-pos" if edge > 0 else "edge-neg"

            html_parts.append(
                f"<tr>"
                f"<td><b>{comp.label}</b></td>"
                f"<td>{flat.n_months}</td>"
                f"<td>{flat.total_return_pct:+.2f}%</td>"
                f"<td>{norm.total_return_pct:+.2f}%</td>"
                f"<td class='{edge_class}'>{edge:+.2f}pp</td>"
                f"<td>{flat.max_drawdown_pct:.1f}%</td>"
                f"<td>{norm.max_drawdown_pct:.1f}%</td>"
                f"</tr>"
            )

        html_parts.append("</table></div>")

    return "".join(html_parts)


def _build_portfolio_tables(
    portfolio_comparisons: Sequence[PortfolioComparison],
) -> str:
    """Build HTML table for portfolio-level backtest results."""
    html_parts: list[str] = []
    html_parts.append(
        "<div class='section'>"
        "<div class='section-title'>Portfolio Backtest</div>"
        "<table>"
        "<tr><th>Period</th><th>Months</th>"
        "<th>Flat Alloc Return</th><th>Score Alloc Return</th><th>Edge</th>"
        "<th>Flat Max DD</th><th>Score Max DD</th></tr>"
    )

    for pc in sorted(portfolio_comparisons, key=lambda x: int(x.period.replace("y", ""))):
        flat = pc.flat
        score = pc.score_alloc
        edge = score.total_return_pct - flat.total_return_pct
        edge_class = "edge-pos" if edge > 0 else "edge-neg"

        html_parts.append(
            f"<tr>"
            f"<td><b>{pc.period}</b></td>"
            f"<td>{flat.n_months}</td>"
            f"<td>{flat.total_return_pct:+.2f}%</td>"
            f"<td>{score.total_return_pct:+.2f}%</td>"
            f"<td class='{edge_class}'>{edge:+.2f}pp</td>"
            f"<td>{flat.max_drawdown_pct:.1f}%</td>"
            f"<td>{score.max_drawdown_pct:.1f}%</td>"
            f"</tr>"
        )

    html_parts.append("</table></div>")
    return "".join(html_parts)
