# =========================================================
# DELTA CLIENT - Fetches data from Delta Exchange API
# =========================================================

import requests
import time
from config import BASE_URL, CANDLE_RESOLUTION, PUMP_LOOKBACK_HRS


def get_all_meme_symbols():
    """
    Fetch all live perpetual futures symbols tagged as 'meme'
    from Delta Exchange.
    Tag filter is done client-side by checking product_specs.tags
    since the API does not support tag-based query filtering.
    Returns list of symbol strings.
    """
    symbols = []
    page_size = 100
    after = None

    while True:
        params = {
            "contract_types": "perpetual_futures",
            "states": "live",
            "page_size": page_size
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
                print(f"[ERROR] Failed to fetch products: {data}")
                break

            results = data.get("result", [])
            if not results:
                break

            for product in results:
                # Only operational products
                if product.get("trading_status") != "operational":
                    continue

                # Client-side meme tag filter
                tags = product.get("product_specs", {}).get("tags", [])
                if "meme" not in tags:
                    continue

                symbols.append(product["symbol"])

            # Handle pagination
            meta = data.get("meta", {})
            after = meta.get("after")
            if not after:
                break

        except Exception as e:
            print(f"[ERROR] get_all_meme_symbols: {e}")
            break

    print(f"[INFO] Total live meme perpetual symbols found: {len(symbols)}")
    return symbols


def _resolution_to_seconds(resolution):
    """
    Convert resolution string to seconds.
    """
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
    Fetch candles covering PUMP_LOOKBACK_HRS hours for pump detection.
    Returns list of candle dicts with keys: time, open, high, low, close, volume
    """
    resolution = CANDLE_RESOLUTION
    end_time   = int(time.time())
    start_time = end_time - (PUMP_LOOKBACK_HRS * 3600)

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
        print(f"[ERROR] get_pump_candles({symbol}): {e}")
        return []


def get_recent_candles(symbol, count=50):
    """
    Fetch the most recent N candles for reversal pattern detection.
    Returns list of candle dicts.
    """
    resolution     = CANDLE_RESOLUTION
    res_seconds    = _resolution_to_seconds(resolution)
    end_time       = int(time.time())
    start_time     = end_time - (res_seconds * count)

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


def get_funding_rate(symbol):
    """
    Fetch the latest funding rate for a symbol.
    Uses FUNDING:SYMBOL candle endpoint.
    Returns funding rate as float, or None if unavailable.
    """
    end_time   = int(time.time())
    start_time = end_time - 3600  # Last 1 hour is enough

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

        # Latest candle close = current funding rate
        latest_rate = float(candles[-1]["close"])
        return latest_rate

    except Exception as e:
        print(f"[ERROR] get_funding_rate({symbol}): {e}")
        return None


def get_oi_data(symbol):
    """
    Fetch OI value (USD) and OI 6H change (USD) from ticker.
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
        oi_value_usd     = float(result.get("oi_value_usd", 0) or 0)
        oi_change_usd_6h = float(result.get("oi_change_usd_6h", 0) or 0)
        return oi_value_usd, oi_change_usd_6h

    except Exception as e:
        print(f"[ERROR] get_oi_data({symbol}): {e}")
        return 0, 0
