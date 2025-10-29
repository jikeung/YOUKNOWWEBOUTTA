"""
Configuration module for trading system.
Loads environment variables and defines safety limits, risk parameters, and system defaults.
"""
import os
from typing import Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# API CREDENTIALS
# ============================================================================
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')

# ============================================================================
# SAFETY TOGGLES - LIVE TRADING REQUIRES BOTH ENV VAR AND CLI FLAG
# ============================================================================
PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'
ALLOW_LIVE_TRADING = os.getenv('ALLOW_LIVE_TRADING', 'False').lower() == 'true'

# ============================================================================
# RISK LIMITS (HARD CONSTRAINTS)
# ============================================================================
MAX_POSITIONS = 2  # Maximum number of open positions
MAX_POSITION_SIZE_PCT = 0.30  # Max 30% of equity per position
MAX_RISK_PER_TRADE_PCT = 0.01  # Max 1% of equity at risk per trade
MIN_STOCK_PRICE = 2.0  # Minimum stock price ($)
MIN_AVG_DOLLAR_VOLUME = 1_000_000  # Minimum 20-day average dollar volume ($)

# ============================================================================
# TRANSACTION COSTS
# ============================================================================
COMMISSION_PER_TRADE = 0.0  # Alpaca has 0 commissions
SLIPPAGE_PCT = 0.001  # 0.10% slippage per side (buy or sell)

# ============================================================================
# MARKET CONSTRAINTS
# ============================================================================
TRADING_MODE: Literal['long_only', 'short_only', 'both'] = 'long_only'
LEVERAGE_ALLOWED = False
SHORTING_ALLOWED = False
OPTIONS_ALLOWED = False
CRYPTO_ALLOWED = False
MARKET_HOURS_ONLY = True  # Only trade during regular market hours

# ============================================================================
# DATA SETTINGS
# ============================================================================
LOOKBACK_DAYS = 100  # Days of historical data to fetch for indicators
TIMEFRAME_OPTIONS = ['1Min', '5Min', '15Min', '1Hour', '1Day']
DEFAULT_TIMEFRAME = '15Min'

# ============================================================================
# STRATEGY DEFAULTS
# ============================================================================
# Momentum strategy
MOMENTUM_LOOKBACK = 20  # days for high detection
MOMENTUM_VOLUME_MULT = 1.5  # volume must be 1.5x average
MOMENTUM_ATR_STOP_MULT = 2.0  # stop at entry - (ATR * multiplier)
MOMENTUM_TARGET_R = 2.0  # target = entry + (risk * R)
MOMENTUM_TRAIL_R = 1.0  # start trailing after +1R

# Pullback strategy  
PULLBACK_EMA_PERIOD = 20
PULLBACK_VOLUME_DECLINE = 0.8  # pullback volume < 80% of breakout
PULLBACK_ATR_STOP_MULT = 2.0
PULLBACK_TARGET_R = 2.0
PULLBACK_TRAIL_R = 1.5

# ============================================================================
# PATHS
# ============================================================================
DATA_DIR = 'data'
JOURNAL_DIR = 'journal'
REPORTS_DIR = 'reports'
TESTS_DIR = 'tests'

# Ensure directories exist
for directory in [DATA_DIR, JOURNAL_DIR, REPORTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ============================================================================
# VALIDATION
# ============================================================================
def validate_config() -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    if not ALPACA_API_KEY:
        errors.append("ALPACA_API_KEY not set in environment")
    if not ALPACA_SECRET_KEY:
        errors.append("ALPACA_SECRET_KEY not set in environment")
    
    if MAX_POSITION_SIZE_PCT <= 0 or MAX_POSITION_SIZE_PCT > 1:
        errors.append(f"MAX_POSITION_SIZE_PCT must be between 0 and 1, got {MAX_POSITION_SIZE_PCT}")
    
    if MAX_RISK_PER_TRADE_PCT <= 0 or MAX_RISK_PER_TRADE_PCT > 0.1:
        errors.append(f"MAX_RISK_PER_TRADE_PCT must be between 0 and 0.1, got {MAX_RISK_PER_TRADE_PCT}")
    
    if MAX_POSITIONS < 1:
        errors.append(f"MAX_POSITIONS must be at least 1, got {MAX_POSITIONS}")
    
    return errors


def print_config_summary():
    """Print configuration summary for verification."""
    print("=" * 70)
    print("TRADING SYSTEM CONFIGURATION")
    print("=" * 70)
    print(f"Mode: {'PAPER TRADING' if PAPER_TRADING else 'LIVE TRADING'}")
    print(f"Live Trading Allowed: {ALLOW_LIVE_TRADING}")
    print(f"\nRisk Limits:")
    print(f"  Max Positions: {MAX_POSITIONS}")
    print(f"  Max Position Size: {MAX_POSITION_SIZE_PCT * 100}% of equity")
    print(f"  Max Risk Per Trade: {MAX_RISK_PER_TRADE_PCT * 100}% of equity")
    print(f"  Min Stock Price: ${MIN_STOCK_PRICE}")
    print(f"  Min Avg Dollar Volume: ${MIN_AVG_DOLLAR_VOLUME:,.0f}")
    print(f"\nTransaction Costs:")
    print(f"  Commission: ${COMMISSION_PER_TRADE}")
    print(f"  Slippage: {SLIPPAGE_PCT * 100}% per side")
    print(f"\nConstraints:")
    print(f"  Trading Mode: {TRADING_MODE}")
    print(f"  Leverage: {'Yes' if LEVERAGE_ALLOWED else 'No'}")
    print(f"  Shorting: {'Yes' if SHORTING_ALLOWED else 'No'}")
    print(f"  Market Hours Only: {'Yes' if MARKET_HOURS_ONLY else 'No'}")
    print("=" * 70)


if __name__ == "__main__":
    # Validate and print config
    errors = validate_config()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  [ERROR] {error}")
    else:
        print("[SUCCESS] Configuration valid")
    
    print()
    print_config_summary()

