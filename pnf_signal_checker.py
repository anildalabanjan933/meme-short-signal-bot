# pnf_signal_checker.py
# -------------------------------------------------------
# Point & Figure (PnF) Bearish Reversal Signal Engine
# For Delta Exchange Meme Coin Short Signal Bot
#
# Matches TradingView PnF [ATR(14), 3] chart exactly
#
# 4 Conditions (in order from screenshot):
#   1st: Double Top OR Higher Low (exhaustion — informational)
#   2nd: Min 3 rising O-bottom touch points + bullish trendline break
#   3rd: Sudden pump >20% dynamic lookback (close-based)
#   4th: PnF Double Bottom Sell + Price breaks below 10 SMA
#
# Other hard gates: Volume > avg, OI rising
# Informational: Exhaustion type, Funding direction
# -------------------------------------------------------

import time
import requests

# -------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------

from config import BASE_URL, CANDLE_RESOLUTION

ATR_PERIOD            = 14
REVERSAL_BOXES        = 3
PUMP_THRESHOLD        = 20.0      # minimum % pump
CANDLES_FETCH         = 700       # extra for ATR warmup
CANDLES_1D            = 288       # 1 day x 5m candles (used for days calc)
MIN_TRENDLINE_TOUCHES = 3
AVG_VOLUME_PERIOD     = 20
SMA_PERIOD            = 10        # 10 SMA for condition 4


# -------------------------------------------------------
# DATA FETCHING
# -------------------------------------------------------

def fetch_candles(symbol: str, resolution: str, limit: int) -> list:
    """
    Fetch OHLCV candles from Delta Exchange.
    Endpoint: GET /v2/history/candles
    Supports: SYMBOL, OI:SYMBOL, FUNDING:SYMBOL
    """
    seconds_per_candle = {
        "1m": 60, "3m": 180, "5m": 300,
        "15m": 900, "30m": 1800, "1h": 3600,
        "4h": 14400, "1d": 86400
    }
    end   = int(time.time())
    span  = limit * seconds_per_candle.get(resolution, 300)
    start = end - span

    url    = f"{BASE_URL}/v2/history/candles"
    params = {
        "symbol":     symbol,
        "resolution": resolution,
        "start":      start,
        "end":        end
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("success") and data.get("result"):
            return sorted(data["result"], key=lambda c: c["time"])
        return []
    except Exception as e:
        print(f"[PnF] fetch_candles error for {symbol}: {e}")
        return []


def fetch_oi_candles(symbol: str) -> list:
    """OI data via OI:SYMBOL format."""
    return fetch_candles(f"OI:{symbol}", CANDLE_RESOLUTION, 30)


def fetch_funding_candles(symbol: str) -> list:
    """Funding rate data via FUNDING:SYMBOL format."""
    return fetch_candles(f"FUNDING:{symbol}", CANDLE_RESOLUTION, 10)


# -------------------------------------------------------
# ATR CALCULATION
# -------------------------------------------------------

def compute_atr(candles: list, period: int = ATR_PERIOD) -> float:
    """
    Compute ATR(period) from candles.
    Matches TradingView ATR formula exactly.

    True Range = max of:
        high - low
        abs(high - prev_close)
        abs(low  - prev_close)

    ATR = simple average of last `period` true ranges
    """
    if len(candles) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(candles)):
        high       = candles[i]["high"]
        low        = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low  - prev_close)
        )
        true_ranges.append(tr)

    recent_trs = true_ranges[-period:]
    return sum(recent_trs) / len(recent_trs)


# -------------------------------------------------------
# 10 SMA CALCULATION
# -------------------------------------------------------

def compute_sma(candles: list, period: int = SMA_PERIOD) -> float:
    """
    Compute Simple Moving Average of close prices.
    Uses last `period` candles.
    """
    if len(candles) < period:
        return 0.0
    closes = [c["close"] for c in candles[-period:]]
    return sum(closes) / len(closes)


# -------------------------------------------------------
# POINT & FIGURE ENGINE
# -------------------------------------------------------

