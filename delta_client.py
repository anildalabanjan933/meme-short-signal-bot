# =========================================================
# DELTA CLIENT - Fetches data from Delta Exchange API
# All public endpoints — no API key required
# Base URL: Production (real market data for signals)
# =========================================================

import requests
import time
from config import BASE_URL, CANDLE_RESOLUTION, PUMP_LOOKBACK_HRS

# =========================================================
# COMPLETE DEMO FUTURES SYMBOL LIST
# All symbols verified live on Delta Exchange
# Source: demo.delta.exchange/app/futures/markets
# Last verified: May 2026
# Format: {COIN}USD
# =========================================================

DEMO_SYMBOLS = [
    # --- Major Coins ---
    "BTCUSD",        # Bitcoin Perpetual
    "ETHUSD",        # Ethereum Perpetual
    "SOLUSD",        # Solana Perpetual
    "XRPUSD",        # Ripple Perpetual
    "ADAUSD",        # Cardano Perpetual

    # --- Meme Coins ---
    "DOGEUSD",       # Dogecoin Perpetual
    "1000SHIBUSD",   # 1000 Shiba Inu Perpetual
    "WIFUSD",        # Dogwifhat Perpetual
    "MEMEUSD",       # Memecoin Perpetual
    "POPCATUSD",     # Popcat Perpetual
    "NEIROUSD",      # Neiro Perpetual
    "GOATUSD",       # Goatseus Maximus Perpetual
    "PNUTUSD",       # Peanut the Squirrel Perpetual
    "ACTUSD",        # Act I The AI Prophecy Perpetual
    "BLESSUSD",      # Bless Perpetual
    "FARTCOINUSD",   # Fartcoin Perpetual
    "TRUMPUSD",      # Official Trump Perpetual
    "MELANIAUSD",    # Melania Meme Perpetual
    "KAITOUSD",      # KAITO Perpetual
    "MOODENGUSD",    # Moo Deng Perpetual

    # --- DeFi / Other ---
    "ONDOUSD",       # Ondo Perpetual

    # --- xStock / Metal Tokens ---
    "NVDAXUSD",      # NVIDIA xStock Token Perpetual
    "XAUUSD",        # Tether Gold Token Perpetual
    "PAXGUSD",       # PAX Gold Token Perpetual
]


def get_all_meme_symbols():
    """
    Returns the full demo symbol list directly.
    No API tag filtering needed — using verified demo list.
    Also attempts to auto-discover any new symbols via API
    and merges them with the base list.
    Returns list of symbol strings.
    """
    # Start with verified demo list
    symbols  = list(DEMO_SYMBOLS)
    page_size = 100
    after     = None
    api_found = []

    # Try to auto-discover new symbols via API
    while True:
        params = {
            "contract_types": "perpetual_futures",
            "states":         "live",
            "page_size":      page_size
        }
        if after:
            params["after"] = after

        try:
            response = requests.get(
                f"{BASE_URL}/v2/products",
                params=params,
                timeout=10
            )
            data = response.json()

            if not data.get("success"):
                break

            results = data.get("result", [])
            if not results:
                break

            for product in results:
                if product.get("trading_status") != "operational":
                    continue
                if product.get("state") != "live":
                    continue

                symbol = product.get("symbol", "")
                tags   = product.get("product_specs", {}).get("tags", [])
                tag_set = {t.lower() for t in tags}

                # Auto-add any new meme coins not in our list
                if "meme" in tag_set and symbol not in symbols:
                    api_found.append(symbol)
                    print(f"[INFO] New meme coin discovered via API: {symbol}")

            meta  = data.get("meta", {})
            after = meta.get("after")
            if not after:
                break

        except Exception as e:
            print(f"[WARN] API auto-discovery failed: {e}")
            break

        time.sleep(0.2)

    # Merge new API-discovered symbols
    symbols.extend(api_found)

    print(f"[INFO] Total symbols to scan: {len(symbols)}")
    return symbols


def _resolution_to_seconds(resolution):
    """Convert resolution string to seconds."""
    mapping = {
        "1m":  60,
        "3m":  180,
        "5m":  300,
        "15m": 900,
        "30m": 1800,
        "1h":  3600,
        "2h":  7200,
        "4h":  14400,
        "6h":  21600,
        "1d":  86400
    }
    return mapping.get(resolution, 300)


