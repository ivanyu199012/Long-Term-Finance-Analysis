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

    header_html = _build_score_header(tickers, allocations)
    chart_html = fig.to_html(include_plotlyjs=True, full_html=False)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(_wrap_html(header_html, chart_html))

    return output_path


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
            f"padding:18px 24px;margin:0 8px;min-width:300px;"
            f"display:grid;grid-template-columns:auto 1fr;gap:0 24px;"
            f"align-items:center'>"
            f"<div style='text-align:center'>"
            f"<div style='font-size:20px;font-weight:700'>{td.label}</div>"
            f"<div style='font-size:42px;font-weight:800;line-height:1.1'>"
            f"{bs.score:.1f}<span style='font-size:18px'>/10</span></div>"
            f"<div style='font-size:14px'>{bs.suggestion}</div>"
            f"</div>"
            f"<div style='font-size:12px;line-height:1.7;"
            f"border-left:1px solid rgba(255,255,255,0.3);padding-left:20px'>"
            f"Price: {td.current_price:,.2f}<br>"
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

    last_date = td.tail.index[-1]
    fig.add_trace(
        go.Scatter(
            x=[last_date],
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
            textposition="top left",
            textfont=dict(size=10, color="darkorange"),
            legendgroup=f"score_latest_{col}",
            showlegend=show_legend,
        ),
        row=row,
        col=col,
    )

    fig.update_yaxes(title_text="Score", range=[0, 10], row=row, col=col)


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


# ── Backtest chart ──────────────────────────────────────────────────


def generate_backtest_chart(
    comparisons: Sequence[BacktestComparison],
    portfolio_comparisons: Sequence[PortfolioComparison] | None = None,
    output_path: str = BACKTEST_OUTPUT_FILE,
) -> str:
    """Render an interactive backtest dashboard and save it to *output_path*."""
    # Group comparisons by ticker label
    by_ticker: dict[str, list[BacktestComparison]] = {}
    for c in comparisons:
        by_ticker.setdefault(c.label, []).append(c)

    ticker_labels = list(by_ticker.keys())
    n_tickers = len(ticker_labels)

    has_portfolio = bool(portfolio_comparisons)
    n_equity_rows = n_tickers + (1 if has_portfolio else 0)
    n_invest_rows = n_tickers
    total_rows = n_equity_rows + n_invest_rows

    n_cols = 2

    subplot_titles: list[str] = []
    for label in ticker_labels:
        for c in sorted(by_ticker[label], key=lambda x: x.period):
            subplot_titles.append(f"{label} — {c.period} Equity Curve")
    if has_portfolio:
        for pc in sorted(portfolio_comparisons, key=lambda x: x.period):
            subplot_titles.append(f"Portfolio — {pc.period} Equity Curve")
    for label in ticker_labels:
        for c in sorted(by_ticker[label], key=lambda x: x.period):
            subplot_titles.append(f"{label} — {c.period} Monthly Investment")

    row_heights = [0.6 / n_equity_rows] * n_equity_rows + [0.4 / n_invest_rows] * n_invest_rows

    fig = make_subplots(
        rows=total_rows,
        cols=n_cols,
        shared_xaxes=False,
        row_heights=row_heights,
        vertical_spacing=0.04,
        subplot_titles=subplot_titles,
    )

    for row_idx, label in enumerate(ticker_labels, start=1):
        sorted_comps = sorted(by_ticker[label], key=lambda x: x.period)
        for col_idx, comp in enumerate(sorted_comps, start=1):
            show_legend = row_idx == 1 and col_idx == 1
            _add_equity_traces(fig, comp, row=row_idx, col=col_idx, show_legend=show_legend)

    if has_portfolio:
        port_row = n_tickers + 1
        sorted_ports = sorted(portfolio_comparisons, key=lambda x: x.period)
        for col_idx, pc in enumerate(sorted_ports, start=1):
            _add_portfolio_equity_traces(fig, pc, row=port_row, col=col_idx)

    for row_offset, label in enumerate(ticker_labels):
        invest_row = n_equity_rows + row_offset + 1
        sorted_comps = sorted(by_ticker[label], key=lambda x: x.period)
        for col_idx, comp in enumerate(sorted_comps, start=1):
            show_legend = row_offset == 0 and col_idx == 1
            _add_investment_traces(fig, comp, row=invest_row, col=col_idx, show_legend=show_legend)

    fig.update_layout(
        height=350 * total_rows,
        autosize=True,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(font=dict(size=9)),
        margin=dict(t=40, b=50, r=60),
    )

    header_html = _build_backtest_header(comparisons, portfolio_comparisons)
    chart_html = fig.to_html(include_plotlyjs=True, full_html=False)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(_wrap_html(header_html, chart_html))

    return output_path


# ── Backtest trace helpers ──────────────────────────────────────────

_FLAT_COLOR = "#1976D2"
_RAW_COLOR = "#F57C00"
_NORM_COLOR = "#388E3C"
_PORT_FLAT_COLOR = "#5C6BC0"
_PORT_SCORE_COLOR = "#EF5350"


def _add_equity_traces(
    fig: go.Figure,
    comp: BacktestComparison,
    row: int,
    col: int,
    show_legend: bool = False,
) -> None:
    """Add flat / raw / normalized equity curves for one ticker+period."""
    for result, name, color in [
        (comp.flat, "Flat DCA", _FLAT_COLOR),
        (comp.score_raw, "Score (raw)", _RAW_COLOR),
        (comp.score_normalized, "Score (norm)", _NORM_COLOR),
    ]:
        if result.equity_curve is not None:
            fig.add_trace(
                go.Scatter(
                    x=result.equity_curve.index,
                    y=result.equity_curve.values,
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=1.5),
                    legendgroup=name,
                    showlegend=show_legend,
                ),
                row=row,
                col=col,
            )
    fig.update_yaxes(title_text="₩", row=row, col=col)