def build_pnf_chart(candles: list) -> tuple:
    """
    Build PnF chart using ATR(14) box sizing.
    Matches TradingView PnF [ATR(14), 3] exactly.

    Returns:
        (columns, box_size)

    Each column:
        {
            "direction" : "X" or "O",
            "boxes"     : list of price levels,
            "top"       : highest level,
            "bottom"    : lowest level,
            "col_index" : sequential index
        }
    """
    if len(candles) < ATR_PERIOD + 2:
        return [], 0.0

    box_size = compute_atr(candles, ATR_PERIOD)
    if box_size <= 0:
        return [], 0.0

    closes = [c["close"] for c in candles]

    # Initialize first column
    start_price = closes[0]
    direction   = "X" if closes[1] >= closes[0] else "O"

    current_column = {
        "direction": direction,
        "boxes":     [start_price],
        "top":       start_price,
        "bottom":    start_price,
        "col_index": 0
    }
    columns = []

    for price in closes[1:]:

        if current_column["direction"] == "X":

            # Add more X boxes if price rises
            boxes_up = int((price - current_column["top"]) / box_size)
            if boxes_up >= 1:
                for _ in range(boxes_up):
                    new_level = current_column["top"] + box_size
                    current_column["boxes"].append(new_level)
                    current_column["top"] = new_level

            # 3-box reversal down -> new O column
            elif (current_column["top"] - price) >= (REVERSAL_BOXES * box_size):
                columns.append(current_column)
                reversal_start = current_column["top"] - box_size

                new_col = {
                    "direction": "O",
                    "boxes":     [reversal_start],
                    "top":       reversal_start,
                    "bottom":    reversal_start,
                    "col_index": len(columns)
                }

                boxes_down = int((reversal_start - price) / box_size)
                for _ in range(max(boxes_down, 0)):
                    new_level = new_col["bottom"] - box_size
                    new_col["boxes"].append(new_level)
                    new_col["bottom"] = new_level

                current_column = new_col

        else:  # O column

            # Add more O boxes if price falls
            boxes_down = int((current_column["bottom"] - price) / box_size)
            if boxes_down >= 1:
                for _ in range(boxes_down):
                    new_level = current_column["bottom"] - box_size
                    current_column["boxes"].append(new_level)
                    current_column["bottom"] = new_level

            # 3-box reversal up -> new X column
            elif (price - current_column["bottom"]) >= (REVERSAL_BOXES * box_size):
                columns.append(current_column)
                reversal_start = current_column["bottom"] + box_size

                new_col = {
                    "direction": "X",
                    "boxes":     [reversal_start],
                    "top":       reversal_start,
                    "bottom":    reversal_start,
                    "col_index": len(columns)
                }

                boxes_up = int((price - reversal_start) / box_size)
                for _ in range(max(boxes_up, 0)):
                    new_level = new_col["top"] + box_size
                    new_col["boxes"].append(new_level)
                    new_col["top"] = new_level

                current_column = new_col

    # Append last open column
    if current_column["boxes"]:
        columns.append(current_column)

    return columns, box_size


# -------------------------------------------------------
# CONDITION 1 — EXHAUSTION (INFORMATIONAL ONLY)
# Double Top OR Higher Low
# -------------------------------------------------------

def detect_exhaustion(columns: list, box_size: float) -> str:
    """
    CONDITION 1 — Informational only. Does NOT block signal.

    Double Top  : Last two X column tops are equal (within 1.5 box tolerance)
    Higher Low  : Last O column bottom is higher than previous O column bottom

    Returns: "Double Top", "Higher Low", or "None"
    """
    x_cols = [c for c in columns if c["direction"] == "X"]
    o_cols = [c for c in columns if c["direction"] == "O"]

    # Double Top check
    if len(x_cols) >= 2:
        last_top = x_cols[-1]["top"]
        prev_top = x_cols[-2]["top"]
        if abs(last_top - prev_top) <= box_size * 1.5:
            return "Double Top"

    # Higher Low check
    if len(o_cols) >= 2:
        if o_cols[-1]["bottom"] > o_cols[-2]["bottom"]:
            return "Higher Low"

    return "None"


# -------------------------------------------------------
# CONDITION 2 — TRENDLINE: MIN 3 RISING O-BOTTOM TOUCH POINTS
# -------------------------------------------------------

