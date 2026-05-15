"""Chart rendering for FinAnalysis.

Builds an interactive Plotly figure with price + moving-average panels
on top and RSI panels on the bottom, one column per ticker.  A summary
header with buy-in scores is rendered as HTML above the chart.  The
result is saved as a self-contained HTML file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader
from plotly.subplots import make_subplots

from src.config import BACKTEST_OUTPUT_FILE, COMPARISON_PAIRS, MA_STYLES, DRAWDOWN_MAX_SCORE, MONTHLY_BUDGET, OUTPUT_FILE, RSI_MAX_SCORE
from src.indicators import SCORE_LEVELS
from src.models import Allocation, BacktestComparison, PortfolioComparison, TickerData

# ── Jinja2 environment ──────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,
)


def _price_line(td: TickerData) -> str:
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


# ── Public API ──────────────────────────────────────────────────────


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
        tab_contents: list[tuple[str, str, str]] = []

        if tickers_kr:
            kr_cards = _render_score_cards(tickers_kr, allocations=allocations)
            kr_chart = _build_chart_figure(tickers_kr)
            tab_contents.append(("kr", "Korea 🇰🇷", f"{kr_cards}{kr_chart}"))

        if tickers_intl:
            intl_cards = _render_score_cards(tickers_intl, allocations=None)
            intl_chart = _build_chart_figure(tickers_intl)
            tab_contents.append(("intl", "International 🌐", f"{intl_cards}{intl_chart}"))

        # Comparison tab
        if tickers_kr and tickers_intl:
            compare_html = _build_comparison_tab(tickers_kr, tickers_intl)
            if compare_html:
                tab_contents.append(("compare", "Comparison 🔄", compare_html))

        tab_html = _render_tab_layout(tab_contents)
        body_html = tab_html
    else:
        # Legacy single-group mode
        body_html = _render_score_cards(tickers, allocations) + _build_chart_figure(tickers)

    template = _env.get_template("dashboard.html")
    html = template.render(body_html=body_html)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path


def generate_backtest_chart(
    comparisons: Sequence[BacktestComparison],
    portfolio_comparisons: Sequence[PortfolioComparison] | None = None,
    output_path: str = BACKTEST_OUTPUT_FILE,
) -> str:
    """Render a backtest results dashboard as a static HTML table."""
    # Group comparisons by period
    by_period: dict[str, list[BacktestComparison]] = {}
    for comp in comparisons:
        by_period.setdefault(comp.period, []).append(comp)
    period_order = sorted(by_period.keys(), key=lambda p: int(p.replace("y", "")))
    comparisons_by_period = [(p, by_period[p]) for p in period_order]

    # Sort portfolio comparisons by period
    sorted_portfolio = None
    if portfolio_comparisons:
        sorted_portfolio = sorted(
            portfolio_comparisons, key=lambda x: int(x.period.replace("y", ""))
        )

    template = _env.get_template("backtest.html")
    html = template.render(
        comparisons_by_period=comparisons_by_period,
        portfolio_comparisons=sorted_portfolio,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path


# ── Template rendering helpers ──────────────────────────────────────


def _render_score_cards(
    tickers: Sequence[TickerData],
    allocations: Sequence[Allocation] | None = None,
) -> str:
    """Render score cards HTML using Jinja2 template."""
    alloc_map: dict[str, Allocation] = {}
    if allocations:
        alloc_map = {a.label: a for a in allocations}

    # Build estimated data warnings
    est_lines = []
    for td in tickers:
        if td.estimated_dates:
            dates = ", ".join(td.estimated_dates)
            est_lines.append(f"{td.label}: {dates}")
    estimated_warnings = " | ".join(est_lines) if est_lines else ""

    template = _env.get_template("partials/score_cards.html")
    return template.render(
        tickers=tickers,
        alloc_map=alloc_map,
        allocations=allocations,
        score_color=_score_color,
        price_line=_price_line,
        rsi_max_score=RSI_MAX_SCORE,
        drawdown_max_score=DRAWDOWN_MAX_SCORE,
        monthly_budget=MONTHLY_BUDGET,
        estimated_warnings=estimated_warnings,
    )


def _render_tab_layout(tabs: list[tuple[str, str, str]]) -> str:
    """Render tabbed layout HTML using Jinja2 template."""
    template = _env.get_template("partials/tab_layout.html")
    return template.render(tabs=tabs)


def _render_comparison_subtabs(pairs: list[tuple[str, str, str]]) -> str:
    """Render comparison sub-tab layout using Jinja2 template."""
    template = _env.get_template("partials/comparison_subtabs.html")
    return template.render(pairs=pairs)


# ── Comparison tab ──────────────────────────────────────────────────


def _build_comparison_tab(
    tickers_kr: Sequence[TickerData],
    tickers_intl: Sequence[TickerData],
) -> str:
    """Build the full comparison tab content with sub-tabs for each pair."""
    # Build lookup maps
    kr_map = {td.symbol: td for td in tickers_kr}
    intl_map = {td.symbol: td for td in tickers_intl}

    pair_contents: list[tuple[str, str, str]] = []  # (id, label, html)

    for pair in COMPARISON_PAIRS:
        kr_td = kr_map.get(pair["kr_symbol"])
        intl_td = intl_map.get(pair["intl_symbol"])
        if not kr_td or not intl_td:
            continue

        # Score cards for the pair (2 cards side by side)
        cards_html = _render_score_cards([kr_td, intl_td], allocations=None)
        # Comparison chart (normalized price, ratio, score)
        chart_html = _build_comparison_figure(kr_td, intl_td)

        pair_id = pair["label"].lower().replace(" ", "_")
        pair_contents.append((pair_id, pair["label"], f"{cards_html}{chart_html}"))

    if not pair_contents:
        return ""

    return _render_comparison_subtabs(pair_contents)


def _build_comparison_figure(kr_td: TickerData, intl_td: TickerData) -> str:
    """Build a Plotly comparison chart for a KR/Intl pair.

    Row 1: 100-day price view side by side (KR left, Intl right)
    Row 2: Normalized price (both rebased to 100, overlaid)
    Row 3: Score comparison (both score lines overlaid)
    """
    fig = make_subplots(
        rows=3,
        cols=2,
        shared_xaxes=False,
        row_heights=[0.40, 0.35, 0.25],
        vertical_spacing=0.10,
        horizontal_spacing=0.06,
        subplot_titles=[
            f"{kr_td.label} — {len(kr_td.tail)} Day View",
            f"{intl_td.label} — {len(intl_td.tail)} Day View",
            f"Normalized Price — {kr_td.label} vs {intl_td.label}",
            "",  # empty (merged with col 1)
            "Score Comparison",
            "",  # empty (merged with col 1)
        ],
        specs=[
            [{}, {}],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None],
        ],
    )

    # ── Row 1: 100-day price view side by side ──
    # KR (left)
    fig.add_trace(
        go.Scatter(
            x=kr_td.tail.index, y=kr_td.tail["Close"],
            mode="lines", name=kr_td.label,
            line=dict(color="#1976D2", width=1.5),
            showlegend=False,
        ),
        row=1, col=1,
    )
    for window, ma_value in kr_td.moving_averages.items():
        style = MA_STYLES[window]
        pct = kr_td.ma_pct_diffs[window]
        dash_map = {"--": "dash", "-.": "dashdot", ":": "dot"}
        fig.add_hline(
            y=ma_value, line_color=style.color,
            line_dash=dash_map.get(style.linestyle, "solid"), line_width=1.2,
            annotation_text=f"MA{window}: {ma_value:,.2f} ({pct:+.2f}%)",
            annotation_font_size=8, annotation_position="top left",
            row=1, col=1,
        )
    fig.update_yaxes(title_text="Price (KRW)", row=1, col=1)

    # Intl (right)
    fig.add_trace(
        go.Scatter(
            x=intl_td.tail.index, y=intl_td.tail["Close"],
            mode="lines", name=intl_td.label,
            line=dict(color="#F57C00", width=1.5),
            showlegend=False,
        ),
        row=1, col=2,
    )
    for window, ma_value in intl_td.moving_averages.items():
        style = MA_STYLES[window]
        pct = intl_td.ma_pct_diffs[window]
        dash_map = {"--": "dash", "-.": "dashdot", ":": "dot"}
        fig.add_hline(
            y=ma_value, line_color=style.color,
            line_dash=dash_map.get(style.linestyle, "solid"), line_width=1.2,
            annotation_text=f"MA{window}: {ma_value:,.2f} ({pct:+.2f}%)",
            annotation_font_size=8, annotation_position="top left",
            row=1, col=2,
        )
    fig.update_yaxes(title_text="Price (USD)", row=1, col=2)

    # ── Row 2: Normalized price (overlaid, spans both columns) ──
    kr_close = kr_td.tail["Close"]
    intl_close = intl_td.tail["Close"]

    kr_norm = (kr_close / kr_close.iloc[0]) * 100
    intl_norm = (intl_close / intl_close.iloc[0]) * 100

    fig.add_trace(
        go.Scatter(
            x=kr_norm.index, y=kr_norm.values,
            mode="lines", name=kr_td.label,
            line=dict(color="#1976D2", width=1.5),
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=intl_norm.index, y=intl_norm.values,
            mode="lines", name=intl_td.label,
            line=dict(color="#F57C00", width=1.5),
        ),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="Normalized (base=100)", row=2, col=1)

    # ── Row 3: Score comparison (spans both columns) ──
    kr_score = kr_td.score_tail
    intl_score = intl_td.score_tail

    fig.add_trace(
        go.Scatter(
            x=kr_score.index, y=kr_score.values,
            mode="lines", name=f"{kr_td.label} Score",
            line=dict(color="#1976D2", width=1.2),
        ),
        row=3, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=intl_score.index, y=intl_score.values,
            mode="lines", name=f"{intl_td.label} Score",
            line=dict(color="#F57C00", width=1.2),
        ),
        row=3, col=1,
    )
    fig.update_yaxes(title_text="Score", range=[0, 10], row=3, col=1)

    fig.update_layout(
        height=900,
        autosize=True,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(font=dict(size=10)),
        margin=dict(t=40, b=30, r=60),
    )

    return fig.to_html(include_plotlyjs="cdn", full_html=False)


# ── Plotly figure builders ──────────────────────────────────────────


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


# ── Chart trace helpers ─────────────────────────────────────────────


def _add_price_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add closing-price line and horizontal MA reference lines."""
    import pandas as pd

    show_legend = col == 1

    x_data = td.tail.index.tolist()
    y_data = td.tail["Close"].tolist()
    if td.is_live_price and td.live_price_time:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in td.tail.index:
            x_data.append(marker_date)
            y_data.append(td.current_price)

    fig.add_trace(
        go.Scatter(
            x=x_data, y=y_data, mode="lines", name="Close",
            line=dict(color="black", width=1.5),
            legendgroup="close", showlegend=show_legend,
        ),
        row=row, col=col,
    )

    for window, ma_value in td.moving_averages.items():
        style = MA_STYLES[window]
        pct = td.ma_pct_diffs[window]
        dash_map = {"--": "dash", "-.": "dashdot", ":": "dot"}
        fig.add_hline(
            y=ma_value, line_color=style.color,
            line_dash=dash_map.get(style.linestyle, "solid"), line_width=1.2,
            annotation_text=f"MA{window}: {ma_value:,.2f} ({pct:+.2f}%)",
            annotation_font_size=9, annotation_position="top left",
            row=row, col=col,
        )

    if td.is_live_price and td.live_price_time:
        marker_date = pd.Timestamp.now().normalize()
    else:
        marker_date = td.tail.index[-1]

    fig.add_trace(
        go.Scatter(
            x=[marker_date], y=[td.current_price],
            mode="markers+text", name=f"Latest: {td.current_price:,.2f}",
            marker=dict(color="crimson", size=9, symbol="diamond"),
            text=[f"{td.current_price:,.2f}"], textposition="top left",
            textfont=dict(size=10, color="crimson"),
            legendgroup=f"latest_{col}", showlegend=show_legend,
        ),
        row=row, col=col,
    )
    fig.update_yaxes(title_text="Price", row=row, col=col)