def _add_portfolio_equity_traces(
    fig: go.Figure,
    pc: PortfolioComparison,
    row: int,
    col: int,
) -> None:
    """Add flat vs score-alloc equity curves for the portfolio."""
    show_legend = col == 1
    for result, name, color in [
        (pc.flat, "Flat Alloc", _PORT_FLAT_COLOR),
        (pc.score_alloc, "Score Alloc", _PORT_SCORE_COLOR),
    ]:
        if result.equity_curve is not None:
            fig.add_trace(
                go.Scatter(
                    x=result.equity_curve.index,
                    y=result.equity_curve.values,
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=1.5),
                    legendgroup=name,
                    showlegend=show_legend,
                ),
                row=row,
                col=col,
            )
    fig.update_yaxes(title_text="₩", row=row, col=col)


def _add_investment_traces(
    fig: go.Figure,
    comp: BacktestComparison,
    row: int,
    col: int,
    show_legend: bool = False,
) -> None:
    """Add monthly investment bar chart for flat vs score-raw."""
    for result, name, color in [
        (comp.flat, "Flat invest", _FLAT_COLOR),
        (comp.score_raw, "Score invest", _RAW_COLOR),
    ]:
        if result.monthly_investments is not None:
            fig.add_trace(
                go.Bar(
                    x=result.monthly_investments.index,
                    y=result.monthly_investments.values,
                    name=name,
                    marker_color=color,
                    opacity=0.6,
                    legendgroup=name + "_inv",
                    showlegend=show_legend,
                ),
                row=row,
                col=col,
            )
    fig.update_yaxes(title_text="₩/mo", row=row, col=col)


# ── Backtest header ────────────────────────────────────────────────


def _build_backtest_header(
    comparisons: Sequence[BacktestComparison],
    portfolio_comparisons: Sequence[PortfolioComparison] | None = None,
) -> str:
    """Build an HTML summary header for the backtest dashboard."""
    # Group by period, then render row by row
    by_period: dict[str, list[BacktestComparison]] = {}
    for comp in comparisons:
        by_period.setdefault(comp.period, []).append(comp)

    rows_html: list[str] = []
    period_order = sorted(by_period.keys(), key=lambda p: int(p.replace("y", "")))
    for period in period_order:
        cards: list[str] = []
        for comp in by_period[period]:
            flat = comp.flat
            norm = comp.score_normalized
            diff = norm.total_return_pct - flat.total_return_pct
            bg = "#388E3C" if diff > 0 else "#F44336" if diff < -1 else "#FF9800"

            cards.append(
                f"<div style='flex:1;background:{bg};color:#fff;border-radius:10px;"
                f"padding:14px 20px;margin:4px 6px;min-width:260px'>"
                f"<div style='font-size:16px;font-weight:700'>{comp.label} — {comp.period}</div>"
                f"<div style='font-size:11px;line-height:1.8;margin-top:6px'>"
                f"<b>Flat DCA:</b> {flat.total_return_pct:+.2f}% return, "
                f"{flat.max_drawdown_pct:.1f}% max DD<br>"
                f"<b>Score (norm):</b> {norm.total_return_pct:+.2f}% return, "
                f"{norm.max_drawdown_pct:.1f}% max DD<br>"
                f"<b>Edge:</b> {diff:+.2f}pp"
                f"</div></div>"
            )

        rows_html.append(
            f"<div style='display:flex;justify-content:center;"
            f"flex-wrap:wrap;margin:4px 8px'>"
            f"{''.join(cards)}</div>"
        )

    # Portfolio cards in a separate row
    if portfolio_comparisons:
        port_cards: list[str] = []
        for pc in sorted(portfolio_comparisons, key=lambda x: int(x.period.replace("y", ""))):
            flat_p = pc.flat
            score_p = pc.score_alloc
            diff_p = score_p.total_return_pct - flat_p.total_return_pct
            bg = "#1565C0" if diff_p > 0 else "#C62828"

            port_cards.append(
                f"<div style='flex:1;background:{bg};color:#fff;border-radius:10px;"
                f"padding:14px 20px;margin:4px 6px;min-width:260px'>"
                f"<div style='font-size:16px;font-weight:700'>Portfolio — {pc.period}</div>"
                f"<div style='font-size:11px;line-height:1.8;margin-top:6px'>"
                f"<b>Flat Alloc:</b> {flat_p.total_return_pct:+.2f}% return, "
                f"{flat_p.max_drawdown_pct:.1f}% max DD<br>"
                f"<b>Score Alloc:</b> {score_p.total_return_pct:+.2f}% return, "
                f"{score_p.max_drawdown_pct:.1f}% max DD<br>"
                f"<b>Edge:</b> {diff_p:+.2f}pp"
                f"</div></div>"
            )

        rows_html.append(
            f"<div style='display:flex;justify-content:center;"
            f"flex-wrap:wrap;margin:4px 8px'>"
            f"{''.join(port_cards)}</div>"
        )

    title = (
        "<div style='text-align:center;font-size:22px;font-weight:700;"
        "margin:16px 0 8px;color:#333'>"
        "FinAnalysis — Backtest: Flat DCA vs Score-based DCA</div>"
    )
    disclaimer = (
        "<div style='text-align:center;font-size:11px;color:#888;"
        "margin-top:6px'>⚠ Past performance does not guarantee future results. "
        "This is a simulation — not financial advice.</div>"
    )

    return f"{title}{''.join(rows_html)}{disclaimer}"