def build_bullish_trendline(columns: list) -> dict | None:
    """
    CONDITION 2 — Hard gate.

    Build bullish support trendline from rising O column bottoms.
    Matches the cyan diagonal rising trendline in the chart.

    Logic:
    - Collect all O column bottoms
    - Find the BEST rising sequence (most touch points, most recent)
      by trying every possible starting O bottom
    - Require minimum 3 rising touch points
    - Project trendline support to current column index

    Returns:
        {
            "touch_points" : list of (col_index, bottom_price),
            "slope"        : price per column step,
            "last_support" : projected support at latest column
        }
        or None if not enough rising touch points.
    """
    o_bottoms = [
        (col["col_index"], col["bottom"])
        for col in columns
        if col["direction"] == "O"
    ]

    if len(o_bottoms) < MIN_TRENDLINE_TOUCHES:
        return None

    best_rising = []

    for start_idx in range(len(o_bottoms)):
        rising = [o_bottoms[start_idx]]
        for i in range(start_idx + 1, len(o_bottoms)):
            if o_bottoms[i][1] > rising[-1][1]:
                rising.append(o_bottoms[i])

        if len(rising) >= MIN_TRENDLINE_TOUCHES:
            if (len(rising) > len(best_rising) or
                (len(rising) == len(best_rising) and
                 rising[-1][0] > best_rising[-1][0])):
                best_rising = rising

    if len(best_rising) < MIN_TRENDLINE_TOUCHES:
        return None

    first    = best_rising[0]
    last     = best_rising[-1]
    col_span = last[0] - first[0]

    if col_span == 0:
        return None

    slope        = (last[1] - first[1]) / col_span
    current_idx  = columns[-1]["col_index"]
    last_support = first[1] + slope * (current_idx - first[0])

    return {
        "touch_points": best_rising,
        "slope":        slope,
        "last_support": last_support
    }


def check_trendline_breakdown(columns: list, trendline: dict, current_price: float) -> bool:
    """
    CONDITION 2 continued — Hard gate.

    Trendline breakdown confirmed when:
    1. Current price < projected trendline support
    2. Latest column is O column (bearish)
    3. O column has >= REVERSAL_BOXES boxes (3-box reversal confirmed)
    """
    if not trendline or not columns:
        return False

    last_col      = columns[-1]
    price_below   = current_price < trendline["last_support"]
    is_o_col      = last_col["direction"] == "O"
    confirmed_rev = len(last_col["boxes"]) >= REVERSAL_BOXES

    return price_below and is_o_col and confirmed_rev


# -------------------------------------------------------
# CONDITION 3 — SUDDEN PUMP — DYNAMIC LOOKBACK
# -------------------------------------------------------

def check_sudden_pump(candles: list) -> tuple:
    """
    CONDITION 3 — Hard gate.

    Dynamically scans ALL available candle history to find where
    the pump actually started — not a fixed window.

    Logic:
    - Scan all candles from oldest to newest
    - Find the lowest close price across all available history
    - Calculate pump % from that lowest close to current close
    - If pump >= PUMP_THRESHOLD, condition passes
    - Calculate how many days ago that lowest point was

    This means:
    - If pump started 1 day ago -> shows 1d
    - If pump started 3 days ago -> shows 3d
    - If pump started a week ago -> shows 7d
    - No fixed cap on lookback window

    Returns:
        (pumped: bool, pump_pct: float, days_ago: float)
    """
    if len(candles) < 10:
        return False, 0.0, 0.0

    latest_close = candles[-1]["close"]
    latest_time  = candles[-1]["time"]

    # Find the lowest close across all available candles (excluding last candle)
    lowest_close = None
    lowest_time  = None

    for candle in candles[:-1]:
        close = candle["close"]
        if lowest_close is None or close < lowest_close:
            lowest_close = close
            lowest_time  = candle["time"]

    if lowest_close is None or lowest_close <= 0:
        return False, 0.0, 0.0

    pump_pct = ((latest_close - lowest_close) / lowest_close) * 100.0

    # Calculate how many days ago the lowest point was
    # candle time is in seconds (unix timestamp)
    seconds_ago = latest_time - lowest_time
    days_ago    = round(seconds_ago / 86400, 1)

    pumped = pump_pct >= PUMP_THRESHOLD
    return pumped, round(pump_pct, 2), days_ago


# -------------------------------------------------------
# CONDITION 4 — PnF DOUBLE BOTTOM SELL + BREAK BELOW 10 SMA
# -------------------------------------------------------