def get_pump_candles(symbol):
    """
    Fetch candles covering PUMP_LOOKBACK_HRS for pump detection.
    Always uses 1h resolution — faster and sufficient for pump check.
    Returns list of candle dicts: time, open, high, low, close, volume
    """
    end_time   = int(time.time())
    start_time = end_time - (PUMP_LOOKBACK_HRS * 3600)

    try:
        response = requests.get(
            f"{BASE_URL}/v2/history/candles",
            params={
                "symbol":     symbol,
                "resolution": "1h",
                "start":      start_time,
                "end":        end_time
            },
            timeout=10
        )
        data = response.json()

        if not data.get("success"):
            return []

        return data.get("result", [])

    except Exception as e:
        print(f"[ERROR] get_pump_candles({symbol}): {e}")
        return []


def get_recent_candles(symbol, count=50):
    """
    Fetch the most recent N candles at CANDLE_RESOLUTION
    for reversal pattern detection.
    Returns list of candle dicts.
    """
    resolution  = CANDLE_RESOLUTION
    res_seconds = _resolution_to_seconds(resolution)
    end_time    = int(time.time())
    start_time  = end_time - (res_seconds * count)

    try:
        response = requests.get(
            f"{BASE_URL}/v2/history/candles",
            params={
                "symbol":     symbol,
                "resolution": resolution,
                "start":      start_time,
                "end":        end_time
            },
            timeout=10
        )
        data = response.json()

        if not data.get("success"):
            return []

        return data.get("result", [])

    except Exception as e:
        print(f"[ERROR] get_recent_candles({symbol}): {e}")
        return []


def get_pnf_candles(symbol, count=700):
    """
    Fetch candles specifically for PnF chart building.
    Uses CANDLE_RESOLUTION from config (5m default).
    Fetches more candles than get_recent_candles for ATR warmup.
    Returns list sorted by time ascending.
    """
    resolution  = CANDLE_RESOLUTION
    res_seconds = _resolution_to_seconds(resolution)
    end_time    = int(time.time())
    start_time  = end_time - (res_seconds * count)

    try:
        response = requests.get(
            f"{BASE_URL}/v2/history/candles",
            params={
                "symbol":     symbol,
                "resolution": resolution,
                "start":      start_time,
                "end":        end_time
            },
            timeout=10
        )
        data = response.json()

        if not data.get("success"):
            return []

        candles = data.get("result", [])
        return sorted(candles, key=lambda c: c["time"])

    except Exception as e:
        print(f"[ERROR] get_pnf_candles({symbol}): {e}")
        return []


def get_funding_rate(symbol):
    """
    Fetch the latest funding rate for a symbol.
    Uses FUNDING:SYMBOL candle endpoint at 1h resolution.
    Fetches last 2 hours as buffer.
    Returns funding rate as float, or None if unavailable.
    """
    end_time   = int(time.time())
    start_time = end_time - 7200   # 2 hours buffer

    try:
        response = requests.get(
            f"{BASE_URL}/v2/history/candles",
            params={
                "symbol":     f"FUNDING:{symbol}",
                "resolution": "1h",
                "start":      start_time,
                "end":        end_time
            },
            timeout=10
        )
        data = response.json()

        if not data.get("success"):
            return None

        candles = data.get("result", [])
        if not candles:
            return None

        return float(candles[-1]["close"])

    except Exception as e:
        print(f"[ERROR] get_funding_rate({symbol}): {e}")
        return None


def get_oi_data(symbol):
    """
    Fetch OI value (USD) and OI 6H change (USD) from ticker.
    Endpoint: GET /v2/tickers/{symbol}
    Returns (oi_value_usd, oi_change_usd_6h) as floats.
    Returns (0, 0) if unavailable.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/v2/tickers/{symbol}",
            timeout=10
        )
        data = response.json()

        if not data.get("success"):
            return 0, 0

        result           = data.get("result", {})
        oi_value_usd     = float(result.get("oi_value_usd",     0) or 0)
        oi_change_usd_6h = float(result.get("oi_change_usd_6h", 0) or 0)
        return oi_value_usd, oi_change_usd_6h

    except Exception as e:
        print(f"[ERROR] get_oi_data({symbol}): {e}")
        return 0, 0
