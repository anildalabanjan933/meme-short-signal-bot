# =========================================================
# TELEGRAM NOTIFIER - Sends signal alerts to Telegram
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
    Format and send signal alert to Telegram.
    """
    message = format_signal_message(signal)
    send_telegram_message(message)
