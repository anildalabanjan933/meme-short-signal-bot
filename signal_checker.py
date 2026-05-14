# =========================================================
# SIGNAL CHECKER - All signal condition logic
# =========================================================

from config import (
    PUMP_THRESHOLD_PCT,
    DOUBLE_TOP_TOLERANCE,
    VOLUME_AVG_PERIOD,
    CANDLE_RESOLUTION,
    REVERSAL_LOOKBACK,
    TP1_PCT,
    TP2_PCT,
    TP3_PCT
)


def check_pump(candles_pump):
    """
    Condition 1: Check if coin pumped >= PUMP_THRESHOLD_PCT
    over the lookback period.
    Returns (bool, pump_percentage)
    """
    if len(candles_pump) < 2:
        return False, 0.0

    old_price     = float(candles_pump[0]["close"])
    current_price = float(candles_pump[-1]["close"])

    if old_price <= 0:
        return False, 0.0

    pump_pct = ((current_price - old_price) / old_price) * 100

    return pump_pct >= PUMP_THRESHOLD_PCT, round(pump_pct, 2)


def check_lower_high(candles):
    """
    Condition 2a: Detect lower high pattern.
    Uses REVERSAL_LOOKBACK to find the last 3 swing highs.
    High[-3] > High[-2] > High[-1]
    Returns bool
    """
    if len(candles) < REVERSAL_LOOKBACK:
        return False

    recent = candles[-REVERSAL_LOOKBACK:]

    high_3 = float(recent[-3]["high"])
    high_2 = float(recent[-2]["high"])
    high_1 = float(recent[-1]["high"])

    return high_3 > high_2 > high_1


def check_double_top(candles):
    """
    Condition 2b: Detect double top pattern.
    Two recent swing highs are nearly equal within DOUBLE_TOP_TOLERANCE.
    Returns bool
    """
    if len(candles) < 10:
        return False

    highs = [float(c["high"]) for c in candles[-20:]]

    sorted_highs = sorted(highs, reverse=True)
    high1 = sorted_highs[0]
    high2 = sorted_highs[1]

    if high1 <= 0:
        return False

    difference = abs(high1 - high2) / high1

    return difference < DOUBLE_TOP_TOLERANCE


def check_red_candle(candles):
    """
    Condition 3: Latest candle must be red (close < open).
    Returns bool
    """
    if len(candles) < 1:
        return False

    latest = candles[-1]
    return float(latest["close"]) < float(latest["open"])


def check_volume_confirmation(candles):
    """
    Condition 4: Current candle volume must be above average.
    Uses VOLUME_AVG_PERIOD candles for average calculation.
    Returns (bool, current_volume, avg_volume)
    """
    if len(candles) < VOLUME_AVG_PERIOD + 1:
        return False, 0, 0

    recent_volumes = [float(c["volume"]) for c in candles[-(VOLUME_AVG_PERIOD + 1):-1]]
    avg_volume     = sum(recent_volumes) / len(recent_volumes)
    current_volume = float(candles[-1]["volume"])

    return current_volume > avg_volume, round(current_volume, 2), round(avg_volume, 2)


def get_stop_loss(candles):
    """
    Stop Loss: Highest high in last REVERSAL_LOOKBACK candles.
    Returns float
    """
    recent_highs = [float(c["high"]) for c in candles[-REVERSAL_LOOKBACK:]]
    return max(recent_highs)


def calculate_targets(entry_price):
    """
    Calculate TP1, TP2, TP3 based on configurable percentages.
    Returns (tp1, tp2, tp3)
    """
    tp1 = round(entry_price * (1 - TP1_PCT / 100), 6)
    tp2 = round(entry_price * (1 - TP2_PCT / 100), 6)
    tp3 = round(entry_price * (1 - TP3_PCT / 100), 6)
    return tp1, tp2, tp3


def run_signal_check(symbol, candles_pump, candles_recent, funding_rate):
    """
    Run all signal conditions.
    Returns signal dict if all conditions pass, else None.

    Conditions:
      1. Pump >= PUMP_THRESHOLD_PCT over lookback period
      2. Lower High OR Double Top pattern
      3. Latest candle is red
      4. Volume above average
    """
    # Condition 1 - Pump check
    pumped, pump_pct = check_pump(candles_pump)
    if not pumped:
        return None

    # Condition 2 - Reversal pattern
    lower_high = check_lower_high(candles_recent)
    double_top = check_double_top(candles_recent)
    if not lower_high and not double_top:
        return None

    # Condition 3 - Red candle
    if not check_red_candle(candles_recent):
        return None

    # Condition 4 - Volume confirmation
    vol_confirmed, current_vol, avg_vol = check_volume_confirmation(candles_recent)
    if not vol_confirmed:
        return None

    # All conditions passed - build signal
    entry_price   = float(candles_recent[-1]["close"])
    sl            = get_stop_loss(candles_recent)
    tp1, tp2, tp3 = calculate_targets(entry_price)

    pattern = "Lower High" if lower_high else "Double Top"
    if lower_high and double_top:
        pattern = "Lower High + Double Top"

    return {
        "symbol":         symbol,
        "pattern":        pattern,
        "pump_pct":       pump_pct,
        "resolution":     CANDLE_RESOLUTION,
        "entry_price":    round(entry_price, 6),
        "sl":             round(sl, 6),
        "tp1":            tp1,
        "tp2":            tp2,
        "tp3":            tp3,
        "current_volume": current_vol,
        "avg_volume":     avg_vol,
        "funding_rate":   funding_rate
    }
