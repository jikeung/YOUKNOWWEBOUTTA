# Quick Start Guide

Get up and running in 5 minutes.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get API Keys

1. Go to [Alpaca Paper Trading](https://app.alpaca.markets/paper/dashboard/overview)
2. Sign up for free paper trading account
3. Navigate to "Your API Keys"
4. Click "Generate New Key"
5. Copy your **API Key** and **Secret Key**

## Step 3: Configure

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and paste your credentials:

```env
ALPACA_API_KEY=your_actual_key_here
ALPACA_SECRET_KEY=your_actual_secret_here
PAPER_TRADING=True
ALLOW_LIVE_TRADING=False
```

## Step 4: Test Connection

```bash
python main.py
```

You should see:
```
✓ Successfully connected to Alpaca API!
Account Information:
  Cash: $100,000.00
  ...
```

## Step 5: Try the System

### Scan for setups:
```bash
python runner.py scan --strategy momentum --timeframe 15Min
```

### Paper trade (dry run):
```bash
python runner.py trade --paper --symbol AAPL --strategy momentum --dry-run
```

### Run a backtest:
```bash
python backtest.py
```

### Generate a report:
```bash
python runner.py report
```

## Step 6: Read the Docs

Open `README.md` for complete documentation.

## Troubleshooting

**"No module named alpaca"**
```bash
pip uninstall alpaca -y
pip install alpaca-py
```

**"ALPACA_API_KEY not set"**
- Make sure `.env` file exists
- Check that keys are correct (no quotes, no spaces)

**"Insufficient data"**
- Market might be closed
- Try a different symbol (AAPL, MSFT, SPY)
- Try a different timeframe (1Day instead of 15Min)

## Safety Reminder

⚠️ **This is paper trading by default** - no real money at risk.

To enable live trading (not recommended until thoroughly tested):
1. Set `ALLOW_LIVE_TRADING=true` in `.env`
2. Use `--i-accept-live-risk` CLI flag
3. Understand all risks involved

---

**You're all set! Happy testing! 📈**