def _add_rsi_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add RSI line with overbought / oversold bands."""
    import pandas as pd

    rsi = td.rsi_tail
    show_legend = col == 1

    x_data = rsi.index.tolist()
    y_data = rsi.tolist()
    if td.is_live_price and td.live_price_time:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in rsi.index:
            x_data.append(marker_date)
            y_data.append(float(rsi.iloc[-1]))

    fig.add_trace(
        go.Scatter(
            x=x_data, y=y_data, mode="lines", name="RSI",
            line=dict(color="purple", width=1.2),
            legendgroup="rsi", showlegend=show_legend,
        ),
        row=row, col=col,
    )

    for level, color, label in [
        (70, "red", "Overbought (70)"),
        (45, "orange", "RSI score 0 (45)"),
        (35, "teal", "RSI score full (35)"),
        (30, "green", "Oversold (30)"),
    ]:
        fig.add_hline(
            y=level, line_color=color, line_dash="dash", line_width=0.8,
            annotation_text=label, annotation_font_size=8,
            annotation_position="top left", row=row, col=col,
        )

    if td.is_live_price and td.live_price_time:
        rsi_marker_date = pd.Timestamp.now().normalize()
    else:
        rsi_marker_date = rsi.index[-1]
    last_rsi = float(rsi.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[rsi_marker_date], y=[last_rsi],
            mode="markers+text", name=f"RSI: {last_rsi:.1f}",
            marker=dict(color="purple", size=8, symbol="diamond"),
            text=[f"{last_rsi:.1f}"], textposition="top left",
            textfont=dict(size=10, color="purple"),
            legendgroup=f"rsi_latest_{col}", showlegend=show_legend,
        ),
        row=row, col=col,
    )
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=row, col=col)


def _add_score_traces(
    fig: go.Figure, td: TickerData, row: int, col: int,
) -> None:
    """Add historical buy-in score line with suggestion threshold bands."""
    import pandas as pd

    score = td.score_tail
    show_legend = col == 1

    x_data = score.index.tolist()
    y_data = score.tolist()
    if td.is_live_price and td.live_price_time and td.buy_score:
        marker_date = pd.Timestamp.now().normalize()
        if marker_date not in score.index:
            x_data.append(marker_date)
            y_data.append(td.buy_score.score)

    fig.add_trace(
        go.Scatter(
            x=x_data, y=y_data, mode="lines", name="Score",
            line=dict(color="darkorange", width=1.5),
            legendgroup="score", showlegend=show_legend,
        ),
        row=row, col=col,
    )

    for level, label in SCORE_LEVELS:
        fig.add_hline(
            y=level, line_color="gray", line_dash="dot", line_width=0.6,
            annotation_text=label, annotation_font_size=7,
            annotation_position="top left", row=row, col=col,
        )

    if td.is_live_price and td.live_price_time and td.buy_score:
        score_marker_date = pd.Timestamp.now().normalize()
        last_score = td.buy_score.score
    else:
        score_marker_date = score.index[-1]
        last_score = float(score.iloc[-1])
    fig.add_trace(
        go.Scatter(
            x=[score_marker_date], y=[last_score],
            mode="markers+text", name=f"Score: {last_score:.1f}",
            marker=dict(color="darkorange", size=8, symbol="diamond"),
            text=[f"{last_score:.1f}"], textposition="top left",
            textfont=dict(size=10, color="darkorange"),
            legendgroup=f"score_latest_{col}", showlegend=show_legend,
        ),
        row=row, col=col,
    )
    fig.update_yaxes(title_text="Score", range=[0, 10], row=row, col=col)
