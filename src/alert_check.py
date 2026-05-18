"""FinAnalysis — Score Alert Check.

Scheduled script that checks Korean ticker scores and sends an email
alert when any score crosses the threshold. Designed to run every 2 hours
during KRX market hours (09:00–15:30 KST) via Windows Task Scheduler.

Usage:
    uv run python -m src.alert_check            # normal mode
    uv run python -m src.alert_check --force    # skip market hours check
    uv run python -m src.alert_check --debug    # skip all checks, always send email
"""

from __future__ import annotations

import json
import logging
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from src.allocation import compute_allocation
from src.config import (
    ALERT_AGGRESSIVE_DELTA,
    ALERT_AGGRESSIVE_THRESHOLD,
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
    ALERT_SCORE_DELTA,
    ALERT_SMTP_PASSWORD,
    ALERT_STATE_PATH,
    ALERT_THRESHOLD,
    BASE_AMOUNT,
    MONTHLY_BUDGET,
    PROJECT_ROOT,
    TICKERS_KR,
)
from src.fetchers import fetch_ticker
from src.indicators import score_to_label, score_to_multiplier
from src.models import TickerData

KST = ZoneInfo("Asia/Seoul")
_LOG_DIR = PROJECT_ROOT / "log"
_LOG_RETENTION_DAYS = 7

# ── Jinja2 environment ──────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=False)

# ── Logging setup ───────────────────────────────────────────────────

_LOG_DIR.mkdir(exist_ok=True)
_log_file = _LOG_DIR / f"alert_{datetime.now(KST).strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("alert_check")


def main() -> None:
    """Run the alert check."""
    force = "--force" in sys.argv
    debug = "--debug" in sys.argv
    now = datetime.now(KST)

    logger.info("=" * 50)
    logger.info("Alert check started%s", " (DEBUG MODE)" if debug else "")
    _cleanup_old_logs()

    # Step 1: Check market hours (skip in debug/force mode)
    if not force and not debug and not _is_market_hours(now):
        logger.info("Outside market hours (%s). Exiting.", now.strftime("%H:%M"))
        return

    # Validate email config
    if not ALERT_EMAIL_TO or not ALERT_EMAIL_FROM or not ALERT_SMTP_PASSWORD:
        logger.error("Email settings not configured. Set ALERT_EMAIL_TO, ALERT_EMAIL_FROM, ALERT_SMTP_PASSWORD in .env")
        sys.exit(1)

    # Step 2: Fetch scores
    logger.info("Fetching Korean ticker scores...")
    tickers: list[TickerData] = []
    for t in TICKERS_KR:
        try:
            td = fetch_ticker(**t)
            tickers.append(td)
            logger.info("  ✓ %s: %.1f/10", td.label, td.buy_score.score)
        except Exception as e:
            logger.warning("  ✗ %s: %s", t["label"], e)

    if not tickers:
        logger.error("No tickers fetched successfully.")
        sys.exit(1)

    # Step 3: Check threshold (skip in debug mode — always send)
    triggered = [td for td in tickers if td.buy_score.score >= ALERT_THRESHOLD]
    if not debug and not triggered:
        logger.info("No scores above threshold (%.1f). Exiting.", ALERT_THRESHOLD)
        return
    if debug and not triggered:
        triggered = tickers  # In debug mode, treat all as triggered

    logger.info("%d ticker(s) above threshold!", len(triggered))

    # Step 4: Cooldown check (skip in debug mode — always send)
    state = _load_state()
    is_repeat = False
    score_changes: dict[str, tuple[float, float]] = {}

    if not debug and state and _is_same_day(state["last_email_time"], now):
        any_rose = False
        for td in triggered:
            old_score = state["scores"].get(td.label, 0.0)
            new_score = td.buy_score.score
            # Aggressive zone (≥8.0): tighter delta of 0.1
            # Normal zone (≥6.5): standard delta of 0.3
            if new_score >= ALERT_AGGRESSIVE_THRESHOLD:
                delta = ALERT_AGGRESSIVE_DELTA
            else:
                delta = ALERT_SCORE_DELTA
            if new_score >= old_score + delta:
                any_rose = True
                score_changes[td.label] = (old_score, new_score)
        if not any_rose:
            logger.info("Already sent today and no significant score increase. Exiting.")
            return
        is_repeat = True
    else:
        for td in triggered:
            old_score = state["scores"].get(td.label, 0.0) if state else 0.0
            score_changes[td.label] = (old_score, td.buy_score.score)

    # Step 5: Compute allocation
    allocations = compute_allocation(tickers, ticker_configs=TICKERS_KR)

    # Step 6: Send email
    logger.info("Sending alert email...")
    subject = _build_subject(triggered, is_repeat, score_changes)
    body = _render_email(tickers, triggered, allocations, is_repeat, score_changes, now)
    try:
        _send_email(subject, body)
        logger.info("Email sent to %s", ALERT_EMAIL_TO)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        sys.exit(1)

    # Step 7: Save state
    _save_state(now, {td.label: td.buy_score.score for td in tickers})
    logger.info("Done.")