def check_double_bottom_sell(columns: list) -> bool:
    """
    CONDITION 4a — Hard gate.

    PnF Double Bottom Sell Signal:
    - Latest O column bottom is LOWER than previous O column bottom
    - Confirms bearish momentum in PnF structure
    """
    o_cols = [c for c in columns if c["direction"] == "O"]

    if len(o_cols) < 2:
        return False

    return o_cols[-1]["bottom"] < o_cols[-2]["bottom"]


def check_below_10sma(candles: list) -> bool:
    """
    CONDITION 4b — Hard gate.

    Price must break and close BELOW 10 SMA.
    Signal confirmed when current close < 10 SMA.
    """
    if len(candles) < SMA_PERIOD:
        return False

    sma_10        = compute_sma(candles, SMA_PERIOD)
    current_close = candles[-1]["close"]

    return current_close < sma_10


# -------------------------------------------------------
# SUPPORTING HARD GATES
# -------------------------------------------------------

def check_volume(candles: list) -> tuple:
    """
    Volume hard gate.
    Latest candle volume must be above 20-candle average.
    """
    if len(candles) < AVG_VOLUME_PERIOD + 1:
        return False, 0.0, 0.0

    recent_vols = [c["volume"] for c in candles[-(AVG_VOLUME_PERIOD + 1):-1]]
    avg_vol     = sum(recent_vols) / len(recent_vols)
    latest_vol  = candles[-1]["volume"]

    return latest_vol > avg_vol, round(latest_vol, 2), round(avg_vol, 2)


def check_oi_rising(symbol: str) -> bool:
    """
    OI rising over last 6 candles (30 min on 5m).
    Uses OI:SYMBOL via Delta Exchange candles endpoint.
    """
    oi_candles = fetch_oi_candles(symbol)
    if len(oi_candles) < 6:
        return False
    recent = oi_candles[-6:]
    return recent[-1]["close"] > recent[0]["close"]


# -------------------------------------------------------
# INFORMATIONAL — FUNDING
# -------------------------------------------------------

def check_funding(symbol: str) -> str:
    """
    Funding rate direction — informational, affects verdict only.

    Returns:
        "Longs Paying"  -> positive -> GOOD FOR SHORT
        "Shorts Paying" -> negative -> AVOID SHORT
        "Neutral"       -> near zero -> GOOD FOR SHORT
    """
    funding_candles = fetch_funding_candles(symbol)
    if not funding_candles:
        return "Neutral"

    latest = funding_candles[-1]["close"]

    if latest > 0.0001:
        return "Longs Paying"
    elif latest < -0.0001:
        return "Shorts Paying"
    else:
        return "Neutral"


# -------------------------------------------------------
# MAIN SIGNAL FUNCTION
# -------------------------------------------------------

