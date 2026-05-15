# Plan: Score Alert Email Notification

**Goal**: Create a scheduled script that checks ticker scores every 2 hours during market hours and sends an email alert when any score crosses the threshold.

## Parameters

- Threshold: 6.5 (Increase buy-in level)
- Schedule: every 2 hours during 09:00–15:30 KST (market hours)
- Email cap: max 1 per day, unless score rises 0.3+ from last emailed score
- SMTP: Gmail with App Password
- State: JSON file to track last email timestamp and score

---

## Tasks

### Task 1: Add alert config to `src/config.py` and `.env.example` ✅

- **Files**: `src/config.py`, `.env.example`
- **What**: Add `ALERT_THRESHOLD`, `ALERT_SCORE_DELTA`, `ALERT_EMAIL_TO`, `ALERT_EMAIL_FROM`, `SMTP_PASSWORD` settings
- **Verify**: Import works

### Task 2: Create `scripts/alert_check.py` ✅

- **Files**: `scripts/alert_check.py`
- **What**:
  - Check if within market hours (09:00–15:30 KST weekdays)
  - Fetch latest scores for KR tickers (reuse `fetch_ticker`)
  - Check threshold + cooldown logic
  - Send email via Gmail SMTP if triggered
  - Update state file (`data/alert_state.json`)
- **Verify**: Script runs without error, sends test email

### Task 3: Document setup ✅

- **Files**: `README.md` or `docs/` (brief section)
- **What**: How to set up Gmail App Password, configure `.env`, set up Windows Task Scheduler
- **Verify**: Instructions are clear

---

## Email Logic

```
1. Is it a weekday and between 09:00–15:30 KST?
   NO → exit
   YES ↓
2. Fetch scores for TICKERS_KR
3. Any score ≥ 6.5?
   NO → exit
   YES ↓
4. Load state file (last_email_date, last_email_scores)
5. Was an email sent today?
   NO → send email, save state
   YES ↓
6. Is any current score ≥ (its last_emailed_score + 0.3)?
   NO → exit
   YES → send email, update state
```

## State File Format (`data/alert_state.json`)

```json
{
  "last_email_time": "2026-05-15T10:30:00",
  "scores": {
    "TIGER S&P500": 7.2,
    "TIGER 나스닥100": 6.8,
    "금현물 (KRX)": 5.1
  }
}
```

---

## Email Format

The email should be HTML-formatted for readability. Subject line includes the highest score for quick scanning in inbox.

### Subject

First email of the day:
```
[FinAnalysis] Buy signal: TIGER S&P500, TIGER 나스닥100
```

Subsequent emails (score rose 0.3+):
```
[FinAnalysis] Score rising: TIGER S&P500 ↑ (was 6.8 → now 7.2)
```

Only tickers above threshold are listed in the subject.

### Body (HTML)

```
┌─────────────────────────────────────────────────────────┐
│  FinAnalysis — Score Alert                              │
│  2026-05-15 10:30 KST                                  │
│                                                         │
│  ⚠ Score update: TIGER S&P500 rose from 6.8 to 7.2     │  ← only on 2nd/3rd email
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Ticker            Score    Suggestion     Price        │
│  ─────────────────────────────────────────────────      │
│  ★ TIGER S&P500    7.2/10   Increase      24,620 KRW   │  ← ★ = above threshold
│  ★ TIGER 나스닥100  6.8/10   Increase      18,450 KRW   │
│    금현물 (KRX)     5.1/10   Regular      152,790 KRW   │
│                                                         │
│  ── Recommended Buy-in ──                               │
│                                                         │
│  ★ TIGER S&P500:     ₩750,000  (1.50x, Increase)       │
│  ★ TIGER 나스닥100:   ₩750,000  (1.50x, Increase)       │
│    금현물 (KRX):      ₩500,000  (1.00x, Regular)        │
│                                                         │
│  ── Score Breakdown (above threshold only) ──           │
│                                                         │
│  TIGER S&P500 (7.2/10):                                │
│    MA:  5.2/7.0  (below MA100, MA200)                  │
│    RSI: 0.75/1.5 (RSI: 42.3)                           │
│    DD:  1.25/1.5 (DD: -20.8%)                          │
│                                                         │
│  TIGER 나스닥100 (6.8/10):                              │
│    MA:  5.8/7.0  (below MA50, MA100, MA200)            │
│    RSI: 0.0/1.5  (RSI: 52.1)                           │
│    DD:  1.0/1.5  (DD: -10.0%)                          │
│                                                         │
│  ── Allocation Recommendation ──                        │
│                                                         │
│  TIGER S&P500      58.2%   →  ₩582,000                 │
│  TIGER 나스닥100    12.3%   →  ₩123,000                 │
│  금현물 (KRX)       29.5%   →  ₩295,000                 │
│  Monthly Budget: ₩1,000,000                             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ⚠ Technical indicator score only — not financial       │
│  advice. Review the dashboard before acting.            │
└─────────────────────────────────────────────────────────┘
```

### Content Rules

- **Subject**: No scores in subject. On repeat emails, indicate why (score rising + which ticker)
- **Trigger reason**: On 2nd/3rd emails, show a banner explaining what changed (e.g., "TIGER S&P500 rose from 6.8 to 7.2")
- **★ highlight**: Tickers above threshold are marked with ★ and shown in bold/highlighted row
- **Recommended Buy-in**: Per-ticker buy-in amount = `BASE_AMOUNT × multiplier` with the multiplier and suggestion label shown. This tells you exactly how much to invest in each ticker.
- **All KR tickers** are shown in the summary table (not just those above threshold) for context
- **Score breakdown** is only shown for tickers above the threshold (the actionable ones)
- **Allocation** is always included so you know how to split the budget if investing the full monthly amount
- **Disclaimer** at the bottom
- Use a clean HTML table with inline styles (no external CSS — email clients strip it)
