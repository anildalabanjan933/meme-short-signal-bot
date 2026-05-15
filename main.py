# =========================================================
# MAIN - Runs the signal scanner loop
# Sends BOTH:
#   - Original reversal signals (signal_checker.py)
#   - New PnF trendline break signals (pnf_signal_checker.py)
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
    get_funding_rate,
    get_oi_data
)
from signal_checker import run_signal_check
from pnf_signal_checker import scan_pnf_signals          # NEW
from telegram_notifier import (
    send_signal_alert,
    send_telegram_message,
    send_pnf_signal                                       # NEW
)

# Track last alert time per symbol (shared by both bots)
# Key format:
#   original bot -> "SYMBOL"
#   PnF bot      -> "PNF_SYMBOL"
last_alert_time = {}


def is_cooldown_active(symbol: str, prefix: str = "") -> bool:
    """
    Returns True if cooldown is still active for a symbol.
    prefix = ""      for original bot
    prefix = "PNF_"  for PnF bot
    Keeps cooldowns separate so both can fire independently.
    """
    key              = f"{prefix}{symbol}"
    if key not in last_alert_time:
        return False

    elapsed_seconds  = time.time() - last_alert_time[key]
    cooldown_seconds = ALERT_COOLDOWN_HRS * 3600

    return elapsed_seconds < cooldown_seconds


def scan_all_symbols():
    """
    Fetch all meme symbols and run BOTH signal checks on each one.
    """
    print(f"\n[SCAN START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Resolution : {CANDLE_RESOLUTION}")
    print(f"[INFO] Scan every : {SCAN_INTERVAL_MIN} minutes")

    symbols = get_all_meme_symbols()

    if not symbols:
        print("[ERROR] No meme symbols fetched. Check API connection.")
        return

    original_signals_found = 0
    pnf_signals_found      = 0

    # =========================================================
    # PART 1 — ORIGINAL REVERSAL BOT (unchanged logic)
    # =========================================================
    for symbol in symbols:
        try:
            # Skip if original bot cooldown active
            if is_cooldown_active(symbol, prefix=""):
                continue

            # Fetch candles
            candles_pump   = get_pump_candles(symbol)
            candles_recent = get_recent_candles(symbol, count=50)

            if not candles_pump or not candles_recent:
                continue

            # Fetch funding and OI
            funding_rate                  = get_funding_rate(symbol)
            oi_value_usd, oi_change_usd_6h = get_oi_data(symbol)

            # Run original signal check
            signal = run_signal_check(
                symbol,
                candles_pump,
                candles_recent,
                funding_rate,
                oi_value_usd,
                oi_change_usd_6h
            )

            if signal:
                signal["tp1_pct"] = TP1_PCT
                signal["tp2_pct"] = TP2_PCT
                signal["tp3_pct"] = TP3_PCT

                print(
                    f"[ORIGINAL SIGNAL] {symbol} | "
                    f"Pump: {signal['pump_pct']}% | "
                    f"Pattern: {signal['pattern']} | "
                    f"Funding: {signal['funding_rate']} | "
                    f"OI: ${signal['oi_value_usd']:,.0f} | "
                    f"OI 6H: ${signal['oi_change_usd_6h']:,.0f}"
                )

                send_signal_alert(signal)
                last_alert_time[symbol] = time.time()
                original_signals_found += 1
                time.sleep(1)

            time.sleep(0.3)

        except Exception as e:
            print(f"[ERROR][ORIGINAL] {symbol}: {e}")
            continue

    # =========================================================
    # PART 2 — PnF TRENDLINE BREAK BOT (new)
    # =========================================================

    # Filter out symbols still in PnF cooldown
    symbols_to_scan_pnf = [
        s for s in symbols
        if not is_cooldown_active(s, prefix="PNF_")
    ]

    # Run PnF scanner on all eligible symbols at once
    pnf_signals = scan_pnf_signals(symbols_to_scan_pnf)

    for signal in pnf_signals:
        try:
            symbol = signal["symbol"]

            print(
                f"[PnF SIGNAL] {symbol} | "
                f"Pattern: {signal['pattern']} | "
                f"Pump: {signal['pump_pct']}% | "
                f"Exhaustion: {signal['exhaustion_type']} | "
                f"ATR Box: {signal['box_size_atr']} | "
                f"Verdict: {signal['verdict']}"
            )

            send_pnf_signal(signal)
            last_alert_time[f"PNF_{symbol}"] = time.time()
            pnf_signals_found += 1
            time.sleep(1)

        except Exception as e:
            print(f"[ERROR][PnF] {signal.get('symbol', '?')}: {e}")
            continue

    # =========================================================
    # SCAN SUMMARY
    # =========================================================
    print(
        f"[SCAN END] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Original signals: {original_signals_found} | "
        f"PnF signals: {pnf_signals_found}"
    )


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
        f"Resolution  : {CANDLE_RESOLUTION}\n"
        f"Scan every  : {SCAN_INTERVAL_MIN} minutes\n"
        f"Cooldown    : {ALERT_COOLDOWN_HRS} hours\n"
        f"Engines     : Original Reversal + PnF Trendline Break"
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
