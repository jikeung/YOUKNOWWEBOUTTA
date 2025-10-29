# Systematic Trading Agent

A modular, safety-first algorithmic trading system built on Alpaca's commission-free brokerage API. This system can scan markets, backtest strategies, paper trade, and (with explicit approval) execute live trades.

**⚠️ IMPORTANT: This is research software. No guarantees of profitability. Past performance does not indicate future results.**

## Features

### Safety First
- **Paper trading by default** - impossible to trade live without double confirmation
- **Live trading guards** - requires both `ALLOW_LIVE_TRADING=true` in `.env` AND `--i-accept-live-risk` CLI flag
- **Hard-coded risk limits** - max 2 positions, 30% per position, 1% risk per trade
- **Liquidity filters** - minimum $2 price, $1M average daily volume
- **Long-only, no leverage** - no shorting, options, or crypto

### Core Capabilities
1. **Market Scanning** - Find setups across a universe of liquid stocks/ETFs
2. **Backtesting** - Vectorized backtests with realistic costs and slippage (0.10% per side)
3. **Paper Trading** - Execute and manage paper trades with full journaling
4. **Live Trading** - Human-in-the-loop control for real money (double-confirmation required)
5. **Trade Journal** - Comprehensive logging (signals, fills, P&L, MAE/MFE, lessons)
6. **Daily Reports** - Markdown reports with equity, positions, win rate, and metrics

### Strategies Included
1. **Momentum Continuation** - Breakout above N-day high with volume confirmation
2. **Breakout-Pullback** - Reentry after pullback to EMA with rising volume

## Project Structure

```
alpacatrading/
├── config.py                 # Configuration and safety toggles
├── data.py                   # Market data access and filtering
├── position_sizing.py        # Risk-based position sizing
├── broker.py                 # Alpaca wrapper with safety guards
├── risk.py                   # Pre-trade and intraday risk checks
├── journal.py                # Trade logging (JSONL/CSV)
├── report.py                 # Daily report generation
├── backtest.py               # Backtesting engine
├── runner.py                 # CLI entrypoint
├── strategies/
│   ├── __init__.py
│   ├── base.py              # Strategy interface
│   ├── momentum.py          # Momentum strategy
│   └── pullback.py          # Pullback strategy
├── tests/
│   ├── test_position_sizing.py
│   ├── test_risk_management.py
│   └── test_broker_safety.py
├── data/                     # Cached data (auto-created)
├── journal/                  # Trade logs (auto-created)
├── reports/                  # Daily reports (auto-created)
├── main.py                   # Simple connection demo
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone or Download

```bash
cd alpacatrading
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Alpaca API Credentials
# Get yours at: https://app.alpaca.markets/paper/dashboard/overview
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# Trading Mode (True = paper, False = live)
PAPER_TRADING=True

# Live Trading Authorization (False by default for safety)
ALLOW_LIVE_TRADING=False
```

### 4. Verify Installation

```bash
python config.py
```

Should display configuration summary without errors.

## Usage

### Market Scanning

Scan for momentum setups:

```bash
python runner.py scan --strategy momentum --timeframe 15Min
```

Scan for pullback setups:

```bash
python runner.py scan --strategy pullback --timeframe 15Min --top 5
```

### Backtesting

Run a backtest on historical data:

```bash
python backtest.py --strategy momentum --start 2024-01-01 --end 2024-12-31 --timeframe 1Day
```

Example output includes:
- Total return, CAGR, max drawdown
- Win rate, profit factor, average R-multiple
- Transaction costs and slippage impact
- Trade-by-trade logs

### Paper Trading

Execute a paper trade:

```bash
python runner.py trade --paper --symbol AAPL --strategy momentum
```

This will:
1. Scan AAPL for a setup
2. Calculate position size based on risk
3. Run pre-trade risk checks
4. Place paper order if approved
5. Log to journal

Dry run (no order placed):

```bash
python runner.py trade --paper --symbol AAPL --strategy momentum --dry-run
```

### Live Trading ⚠️

**CRITICAL: Live trading requires TWO confirmations:**

1. Set `ALLOW_LIVE_TRADING=true` in `.env`
2. Use `--i-accept-live-risk` CLI flag

```bash
python runner.py trade --live --symbol AAPL --strategy momentum --i-accept-live-risk
```

**Warning banner will display before execution.**

### Daily Report

Generate and save a daily report:

```bash
python runner.py report
```

Report includes:
- Account summary (equity, cash, buying power)
- Open positions with P&L
- All-time trading statistics
- Recent trades
- Risk management status

Reports are saved to `reports/YYYY-MM-DD.md`

## Configuration

All risk limits are defined in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITIONS` | 2 | Maximum simultaneous positions |
| `MAX_POSITION_SIZE_PCT` | 0.30 | Max 30% of equity per position |
| `MAX_RISK_PER_TRADE_PCT` | 0.01 | Max 1% equity at risk per trade |
| `MIN_STOCK_PRICE` | $2.00 | Minimum stock price |
| `MIN_AVG_DOLLAR_VOLUME` | $1M | Minimum 20-day avg volume |
| `COMMISSION_PER_TRADE` | $0.00 | Alpaca is commission-free |
| `SLIPPAGE_PCT` | 0.001 | 0.10% slippage per side |

**These limits are hard-coded for safety. Modify with caution.**

## Strategy Details

### Momentum Continuation

