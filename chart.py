"""Chart rendering for FinAnalysis.

Builds a combined figure with price + moving-average panels on top and
RSI panels on the bottom, one column per ticker.
"""

from __future__ import annotations

from typing import Sequence

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from config import FIGURE_SIZE, HEIGHT_RATIOS, MA_STYLES, OUTPUT_FILE
from data import TickerData


def generate_chart(
    tickers: Sequence[TickerData],
    output_path: str = OUTPUT_FILE,
) -> str:
    """Render the combined chart and save it to *output_path*.

    Parameters
    ----------
    tickers:
        One :class:`TickerData` per column in the figure.
    output_path:
        File path for the saved PNG image.

    Returns
    -------
    str
        The path the image was written to.
    """
    n_cols = len(tickers)
    fig, axes = plt.subplots(
        2,
        n_cols,
        figsize=FIGURE_SIZE,
        height_ratios=HEIGHT_RATIOS,
        sharex="col",
        squeeze=False,
    )

    for col, td in enumerate(tickers):
        _plot_price(axes[0, col], td)
        _plot_rsi(axes[1, col], td)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig)
    return output_path


# ── Private helpers ─────────────────────────────────────────────────


def _plot_price(ax: plt.Axes, td: TickerData) -> None:
    """Draw the closing-price line and horizontal MA reference lines."""
    ax.plot(
        td.tail.index,
        td.tail["Close"],
        label="Close",
        color="black",
        linewidth=1.5,
    )

    for window, ma_value in td.moving_averages.items():
        style = MA_STYLES[window]
        pct = td.ma_pct_diffs[window]
        ax.axhline(
            y=ma_value,
            color=style.color,
            linestyle=style.linestyle,
            linewidth=1.2,
            label=f"MA{window}: {ma_value:,.2f} ({pct:+.2f}%)",
        )

    ax.set_title(f"{td.label} — {len(td.tail)} Day View")
    ax.set_ylabel("Price")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(linestyle="--", alpha=0.4)


def _plot_rsi(ax: plt.Axes, td: TickerData) -> None:
    """Draw the RSI oscillator with overbought / oversold shading."""
    rsi = td.rsi_tail

    ax.plot(rsi.index, rsi, color="purple", linewidth=1.2)
    ax.axhline(y=70, color="red", linestyle="--", linewidth=0.8, label="Overbought (70)")
    ax.axhline(y=30, color="green", linestyle="--", linewidth=0.8, label="Oversold (30)")

    ax.fill_between(
        rsi.index, 30, rsi.where(rsi < 30), color="green", alpha=0.3,
    )
    ax.fill_between(
        rsi.index, 70, rsi.where(rsi > 70), color="red", alpha=0.3,
    )

    ax.set_ylabel("RSI")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=30)