def check_pnf_signal(symbol: str) -> dict | None:
    """
    Full PnF Bearish Reversal Signal Check.

    4 Main Conditions (in order):
        1st: Double Top OR Higher Low     — INFORMATIONAL (shown in message)
        2nd: Min 3 rising O-bottom touch points + trendline breakdown — HARD GATE
        3rd: Sudden pump — dynamic lookback, finds actual pump origin  — HARD GATE
        4th: PnF Double Bottom Sell + Break below 10 SMA               — HARD GATE

    Additional Hard Gates:
        - Volume above 20-candle average
        - OI rising

    Informational (shown in message, does NOT block signal):
        - Exhaustion type: Double Top / Higher Low / None
        - Funding: Longs Paying / Shorts Paying / Neutral

    Verdict:
        - "Shorts Paying" funding -> AVOID SHORT
        - All others              -> GOOD FOR SHORT

    Returns signal dict or None.
    """

    # --- Fetch candles ---
    candles = fetch_candles(symbol, CANDLE_RESOLUTION, CANDLES_FETCH)
    if len(candles) < ATR_PERIOD + 20:
        print(f"[PnF] {symbol}: Not enough candles ({len(candles)})")
        return None

    # --- Build PnF chart ---
    columns, box_size = build_pnf_chart(candles)
    if len(columns) < 4 or box_size <= 0:
        print(f"[PnF] {symbol}: Not enough PnF columns or zero box size")
        return None

    # -------------------------------------------------------
    # CONDITION 1 — Exhaustion (INFORMATIONAL ONLY)
    # -------------------------------------------------------
    exhaustion_type = detect_exhaustion(columns, box_size)

    # -------------------------------------------------------
    # CONDITION 2 — Min 3 rising O-bottom touch points
    #               + Trendline breakdown (HARD GATE)
    # -------------------------------------------------------
    trendline = build_bullish_trendline(columns)
    if trendline is None:
        print(f"[PnF] {symbol}: No valid bullish trendline (need {MIN_TRENDLINE_TOUCHES} rising O bottoms)")
        return None

    current_price = candles[-1]["close"]
    if not check_trendline_breakdown(columns, trendline, current_price):
        print(f"[PnF] {symbol}: Trendline not broken yet")
        return None

    # -------------------------------------------------------
    # CONDITION 3 — Sudden pump dynamic lookback (HARD GATE)
    # -------------------------------------------------------
    pumped, pump_pct, pump_days = check_sudden_pump(candles)
    if not pumped:
        print(f"[PnF] {symbol}: Pump {pump_pct:.2f}% < {PUMP_THRESHOLD}% threshold")
        return None

    # -------------------------------------------------------
    # CONDITION 4 — PnF Double Bottom Sell + Break below 10 SMA
    #               (HARD GATE — BOTH must pass)
    # -------------------------------------------------------
    if not check_double_bottom_sell(columns):
        print(f"[PnF] {symbol}: No PnF double bottom sell signal")
        return None

    if not check_below_10sma(candles):
        print(f"[PnF] {symbol}: Price not below 10 SMA")
        return None

    # -------------------------------------------------------
    # ADDITIONAL HARD GATES
    # -------------------------------------------------------

    vol_ok, latest_vol, avg_vol = check_volume(candles)
    if not vol_ok:
        print(f"[PnF] {symbol}: Volume too low ({latest_vol} < avg {avg_vol})")
        return None

    oi_rising = check_oi_rising(symbol)
    if not oi_rising:
        print(f"[PnF] {symbol}: OI not rising")
        return None

    # -------------------------------------------------------
    # INFORMATIONAL — Funding
    # -------------------------------------------------------
    funding = check_funding(symbol)

    # -------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------
    if funding == "Shorts Paying":
        verdict = "AVOID SHORT"
    else:
        verdict = "GOOD FOR SHORT"

    # -------------------------------------------------------
    # PRICE LEVELS
    # SL  : +5% above entry
    # TP1 : -30% from entry
    # TP2 : -50% from entry
    # TP3 : -70% from entry
    # -------------------------------------------------------
    entry     = current_price
    stop_loss = round(entry * 1.05, 8)
    tp1       = round(entry * 0.70, 8)
    tp2       = round(entry * 0.50, 8)
    tp3       = round(entry * 0.30, 8)

    # -------------------------------------------------------
    # SIGNAL DICT
    # -------------------------------------------------------
    return {
        "symbol":          symbol,
        "pattern":         "PnF Bullish Trendline Break",
        "trendline_break": True,
        "pump_pct":        pump_pct,
        "pump_days":       pump_days,
        "exhaustion_type": exhaustion_type,
        "box_size_atr":    round(box_size, 8),
        "volume":          latest_vol,
        "avg_volume":      avg_vol,
        "oi_rising":       oi_rising,
        "funding":         funding,
        "verdict":         verdict,
        "entry":           entry,
        "stop_loss":       stop_loss,
        "tp1":             tp1,
        "tp2":             tp2,
        "tp3":             tp3,
    }


# -------------------------------------------------------
# BATCH SCANNER — called from main.py
# -------------------------------------------------------

def scan_pnf_signals(symbols: list) -> list:
    """
    Scan list of symbols for PnF short signals.
    Returns only triggered signal dicts.
    """
    triggered = []
    for symbol in symbols:
        try:
            signal = check_pnf_signal(symbol)
            if signal:
                print(
                    f"[PnF] *** SIGNAL: {symbol} | {signal['pattern']} | "
                    f"pump={signal['pump_pct']}% in {signal['pump_days']}d | "
                    f"exhaustion={signal['exhaustion_type']} | "
                    f"verdict={signal['verdict']} ***"
                )
                triggered.append(signal)
        except Exception as e:
            print(f"[PnF] Error scanning {symbol}: {e}")
    return triggered
