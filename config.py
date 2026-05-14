# =========================================================
# CONFIG FILE - Edit your settings here ONLY
# No need to touch any other file to change bot behavior
# =========================================================

# --- TELEGRAM SETTINGS ---
TELEGRAM_BOT_TOKEN  = "8784919505:AAG2NobvxecZB9EKPiQ0PLTYO8RBXYqvk5Q"   # Paste your bot token here
TELEGRAM_CHAT_ID    = "5026667156"      # Paste your chat ID here

# --- DELTA EXCHANGE API ---
BASE_URL            = "https://api.india.delta.exchange"

# --- PUMP DETECTION ---
PUMP_LOOKBACK_HRS   = 48       # How many hours back to check pump
                               # Change to 24 or 72 as needed
PUMP_THRESHOLD_PCT  = 30       # Minimum % pump to qualify coin
                               # Change to 50, 100, 200 as needed

# --- CANDLE SETTINGS ---
CANDLE_RESOLUTION   = "5m"     # Candle timeframe: 5m, 15m, 30m, 1h

# --- REVERSAL DETECTION ---
REVERSAL_LOOKBACK   = 10       # Candles back to find swing high for SL
                               # More candles = wider stop loss
DOUBLE_TOP_TOLERANCE = 0.005   # 0.5% tolerance for double top pattern
                               # Lower = stricter match, Higher = looser match

# --- VOLUME CONFIRMATION ---
VOLUME_AVG_PERIOD   = 20       # Candles used to calculate average volume

# --- TAKE PROFIT LEVELS ---
TP1_PCT             = 30       # TP1 target: 30% drop from entry
TP2_PCT             = 50       # TP2 target: 50% drop from entry
TP3_PCT             = 70       # TP3 target: 70% drop from entry

# --- SCAN & ALERT SETTINGS ---
SCAN_INTERVAL_MIN   = 15       # How often bot scans in minutes
ALERT_COOLDOWN_HRS  = 4        # Hours before same coin alerted again

# =========================================================
# QUICK CHANGE EXAMPLES
# =========================================================
# Catch bigger pumps only:
#   PUMP_THRESHOLD_PCT   = 100
#
# Stricter double top:
#   DOUBLE_TOP_TOLERANCE = 0.002
#
# Faster signals:
#   CANDLE_RESOLUTION    = "5m"
#   SCAN_INTERVAL_MIN    = 5
#
# Wider scan window:
#   PUMP_LOOKBACK_HRS    = 72
#
# Aggressive TP targets:
#   TP1_PCT = 20
#   TP2_PCT = 40
#   TP3_PCT = 60
#
# Less noise:
#   ALERT_COOLDOWN_HRS   = 8
#   VOLUME_AVG_PERIOD    = 30
# =========================================================

