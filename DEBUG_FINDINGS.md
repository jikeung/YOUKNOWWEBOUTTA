# Debug Findings - Pullback Strategy

## Summary

The pullback strategy scan method is working **correctly**. Setups appear and disappear as market conditions change in real-time.

## What We Discovered

### Debug Logs Show:
- ✅ Data is fetched successfully (71 bars)
- ✅ Indicators are calculated correctly
- ✅ Signals ARE being generated (4-6 per symbol)
- ✅ Recent signals found on Oct 24 and Oct 27
- ❌ **But NO signals on the current bar (Oct 29)**

### Why No Current Signals:

**Missing Conditions on Oct 29:**
| Symbol | Price Rising | Volume Rising | Result |
|--------|--------------|---------------|---------|
| MCD | ✗ | ✗ | No signal |
| AAPL | ✗ | ✗ | No signal |
| GOOGL | ✓ | ✗ | No signal (needs BOTH) |
| SPY | ✗ | ✗ | No signal |

## The Gap Between Scan and Execution

### When You Scan:
```
Time: Earlier in the day or previous day
Data: Shows setups that existed at that time
Result: "Found 3 setups!"
```

### When You Execute:
```
Time: Later (market has moved)
Data: Fetches LATEST data
Result: Setup no longer exists on current bar
Action: Correctly rejects the trade
```

## This is CORRECT Behavior

### Why It's Good:
1. **Prevents trading stale signals**
2. **Validates conditions in real-time**
3. **Protects from market changes**
4. **Only trades current opportunities**

### Why Backtest Works:
- Backtesting scans every bar historically
- Finds setups as they occur
- Executes on the same bar
- No time delay between scan and execution

## Solutions

### Option 1: End-of-Day Workflow
```bash
# After market close (4:00 PM ET)
python runner.py scan --strategy pullback --timeframe 1Day

# Record top setups for tomorrow

# Next morning (9:20 AM ET) - Verify
python runner.py scan --strategy pullback --timeframe 1Day

# If setup persists, execute at 9:30 AM
python runner.py trade --paper --symbol MCD --strategy pullback
```

### Option 2: Intraday Monitoring
```bash
# Monitor continuously
# Execute immediately when setup appears
watch -n 300 'python runner.py scan --strategy pullback --timeframe 1Day'

# When setup found:
python runner.py trade --paper --symbol [SYMBOL] --strategy pullback
```

### Option 3: Use Shorter Timeframes
```bash
# Try 15-minute or 1-hour timeframes
# Setups persist longer intraday
python runner.py scan --strategy pullback --timeframe 15Min
```

## Debug Logging Added

### New Feature:
The pullback strategy scan method now accepts a `debug=True` parameter:

```python
from strategies import PullbackStrategy
strategy = PullbackStrategy()
setup = strategy.scan(symbol='AAPL', df=data, debug=True)
```

### What It Shows:
1. **Step 1**: Data validation (shape, date range, last close)
2. **Step 2**: Indicator calculation (EMA, ATR, volume, etc.)
3. **Step 3**: Signal generation (how many signals found)
4. **Step 4**: Last bar check (signal value, recent signals)
5. **Step 5**: Entry/stop/target extraction
6. **Step 6**: Confidence calculation

### When It Fails:
Shows exactly WHY:
- Which condition is missing
- What the current values are
- What's needed for a signal

## Test Results

### Symbols Tested (Oct 29, 2025):
- **MCD**: 4 signals in data, last on Oct 27, none on Oct 29
- **AAPL**: 6 signals in data, last on Oct 27, none on Oct 29
- **GOOGL**: 6 signals in data, last on Oct 27, none on Oct 29
- **SPY**: 6 signals in data, last on Oct 24, none on Oct 29

**Conclusion:** All setups from scan have resolved or expired.

## Recommendations

### For Paper Trading:
1. ✅ Scan at end of day
2. ✅ Verify setup next morning
3. ✅ Execute if still valid
4. ✅ Use limit orders at entry price

### For Live Trading:
1. ✅ Only trade after 4+ weeks paper trading
2. ✅ Confirm setup exists at execution time
3. ✅ Have a plan if setup disappears
4. ✅ Start with minimal capital

## Key Takeaway

> **The system is working correctly. Setups are time-sensitive and must be traded when they exist, not hours or days later.**

This is actually a **feature, not a bug** - it protects you from trading outdated signals!

---

*Debug logs added: October 29, 2025*  
*Test script: `test_pullback_debug.py`*