**Entry Conditions:**
- Price breaks above 20-day high
- Volume > 1.5x 20-day average
- Price above 20 EMA (trend confirmation)

**Exit Rules:**
- **Stop:** Below breakout level or entry - (ATR × 2.0)
- **Target:** Entry + (Risk × 2.0) = 2R target
- **Trailing:** ATR-based trail after +1R
- **Breakeven:** Move stop to entry at +1R

**Best For:** Intraday to 1-day swings

### Breakout-Pullback

**Entry Conditions:**
- Prior breakout confirmed (20-day high breach)
- Pullback to 20 EMA with declining volume
- Re-break with rising volume

**Exit Rules:**
- **Stop:** Below pullback low or entry - (ATR × 2.0)
- **Target:** Entry + (Risk × 2.0)
- **Trailing:** ATR-based trail after +1.5R
- **Breakeven:** Move stop to entry at +1R

**Best For:** Swing trades (2-5 days)

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

Tests cover:
- Position sizing calculations
- Risk limit enforcement
- Broker safety guards
- Configuration validation

## Journal & Logs

All trading activity is logged to `journal/` directory:

- **signals.jsonl** - Every signal generated (executed, rejected, skipped)
- **trades.jsonl** - Entry/exit details with P&L, MAE/MFE, lessons learned
- **daily.jsonl** - End-of-day summaries

Example journal entry:

```json
{
  "timestamp": "2024-10-27T14:30:00",
  "type": "exit",
  "trade_id": "AAPL_20241027_143000",
  "symbol": "AAPL",
  "exit_price": 158.50,
  "exit_reason": "target",
  "net_pnl": 402.50,
  "r_multiple": 1.62,
  "mae": -50.0,
  "mfe": 450.0,
  "rule_adherence": "yes",
  "lesson_learned": "Strong momentum follow-through as expected"
}
```

## Risk Management Philosophy

This system enforces **conservative risk limits** by design:

1. **Position Limits** - Max 2 positions prevents over-concentration
2. **Position Sizing** - Max 30% per position limits single-stock risk
3. **Risk Per Trade** - Max 1% equity risk per trade protects capital
4. **Liquidity Filters** - Ensures you can enter/exit without excessive slippage
5. **Long-Only** - No shorting reduces complexity and margin risk
6. **No Leverage** - Total exposure cannot exceed equity

**Pre-Trade Checks:**
- Position count limit
- Position size limit
- Risk per trade limit
- Price and liquidity requirements
- Duplicate position check
- Leverage check

**Intraday Monitoring:**
- Large unrealized loss alerts
- Position size drift detection
- Market hours compliance

## Backtesting with Costs

All backtests include:
- **Slippage:** 0.10% per side (0.20% round-trip)
- **Commission:** $0 (Alpaca is commission-free)
- **Stop/Target Modeling:** Uses bar high/low for realistic fills
- **Trailing Stops:** ATR-based trailing implemented
- **Walk-Forward Validation:** Split data into train/test

Backtest results include:
- CAGR, Sharpe ratio, max drawdown
- Win rate, profit factor, average R-multiple
- Trade-by-trade logs with MAE/MFE
- Total cost impact (slippage + commission)

## Troubleshooting

### "No module named alpaca"
You installed the wrong package. Uninstall and install correct one:
```bash
pip uninstall alpaca -y
pip install alpaca-py
```

### "ALPACA_API_KEY not set"
Create a `.env` file with your API credentials. See Installation step 3.

### "Live trading blocked"
This is intentional. To enable live trading:
1. Set `ALLOW_LIVE_TRADING=true` in `.env`
2. Use `--i-accept-live-risk` CLI flag

### "Insufficient data for symbol"
Symbol may not trade on requested timeframe, or Alpaca doesn't have data. Try a different symbol or timeframe.

## Safety Warnings

⚠️ **READ BEFORE LIVE TRADING:**

1. **This is research software** - No warranty, no guarantee of profit
2. **Test extensively in paper mode** - Run for weeks before considering live
3. **Start small** - If you go live, start with minimum capital
4. **Markets are unpredictable** - Past performance ≠ future results
5. **Know your risk** - You can lose money, potentially all of it
6. **Understand the code** - Review every line before trusting it with real money
7. **Monitor actively** - Automated ≠ unattended
8. **Have a kill switch** - Know how to flatten all positions quickly

**The double-confirmation system is your friend. Don't disable it.**

## License & Disclaimer

This software is provided "as-is" for educational and research purposes.

**DISCLAIMER:**
- No warranty or guarantee of any kind
- Not financial advice
- Not investment advice  
- Not a recommendation to buy or sell securities
- Trading involves substantial risk of loss
- Only trade with money you can afford to lose
- The authors are not liable for any losses

**By using this software, you acknowledge and accept all risks.**

## Support & Contributions

This is a reference implementation. Feel free to:
- Fork and modify for your own use
- Add new strategies
- Improve risk management
- Enhance reporting

**Do not** share or trade this system without understanding:
1. The risks involved
2. How every component works
3. The limitations and edge cases

## Additional Resources

- [Alpaca API Docs](https://alpaca.markets/docs/)
- [Alpaca Python SDK](https://github.com/alpacahq/alpaca-py)
- [Risk Management Basics](https://www.investopedia.com/trading/risk-management/)

---

**Built with safety and transparency as core principles.**

*Happy (and careful) trading! 📈*

