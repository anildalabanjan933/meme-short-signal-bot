# pnf_signal_checker.py
# -------------------------------------------------------
# Point & Figure (PnF) Bearish Reversal Signal Engine
# For Delta Exchange Meme Coin Short Signal Bot
#
# Matches TradingView PnF [ATR(14), 3] chart exactly
#
# Settings:
#   Box Size   : ATR(14) based
#   Reversal   : 3 boxes
#   Resolution : 5m candles
#
# Exhaustion (double top / higher low) = informational only
# Trendline break = main hard trigger
# -------------------------------------------------------

import time
import requests

# -------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------

BASE_URL = "https://api.india.delta.exchange"

ATR_PERIOD     = 14        # ATR period for box size
REVERSAL_BOXES = 3         # 3-box reversal rule

PUMP_THRESHOLD = 20.0      # minimum 20% pump in 48h

CANDLE_RESOLUTION     = "5m"
CANDLES_48H           = 576   # 48h of 5m candles
CANDLES_FETCH         = 700   # extra for ATR warmup
MIN_TRENDLINE_TOUCHES = 3     # minimum rising O bottom touch points
AVG_VOLUME_PERIOD     = 20    # candles for average volume


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

    ATR = average of last `period` true ranges
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
# POINT & FIGURE ENGINE
# -------------------------------------------------------

def build_pnf_chart(candles: list) -> list:
    """
    Build PnF chart using ATR(14) box sizing.
    Matches TradingView PnF [ATR(14), 3] exactly.

    Returns list of columns:
        {
            "direction" : "X" or "O",
            "boxes"     : list of price levels,
            "top"       : highest level,
            "bottom"    : lowest level,
            "col_index" : position in column list
        }
    """
    if len(candles) < ATR_PERIOD + 2:
        return []

    box_size = compute_atr(candles, ATR_PERIOD)
    if box_size <= 0:
        return []

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
                for _ in range(boxes_down):
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
                for _ in range(boxes_up):
                    new_level = new_col["top"] + box_size
                    new_col["boxes"].append(new_level)
                    new_col["top"] = new_level

                current_column = new_col

    # Append last open column
    if current_column["boxes"]:
        columns.append(current_column)

    return columns


# -------------------------------------------------------
# PnF PATTERN CHECKS
# -------------------------------------------------------

def has_bullish_uptrend(columns: list) -> bool:
    """
    Confirm bullish uptrend:
    At least 2 X columns with each top higher than previous.
    """
    x_cols = [c for c in columns if c["direction"] == "X"]
    if len(x_cols) < 2:
        return False

    rising = sum(
        1 for i in range(1, len(x_cols))
        if x_cols[i]["top"] > x_cols[i - 1]["top"]
    )
    return rising >= 2


def detect_exhaustion(columns: list, box_size: float) -> str:
    """
    Detect exhaustion near top — INFORMATIONAL ONLY.
    Does NOT block signal. Just labels what is happening.

    Returns: "Double Top", "Higher Low", or "None"
    """
    x_cols = [c for c in columns if c["direction"] == "X"]
    o_cols = [c for c in columns if c["direction"] == "O"]

    # Double top: last two X tops equal within 1.5 box tolerance
    if len(x_cols) >= 2:
        last_top = x_cols[-1]["top"]
        prev_top = x_cols[-2]["top"]
        if abs(last_top - prev_top) <= box_size * 1.5:
            return "Double Top"

    # Higher low: last O bottom higher than previous O bottom
    if len(o_cols) >= 2:
        if o_cols[-1]["bottom"] > o_cols[-2]["bottom"]:
            return "Higher Low"

    return "None"


def build_bullish_trendline(columns: list) -> dict | None:
    """
    Build bullish support trendline from rising O column bottoms.
    Matches the cyan diagonal line in your chart.

    Requires minimum 3 rising O bottom touch points.

    Returns:
        {
            "touch_points" : list of (col_index, bottom_price),
            "slope"        : price per column step,
            "last_support" : projected support at latest column
        }
        or None.
    """
    o_bottoms = [
        (col["col_index"], col["bottom"])
        for col in columns
        if col["direction"] == "O"
    ]

    if len(o_bottoms) < MIN_TRENDLINE_TOUCHES:
        return None

    # Keep only rising sequence
    rising = [o_bottoms[0]]
    for i in range(1, len(o_bottoms)):
        if o_bottoms[i][1] > rising[-1][1]:
            rising.append(o_bottoms[i])

    if len(rising) < MIN_TRENDLINE_TOUCHES:
        return None

    first    = rising[0]
    last     = rising[-1]
    col_span = last[0] - first[0]

    if col_span == 0:
        return None

    slope            = (last[1] - first[1]) / col_span
    current_col_idx  = columns[-1]["col_index"]
    last_support     = first[1] + slope * (current_col_idx - first[0])

    return {
        "touch_points": rising,
        "slope":        slope,
        "last_support": last_support
    }


def check_trendline_breakdown(columns: list, trendline: dict, current_price: float) -> bool:
    """
    Confirm bearish breakdown below bullish PnF trendline.

    ALL must be true:
    1. Current price < projected trendline support
    2. Latest column is O column
    3. O column has >= REVERSAL_BOXES boxes (confirmed reversal)
    """
    if not trendline or not columns:
        return False

    last_col      = columns[-1]
    price_below   = current_price < trendline["last_support"]
    is_o_col      = last_col["direction"] == "O"
    confirmed_rev = len(last_col["boxes"]) >= REVERSAL_BOXES

    return price_below and is_o_col and confirmed_rev


