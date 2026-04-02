"""Chart rendering for FinAnalysis.

Builds an interactive Plotly figure with price + moving-average panels
on top and RSI panels on the bottom, one column per ticker.  The result
is saved as a self-contained HTML file.
"""

from __future__ import annotations

from typing import Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import MA_STYLES, OUTPUT_FILE
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

    fig = make_subplots(
        rows=2,
        cols=n_cols,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.06,
        subplot_titles=subplot_titles,
    )

    for col, td in enumerate(tickers, start=1):
        _add_price_traces(fig, td, row=1, col=col)
        _add_rsi_traces(fig, td, row=2, col=col)

    fig.update_layout(
        height=700,
        autosize=True,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(font=dict(size=9)),
        margin=dict(t=40, b=30),
    )

    fig.write_html(output_path, include_plotlyjs=True)
    return output_path


# ── Private helpers ─────────────────────────────────────────────────


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

    # Overbought / oversold reference lines
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
