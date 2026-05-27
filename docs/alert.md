# Score Alert

Automated email notifications when Korean ticker scores cross the buy-in threshold.

## How It Works

The script runs every 15 minutes during KRX market hours (09:00–15:30 KST, weekdays). When any Korean ticker score reaches 6.5+ (Increase buy-in level), it sends an email with:

- Score summary for all KR tickers (highlighted if above threshold)
- Recommended buy-in amounts per ticker
- Score breakdown (MA, RSI, drawdown) for triggered tickers
- Portfolio allocation recommendation

### Email Frequency

- **First alert**: Sent once per day when any score first crosses 6.5
- **Repeat alerts**: Only sent again same day if a score rises 0.3+ points from the last emailed score (indicating the opportunity is getting better)

## Setup

### 1. Outlook

Ensure Microsoft Outlook is installed and configured with a mail account on this machine. The script sends email via the Outlook COM interface (pywin32) using the default account.

### 2. Configure `.env`

Add the recipient address to your `.env` file:

```
ALERT_EMAIL_TO=your_email@gmail.com
```

### 3. Test manually

```bash
uv run python -m src.alert_check --force
```

The `--force` flag skips the market hours check so you can test anytime.

### 4. Windows Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)
2. Create a new task:
   - **Trigger**: Repeat every 15 minutes, starting at 09:00, for 7 hours (covers 09:00–15:30)
   - **Action**: Start a program → `alert.bat` (browse to the project root)
   - **Start in**: Set to the project root directory (e.g., `C:\Users\you\Documents\FinAnalysis`)
   - **Conditions**: Only start if on AC power (optional), wake to run (optional)
3. Or simply double-click `alert.bat` to run manually

## Configuration

All settings are in `src/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ALERT_THRESHOLD` | 6.5 | Score that triggers an alert |
| `ALERT_SCORE_DELTA` | 0.3 | Score increase needed for repeat alert same day |
| `ALERT_EMAIL_TO` | (from .env) | Recipient email |
| `ALERT_STATE_PATH` | `log/alert_state.json` | State file location |

## Logs

- Location: `log/alert_YYYYMMDD.log`
- Retention: 7 days (older logs auto-deleted on each run)
- Contains: timestamps, scores fetched, email send status, errors

## Files

| File | Purpose |
|------|---------|
| `src/alert_check.py` | Main script (run via `python -m src.alert_check`) |
| `src/templates/alert_email.html` | Jinja2 email template |
| `alert.bat` | Windows batch file for Task Scheduler |
| `log/alert_state.json` | Tracks last email time and scores |