# -------------------------------------------------------
# SUPPORTING CONDITIONS
# -------------------------------------------------------

def check_48h_pump(candles: list) -> tuple[bool, float]:
    """
    Check pump > 20% in last 48h.
    """
    if len(candles) < 2:
        return False, 0.0

    window     = candles[-CANDLES_48H:] if len(candles) >= CANDLES_48H else candles
    low_price  = min(c["low"]  for c in window)
    high_price = max(c["high"] for c in window)

    if low_price <= 0:
        return False, 0.0

    pump_pct = ((high_price - low_price) / low_price) * 100.0
    return pump_pct >= PUMP_THRESHOLD, round(pump_pct, 2)


def check_volume(candles: list) -> tuple[bool, float, float]:
    """
    Latest candle volume must be above 20-candle average.
    """
    if len(candles) < AVG_VOLUME_PERIOD + 1:
        return False, 0.0, 0.0

    recent_vols = [c["volume"] for c in candles[-(AVG_VOLUME_PERIOD + 1):-1]]
    avg_vol     = sum(recent_vols) / len(recent_vols)
    latest_vol  = candles[-1]["volume"]

    return latest_vol > avg_vol, round(latest_vol, 2), round(avg_vol, 2)


def check_latest_candle_red(candles: list) -> bool:
    """
    Latest candle must close red (close < open).
    """
    if not candles:
        return False
    last = candles[-1]
    return last["close"] < last["open"]


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


def check_funding(symbol: str) -> str:
    """
    Funding rate direction from FUNDING:SYMBOL candles.

    Returns:
        "Longs Paying"  -> positive -> good for short
        "Shorts Paying" -> negative -> caution
        "Neutral"       -> near zero -> acceptable
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

    Hard conditions (ALL must pass):
        1. 48h pump > 20%
        2. PnF bullish uptrend confirmed
        3. Bullish trendline built (min 3 rising O bottoms)
        4. Trendline breakdown + confirmed O column
        5. Volume above average
        6. Latest candle red
        7. OI rising

    Informational (shown in message, does NOT block signal):
        - Exhaustion type: Double Top / Higher Low / None
        - Funding: Longs Paying / Shorts Paying / Neutral

    Returns signal dict or None.
    """

    # Step 1: Fetch candles
    candles = fetch_candles(symbol, CANDLE_RESOLUTION, CANDLES_FETCH)
    if len(candles) < ATR_PERIOD + 20:
        print(f"[PnF] {symbol}: Not enough candles ({len(candles)})")
        return None

    # Step 2: Compute ATR box size
    box_size = compute_atr(candles, ATR_PERIOD)
    if box_size <= 0:
        print(f"[PnF] {symbol}: ATR box size is zero, skipping")
        return None

    # Step 3: Check 48h pump
    pumped, pump_pct = check_48h_pump(candles)
    if not pumped:
        return None

    # Step 4: Build PnF chart
    columns = build_pnf_chart(candles)
    if len(columns) < 4:
        return None

    # Step 5: Confirm bullish uptrend
    if not has_bullish_uptrend(columns):
        return None

    # Step 6: Build bullish trendline (hard gate)
    trendline = build_bullish_trendline(columns)
    if trendline is None:
        return None

    # Step 7: Confirm trendline breakdown (hard gate)
    current_price = candles[-1]["close"]
    if not check_trendline_breakdown(columns, trendline, current_price):
        return None

    # Step 8: Volume above average (hard gate)
    vol_ok, latest_vol, avg_vol = check_volume(candles)
    if not vol_ok:
        return None

    # Step 9: Latest candle red (hard gate)
    if not check_latest_candle_red(candles):
        return None

    # Step 10: OI rising (hard gate)
    oi_rising = check_oi_rising(symbol)
    if not oi_rising:
        return None

    # Step 11: Exhaustion — informational only
    exhaustion_type = detect_exhaustion(columns, box_size)

    # Step 12: Funding — informational, affects verdict
    funding = check_funding(symbol)

    # Step 13: Verdict
    verdict = "AVOID SHORT" if funding == "Shorts Paying" else "GOOD FOR SHORT"

    # Step 14: Levels
    entry     = current_price
    stop_loss = round(entry * 1.05, 6)
    tp1       = round(entry * 0.70, 6)
    tp2       = round(entry * 0.50, 6)
    tp3       = round(entry * 0.30, 6)

    return {
        "symbol":          symbol,
        "pattern":         "PnF Bullish Trendline Break",
        "trendline_break": True,
        "pump_pct":        pump_pct,
        "exhaustion_type": exhaustion_type,
        "box_size_atr":    round(box_size, 6),
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

    Usage in main.py:
        from pnf_signal_checker import scan_pnf_signals
        pnf_signals = scan_pnf_signals(meme_coin_symbols)
        for signal in pnf_signals:
            send_pnf_signal(signal)
    """
    triggered = []
    for symbol in symbols:
        try:
            signal = check_pnf_signal(symbol)
            if signal:
                print(f"[PnF] SIGNAL: {symbol} | {signal['pattern']} | "
                      f"pump={signal['pump_pct']}% | exhaustion={signal['exhaustion_type']}")
                triggered.append(signal)
        except Exception as e:
            print(f"[PnF] Error scanning {symbol}: {e}")
    return triggered
