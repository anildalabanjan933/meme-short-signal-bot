# =========================================================
# MAIN - Runs the signal scanner loop
# =========================================================

import time
import schedule
from datetime import datetime

from config import (
    SCAN_INTERVAL_MIN,
    ALERT_COOLDOWN_HRS,
    CANDLE_RESOLUTION,
    TP1_PCT,
    TP2_PCT,
    TP3_PCT
)
from delta_client import (
    get_all_meme_symbols,
    get_pump_candles,
    get_recent_candles,
    get_funding_rate
)
from signal_checker import run_signal_check
from telegram_notifier import send_signal_alert, send_telegram_message

# Track last alert time per symbol to enforce cooldown
last_alert_time = {}


def is_cooldown_active(symbol):
    """
    Returns True if cooldown is still active for a symbol.
    """
    if symbol not in last_alert_time:
        return False

    elapsed_seconds  = time.time() - last_alert_time[symbol]
    cooldown_seconds = ALERT_COOLDOWN_HRS * 3600

    return elapsed_seconds < cooldown_seconds


def scan_all_symbols():
    """
    Fetch all meme symbols and run signal check on each one.
    """
    print(f"\n[SCAN START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Resolution : {CANDLE_RESOLUTION}")
    print(f"[INFO] Scan every : {SCAN_INTERVAL_MIN} minutes")

    symbols = get_all_meme_symbols()

    if not symbols:
        print("[ERROR] No meme symbols fetched. Check API connection.")
        return

    signals_found = 0

    for symbol in symbols:
        try:
            # Skip if cooldown active
            if is_cooldown_active(symbol):
                continue

            # Fetch candles
            candles_pump   = get_pump_candles(symbol)
            candles_recent = get_recent_candles(symbol, count=50)

            if not candles_pump or not candles_recent:
                continue

            # Fetch funding rate
            funding_rate = get_funding_rate(symbol)

            # Run signal check
            signal = run_signal_check(
                symbol,
                candles_pump,
                candles_recent,
                funding_rate
            )

            if signal:
                # Attach TP percentage labels for Telegram message
                signal["tp1_pct"] = TP1_PCT
                signal["tp2_pct"] = TP2_PCT
                signal["tp3_pct"] = TP3_PCT

                print(
                    f"[SIGNAL FOUND] {symbol} | "
                    f"Pump: {signal['pump_pct']}% | "
                    f"Pattern: {signal['pattern']} | "
                    f"Funding: {signal['funding_rate']}"
                )
                send_signal_alert(signal)
                last_alert_time[symbol] = time.time()
                signals_found += 1

                # Small delay after sending alert
                time.sleep(1)

            # Rate limit protection between symbols
            time.sleep(0.3)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            continue

    print(f"[SCAN END] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Signals found: {signals_found}")


def main():
    print("=" * 50)
    print("  MEME SHORT SIGNAL BOT - STARTED")
    print("=" * 50)
    print(f"  Resolution  : {CANDLE_RESOLUTION}")
    print(f"  Scan every  : {SCAN_INTERVAL_MIN} minutes")
    print(f"  Cooldown    : {ALERT_COOLDOWN_HRS} hours")
    print("=" * 50)

    send_telegram_message(
        f"<b>MEME SHORT SIGNAL BOT - STARTED</b>\n"
        f"Resolution : {CANDLE_RESOLUTION}\n"
        f"Scan every : {SCAN_INTERVAL_MIN} minutes\n"
        f"Cooldown   : {ALERT_COOLDOWN_HRS} hours"
    )

    # Run once immediately on start
    scan_all_symbols()

    # Schedule recurring scans
    schedule.every(SCAN_INTERVAL_MIN).minutes.do(scan_all_symbols)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
