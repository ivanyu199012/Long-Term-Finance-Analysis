# Product Overview

FinAnalysis is a self-contained technical-analysis dashboard and DCA (Dollar-Cost Averaging) scoring system targeting S&P 500, NASDAQ 100, and Gold across international and Korean markets.

## What It Does

- Generates interactive HTML dashboards with MA, RSI, and buy-in score panels
- Computes a 0–10 buy-in score from moving-average positioning, RSI, and drawdown
- Provides portfolio allocation recommendations with dynamic score-based weighting
- Runs backtests comparing flat DCA vs score-based DCA over 5y and 10y periods
- Supports multiple data sources: Yahoo Finance (international), pykrx (Korean ETFs), KRX Gold API

## Key Concepts

- **Buy-in Score**: A 0–10 composite score (MA component up to 7 pts, RSI up to 1.5 pts, drawdown up to 1.5 pts) that maps to investment multipliers (0.25x–2.25x)
- **Two market groups**: International (USD, reference) and Korean (KRW, investment portfolio)
- **Score-based allocation**: Monthly budget is distributed across assets using base weights adjusted by each asset's score multiplier, with minimum weight floors enforced

## Target Users

Personal finance tool for the developer — runs locally, outputs static HTML, no server component.
