import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------------------------
# 1. Download S&P 500 data
# ------------------------------------
sp500 = yf.download("^GSPC", period="1y", auto_adjust=True)
sp500.columns = sp500.columns.get_level_values(0)

current_sp = sp500["Close"].iloc[-1]
ma50_sp = sp500["Close"].rolling(window=50).mean().iloc[-1]
ma100_sp = sp500["Close"].rolling(window=100).mean().iloc[-1]
ma200_sp = sp500["Close"].rolling(window=200).mean().iloc[-1]

# Percentage differences
sp_pct50 = (current_sp - ma50_sp) / ma50_sp * 100
sp_pct100 = (current_sp - ma100_sp) / ma100_sp * 100
sp_pct200 = (current_sp - ma200_sp) / ma200_sp * 100

# ------------------------------------
# 2. Download Gold futures data
# ------------------------------------
gold = yf.download("GC=F", period="1y", auto_adjust=True)
gold.columns = gold.columns.get_level_values(0)

current_gold = gold["Close"].iloc[-1]
ma50_gold = gold["Close"].rolling(window=50).mean().iloc[-1]
ma100_gold = gold["Close"].rolling(window=100).mean().iloc[-1]
ma200_gold = gold["Close"].rolling(window=200).mean().iloc[-1]

# Percentage differences
gold_pct50 = (current_gold - ma50_gold) / ma50_gold * 100
gold_pct100 = (current_gold - ma100_gold) / ma100_gold * 100
gold_pct200 = (current_gold - ma200_gold) / ma200_gold * 100

# ------------------------------------
# 3. RSI calculation helper
# ------------------------------------
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ------------------------------------
# 4. Charts: Price + MA lines on top, RSI on bottom
# ------------------------------------
sp500_100 = sp500.tail(100)
gold_100 = gold.tail(100)

sp500_rsi = calc_rsi(sp500["Close"]).tail(100)
gold_rsi = calc_rsi(gold["Close"]).tail(100)

fig, axes = plt.subplots(2, 2, figsize=(16, 10),
                         height_ratios=[3, 1], sharex="col")

def plot_price(ax, df, title, ma50, ma100, ma200, pct50, pct100, pct200):
    ax.plot(df.index, df["Close"], label="Close", color="black", linewidth=1.5)
    for ma_val, ma_name, pct, ls, clr in [
        (ma50, "MA50", pct50, "--", "green"),
        (ma100, "MA100", pct100, "-.", "blue"),
        (ma200, "MA200", pct200, ":", "red"),
    ]:
        ax.axhline(y=ma_val, color=clr, linestyle=ls, linewidth=1.2,
                   label=f"{ma_name}: {ma_val:,.2f} ({pct:+.2f}%)")
    ax.set_title(title)
    ax.set_ylabel("Price")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(linestyle="--", alpha=0.4)

def plot_rsi(ax, rsi_series):
    ax.plot(rsi_series.index, rsi_series, color="purple", linewidth=1.2)
    ax.axhline(y=70, color="red", linestyle="--", linewidth=0.8, label="Overbought (70)")
    ax.axhline(y=30, color="green", linestyle="--", linewidth=0.8, label="Oversold (30)")
    ax.fill_between(rsi_series.index, 30, rsi_series.where(rsi_series < 30),
                    color="green", alpha=0.3)
    ax.fill_between(rsi_series.index, 70, rsi_series.where(rsi_series > 70),
                    color="red", alpha=0.3)
    ax.set_ylabel("RSI")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=30)

# S&P 500
plot_price(axes[0, 0], sp500_100, "S&P 500 — 100 Day View",
           ma50_sp, ma100_sp, ma200_sp, sp_pct50, sp_pct100, sp_pct200)
plot_rsi(axes[1, 0], sp500_rsi)

# Gold
plot_price(axes[0, 1], gold_100, "Gold — 100 Day View",
           ma50_gold, ma100_gold, ma200_gold, gold_pct50, gold_pct100, gold_pct200)
plot_rsi(axes[1, 1], gold_rsi)

plt.tight_layout()
plt.savefig("combined_chart.png")
plt.close()

import subprocess, sys
subprocess.Popen(["start", "", "combined_chart.png"], shell=True)

print("Combined chart saved: combined_chart.png")