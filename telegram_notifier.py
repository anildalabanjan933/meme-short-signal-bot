# =========================================================
# telegram_notifier.py
# Sends signal alerts to Telegram
#
# Handles:
#   - Original reversal bot signals  (send_signal_alert)
#   - PnF trendline break signals    (send_pnf_signal)
#   - Bot startup test message       (send_test_message)
# =========================================================

import requests
from datetime import datetime, timezone
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# =========================================================
# CORE SENDER
# =========================================================

def send_telegram_message(message: str) -> bool:
    """
    Send a plain text or HTML message to Telegram bot.
    Retries once on failure.
    Returns True if sent successfully, False otherwise.
    """
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML"
    }

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            data     = response.json()
            if data.get("ok"):
                print("[TELEGRAM] Message sent successfully")
                return True
            else:
                print(f"[TELEGRAM ERROR] Attempt {attempt + 1}: {data}")
        except Exception as e:
            print(f"[TELEGRAM ERROR] Attempt {attempt + 1}: {e}")

    return False


# =========================================================
# STARTUP TEST MESSAGE
# =========================================================

def send_test_message() -> None:
    """
    Send a startup confirmation message when bot launches.
    Called from main.py on startup.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = (
        "✅ <b>PnF Signal Bot Started</b>\n"
        f"{'=' * 32}\n"
        f"<b>Time :</b> {now_utc}\n"
        f"{'=' * 32}\n"
        "Bot is running and scanning for signals.\n"
        "Waiting for PnF Trendline Break setups..."
    )
    send_telegram_message(message)


# =========================================================
# ORIGINAL REVERSAL BOT SIGNAL
# =========================================================

def _format_funding_label(funding_rate) -> str:
    """
    Format funding rate with direction label.
    Positive = longs paying shorts (good for short bias)
    Negative = shorts paying longs (bad for short bias)
    """
    if funding_rate is None:
        return "N/A"

    pct   = round(funding_rate * 100, 4)
    sign  = "+" if pct >= 0 else ""
    label = "Longs Paying ✅" if pct >= 0 else "Shorts Paying ⚠️"

    return f"{sign}{pct}% ({label})"


def format_signal_message(signal: dict) -> str:
    """
    Format original reversal signal dict into Telegram message.

    Expected signal dict keys:
        symbol, pattern, resolution, pump_pct,
        entry, stop_loss, tp1, tp2, tp3,
        volume, avg_volume,
        funding_rate, oi_rising, verdict
    """
    funding_str = _format_funding_label(signal.get("funding_rate"))
    now_utc     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # OI line
    oi_line = "OI Rising ✅" if signal.get("oi_rising") else "OI Weak ⚠️"

    # Verdict line
    verdict      = signal.get("verdict", "AVOID SHORT")
    verdict_line = "✅ GOOD FOR SHORT" if verdict == "GOOD FOR SHORT" else "⚠️ AVOID SHORT"

    message = (
        "🔴 <b>SHORT SIGNAL - MEME COIN REVERSAL</b>\n"
        f"{'=' * 32}\n"
        f"<b>Coin      :</b> {signal.get('symbol', 'N/A')}\n"
        f"<b>Pattern   :</b> {signal.get('pattern', 'N/A')} ({signal.get('resolution', '5m')})\n"
        f"<b>48H Pump  :</b> +{signal.get('pump_pct', 0)}%\n"
        f"{'=' * 32}\n"
        f"<b>Entry     :</b> {signal.get('entry', 'N/A')}\n"
        f"<b>Stop Loss :</b> {signal.get('stop_loss', 'N/A')} (+5%)\n"
        f"{'=' * 32}\n"
        f"<b>TP1 (-30%):</b> {signal.get('tp1', 'N/A')}\n"
        f"<b>TP2 (-50%):</b> {signal.get('tp2', 'N/A')}\n"
        f"<b>TP3 (-70%):</b> {signal.get('tp3', 'N/A')}\n"
        f"{'=' * 32}\n"
        f"<b>Volume    :</b> {signal.get('volume', 'N/A')}\n"
        f"<b>Avg Vol   :</b> {signal.get('avg_volume', 'N/A')}\n"
        f"{'=' * 32}\n"
        f"<b>Funding   :</b>\n{funding_str}\n"
        "\n"
        f"<b>OI        :</b>\n{oi_line}\n"
        f"{'=' * 32}\n"
        f"<b>Verdict   :</b>\n{verdict_line}\n"
        f"{'=' * 32}\n"
        f"<b>Time      :</b> {now_utc}\n"
        f"{'=' * 32}\n"
        "<b>Signal only. Do your own analysis before trading.</b>"
    )
    return message


def send_signal_alert(signal: dict) -> None:
    """
    Format and send original reversal signal alert to Telegram.
    Called from main.py PART 1 loop.
    """
    message = format_signal_message(signal)
    send_telegram_message(message)


# =========================================================
# PnF TRENDLINE BREAK SIGNAL
# =========================================================

def format_pnf_signal_message(signal: dict) -> str:
    """
    Format PnF trendline break signal into Telegram message.

    Expected signal dict keys (from pnf_signal_checker.py):
        symbol, pattern, pump_pct, pump_days,
        entry, stop_loss, tp1, tp2, tp3,
        box_size_atr, exhaustion_type, trendline_break,
        volume, avg_volume,
        funding, oi_rising, verdict
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Pump line — show actual days window found, not hardcoded 48H
    pump_pct  = signal.get("pump_pct", 0)
    pump_days = signal.get("pump_days", 1)
    pump_line = f"+{pump_pct}% ({pump_days}d)"

    # Funding line with icon
    funding = signal.get("funding", "Neutral")
    funding_icons = {
        "Longs Paying":  "Longs Paying ✅",
        "Shorts Paying": "Shorts Paying ⚠️",
        "Neutral":       "Neutral"
    }
    funding_line = funding_icons.get(funding, funding)

    # OI line with icon
    oi_line = "OI Rising ✅" if signal.get("oi_rising") else "OI Weak ⚠️"

    # Verdict line with icon
    verdict      = signal.get("verdict", "AVOID SHORT")
    verdict_line = (
        "✅ GOOD FOR SHORT"
        if verdict == "GOOD FOR SHORT"
        else "⚠️ AVOID SHORT"
    )

    # Exhaustion label
    exhaustion = signal.get("exhaustion_type", "None")

    # Trendline break label
    trendline_label = "Confirmed" if signal.get("trendline_break") else "Not Confirmed"

    message = (
        "🔴 <b>SHORT SIGNAL - PnF TRENDLINE BREAK</b>\n"
        f"{'=' * 32}\n"
        f"<b>Coin      :</b> {signal.get('symbol', 'N/A')}\n"
        f"<b>Pattern   :</b> {signal.get('pattern', 'N/A')}\n"
        f"<b>Timeframe :</b> 5m\n"
        f"<b>Pump      :</b> {pump_line}\n"
        f"{'=' * 32}\n"
        f"<b>Entry     :</b> {signal.get('entry', 'N/A')}\n"
        f"<b>Stop Loss :</b> {signal.get('stop_loss', 'N/A')} (+5%)\n"
        f"{'=' * 32}\n"
        f"<b>TP1 (-30%):</b> {signal.get('tp1', 'N/A')}\n"
        f"<b>TP2 (-50%):</b> {signal.get('tp2', 'N/A')}\n"
        f"<b>TP3 (-70%):</b> {signal.get('tp3', 'N/A')}\n"
        f"{'=' * 32}\n"
        "<b>PnF Structure</b>\n"
        f"<b>Box Size (ATR14) :</b> {signal.get('box_size_atr', 'N/A')}\n"
        f"<b>Exhaustion       :</b> {exhaustion}\n"
        f"<b>Trendline Break  :</b> {trendline_label}\n"
        f"{'=' * 32}\n"
        f"<b>Volume    :</b> {signal.get('volume', 'N/A')}\n"
        f"<b>Avg Vol   :</b> {signal.get('avg_volume', 'N/A')}\n"
        f"{'=' * 32}\n"
        f"<b>Funding   :</b>\n{funding_line}\n"
        "\n"
        f"<b>OI        :</b>\n{oi_line}\n"
        f"{'=' * 32}\n"
        f"<b>Verdict   :</b>\n{verdict_line}\n"
        f"{'=' * 32}\n"
        f"<b>Time      :</b> {now_utc}\n"
        f"{'=' * 32}\n"
        "<b>Signal only. Do your own analysis before trading.</b>"
    )
    return message


def send_pnf_signal(signal: dict) -> None:
    """
    Format and send PnF trendline break signal alert to Telegram.
    Called from main.py PART 2 loop.
    """
    message = format_pnf_signal_message(signal)
    send_telegram_message(message)
