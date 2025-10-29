"""
Test script to debug pullback strategy scan with detailed logging.
"""
from datetime import datetime, timedelta
from strategies import PullbackStrategy
from data import DataClient, add_technical_indicators

print("=" * 80)
print("PULLBACK STRATEGY DEBUG TEST")
print("=" * 80)

# Test symbols that showed setups in scan
test_symbols = ['MCD', 'AAPL', 'GOOGL', 'SPY']

client = DataClient()
strategy = PullbackStrategy()

end = datetime.now()
start = end - timedelta(days=100)  # Get 100 days of data

for symbol in test_symbols:
    print(f"\n{'='*80}")
    print(f"TESTING: {symbol}")
    print(f"{'='*80}")
    
    # Fetch data
    data = client.get_ohlcv([symbol], start, end, '1Day')
    
    if symbol not in data:
        print(f"[ERROR] No data fetched for {symbol}")
        continue
    
    df = data[symbol]
    
    print(f"Data fetched: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
    
    # Run scan with debug enabled
    setup = strategy.scan(symbol, df, debug=True)
    
    if setup:
        print(f"\n[SUCCESS] Setup found!")
        print(f"Details: {setup}")
    else:
        print(f"\n[FAILED] No setup found")
    
    print("\n" + "=" * 80)

print("\n" + "=" * 80)
print("DEBUG TEST COMPLETE")
print("=" * 80)
print("\nThis shows exactly where the scan logic is succeeding or failing.")
print("Look for:")
print("  - 'Step X PASSED' messages showing progress")
print("  - 'FAILED' messages showing where it stops")
print("  - Signal conditions to understand why no setup was found")