# ── Helpers ─────────────────────────────────────────────────────────


def _is_market_hours(now: datetime) -> bool:
    """Check if within KRX market hours (weekday 09:00–15:30 KST)."""
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def _cleanup_old_logs() -> None:
    """Remove log files older than _LOG_RETENTION_DAYS."""
    cutoff = datetime.now() - timedelta(days=_LOG_RETENTION_DAYS)
    for log_file in _LOG_DIR.glob("alert_*.log"):
        try:
            date_str = log_file.stem.replace("alert_", "")
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date < cutoff:
                log_file.unlink()
                logger.info("Removed old log: %s", log_file.name)
        except (ValueError, OSError):
            pass


def _load_state() -> dict | None:
    """Load alert state from JSON file."""
    if not ALERT_STATE_PATH.exists():
        return None
    try:
        with open(ALERT_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_state(now: datetime, scores: dict[str, float]) -> None:
    """Save alert state to JSON file."""
    state = {"last_email_time": now.isoformat(), "scores": scores}
    ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERT_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _is_same_day(last_time_str: str, now: datetime) -> bool:
    """Check if last_time_str is the same calendar day as now (KST)."""
    try:
        last = datetime.fromisoformat(last_time_str)
        if last.tzinfo is None:
            last = last.replace(tzinfo=KST)
        return last.date() == now.date()
    except (ValueError, TypeError):
        return False


# ── Email ───────────────────────────────────────────────────────────


def _build_subject(
    triggered: list[TickerData],
    is_repeat: bool,
    score_changes: dict[str, tuple[float, float]],
) -> str:
    """Build email subject line."""
    if is_repeat:
        parts = [f"{label} ↑ (was {old:.1f} → now {new:.1f})" for label, (old, new) in score_changes.items()]
        return f"[FinAnalysis] Score rising: {', '.join(parts)}"
    else:
        names = ", ".join(td.label for td in triggered)
        return f"[FinAnalysis] Buy signal: {names}"


def _render_email(
    all_tickers: list[TickerData],
    triggered: list[TickerData],
    allocations,
    is_repeat: bool,
    score_changes: dict[str, tuple[float, float]],
    now: datetime,
) -> str:
    """Render HTML email body using Jinja2 template."""
    triggered_labels = {td.label for td in triggered}
    template = _env.get_template("alert_email.html")
    return template.render(
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        is_repeat=is_repeat,
        score_changes=score_changes,
        all_tickers=all_tickers,
        triggered_labels=triggered_labels,
        triggered=triggered,
        allocations=allocations,
        suggestion_label=score_to_label,
        score_to_multiplier=score_to_multiplier,
        base_amount=BASE_AMOUNT,
        monthly_budget=MONTHLY_BUDGET,
    )


def _send_email(subject: str, html_body: str) -> None:
    """Send HTML email via Gmail SMTP_SSL (port 465)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ALERT_EMAIL_TO

    plain = f"{subject}\n\nPlease view this email in an HTML-capable client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(ALERT_EMAIL_FROM, ALERT_SMTP_PASSWORD)
        server.sendmail(ALERT_EMAIL_FROM, ALERT_EMAIL_TO, msg.as_string())


if __name__ == "__main__":
    main()
