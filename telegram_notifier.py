# =========================================================
# TELEGRAM NOTIFIER - Sends signal alerts to Telegram
# Handles both:
#   - Original reversal bot signals  (send_signal_alert)
#   - New PnF trendline break signals (send_pnf_signal)
# =========================================================

import requests
from datetime import datetime, timezone
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(message):
    """
    Send a plain text or HTML message to Telegram bot.
    """
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data     = response.json()
        if data.get("ok"):
            print(f"[TELEGRAM] Message sent successfully")
        else:
            print(f"[TELEGRAM ERROR] {data}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


# =========================================================
# ORIGINAL REVERSAL BOT — unchanged
# =========================================================

def _format_funding_label(funding_rate):
    """
    Format funding rate with direction label.
    Positive = longs paying shorts (good for short bias)
    Negative = shorts paying longs (bad for short bias)
    """
    if funding_rate is None:
        return "N/A"

    pct   = round(funding_rate * 100, 4)
    sign  = "+" if pct >= 0 else ""
    label = "longs paying" if pct >= 0 else "shorts paying"

    return f"{sign}{pct}% ({label})"


def format_signal_message(signal):
    """
    Format the signal dict into a clean Telegram message
    matching the roadmap format exactly.
    """
    funding_str  = _format_funding_label(signal.get("funding_rate"))
    now_utc      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    message = (
        f"<b>SHORT SIGNAL - MEME COIN REVERSAL</b>\n"
        f"{'=' * 32}\n"
        f"<b>Coin     :</b> {signal['symbol']}\n"
        f"<b>Pattern  :</b> {signal['pattern']} ({signal['resolution']})\n"
        f"<b>48H Pump :</b> +{signal['pump_pct']}%\n"
        f"{'=' * 32}\n"
        f"<b>Entry    :</b> {signal['entry_price']}\n"
        f"<b>Stop Loss:</b> {signal['sl']}\n"
        f"{'=' * 32}\n"
        f"<b>TP1 (-{signal.get('tp1_pct', 30)}%):</b> {signal['tp1']}\n"
        f"<b>TP2 (-{signal.get('tp2_pct', 50)}%):</b> {signal['tp2']}\n"
        f"<b>TP3 (-{signal.get('tp3_pct', 70)}%):</b> {signal['tp3']}\n"
        f"{'=' * 32}\n"
        f"<b>Volume   :</b> {signal['current_volume']}\n"
        f"<b>Avg Vol  :</b> {signal['avg_volume']}\n"
        f"<b>Funding  :</b> {funding_str}\n"
        f"{'=' * 32}\n"
        f"<b>Time     :</b> {now_utc}\n"
        f"{'=' * 32}\n"
        f"<b>Signal only. Do your own analysis before trading.</b>"
    )
    return message


def send_signal_alert(signal):
    """
    Format and send original reversal signal alert to Telegram.
    """
    message = format_signal_message(signal)
    send_telegram_message(message)


# =========================================================
# PnF TRENDLINE BREAK BOT — new
# =========================================================

def format_pnf_signal_message(signal: dict) -> str:
    """
    Format PnF trendline break signal into Telegram message.
    Exhaustion = informational label only (not a hard gate).
    Funding    = informational, affects verdict only.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Funding line with icon
    funding      = signal.get("funding", "Neutral")
    funding_icons = {
        "Longs Paying":  "Longs Paying \u2705",
        "Shorts Paying": "Shorts Paying \u26a0\ufe0f",
        "Neutral":       "Neutral"
    }
    funding_line = funding_icons.get(funding, funding)

    # OI line with icon
    oi_line = "OI Rising \u2705" if signal.get("oi_rising") else "OI Weak \u26a0\ufe0f"

    # Verdict line with icon
    verdict      = signal.get("verdict", "AVOID SHORT")
    verdict_line = (
        "\u2705 GOOD FOR SHORT"
        if verdict == "GOOD FOR SHORT"
        else "\u26a0\ufe0f AVOID SHORT"
    )

    # Exhaustion label
    exhaustion = signal.get("exhaustion_type", "None")

    message = (
        f"\U0001f534 <b>SHORT SIGNAL - PnF TRENDLINE BREAK</b>\n"
        f"{'=' * 32}\n"
        f"<b>Coin      :</b> {signal['symbol']}\n"
        f"<b>Pattern   :</b> {signal['pattern']}\n"
        f"<b>Timeframe :</b> 5m\n"
        f"<b>48H Pump  :</b> +{signal['pump_pct']}%\n"
        f"{'=' * 32}\n"
        f"<b>Entry     :</b> {signal['entry']}\n"
        f"<b>Stop Loss :</b> {signal['stop_loss']} (+5%)\n"
        f"{'=' * 32}\n"
        f"<b>TP1 (-30%):</b> {signal['tp1']}\n"
        f"<b>TP2 (-50%):</b> {signal['tp2']}\n"
        f"<b>TP3 (-70%):</b> {signal['tp3']}\n"
        f"{'=' * 32}\n"
        f"<b>PnF Structure</b>\n"
        f"<b>Box Size (ATR14) :</b> {signal['box_size_atr']}\n"
        f"<b>Exhaustion       :</b> {exhaustion}\n"
        f"<b>Trendline Break  :</b> Confirmed\n"
        f"{'=' * 32}\n"
        f"<b>Volume    :</b> {signal['volume']}\n"
        f"<b>Avg Vol   :</b> {signal['avg_volume']}\n"
        f"{'=' * 32}\n"
        f"<b>Funding   :</b>\n{funding_line}\n"
        f"\n"
        f"<b>OI        :</b>\n{oi_line}\n"
        f"{'=' * 32}\n"
        f"<b>Verdict   :</b>\n{verdict_line}\n"
        f"{'=' * 32}\n"
        f"<b>Time      :</b> {now_utc}\n"
        f"{'=' * 32}\n"
        f"<b>Signal only. Do your own analysis before trading.</b>"
    )
    return message


def send_pnf_signal(signal: dict) -> None:
    """
    Format and send PnF trendline break signal alert to Telegram.
    Called from main.py PART 2 loop.
    """
    message = format_pnf_signal_message(signal)
    send_telegram_message(message)
