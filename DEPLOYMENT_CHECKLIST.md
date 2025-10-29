# Deployment Checklist

Before using this trading system, complete these steps:

## ✅ Pre-Deployment

### 1. Environment Setup
- [ ] Python 3.8+ installed
- [ ] `pip install -r requirements.txt` completed successfully
- [ ] `.env` file created with valid Alpaca API keys
- [ ] API keys verified with `python main.py`

### 2. Configuration Review
- [ ] Read and understand `config.py` risk limits
- [ ] Confirm `PAPER_TRADING=True` in `.env`
- [ ] Confirm `ALLOW_LIVE_TRADING=False` in `.env`
- [ ] Review and accept default risk parameters:
  - Max 2 positions
  - Max 30% position size
  - Max 1% risk per trade

### 3. Testing
- [ ] Run unit tests: `pytest tests/ -v`
- [ ] All tests pass
- [ ] No configuration errors reported

## ✅ Paper Trading Phase

### Week 1: Learning & Validation
- [ ] Run `python runner.py scan --strategy momentum --timeframe 15Min`
- [ ] Review scan results and understand setups
- [ ] Run `python backtest.py` to see historical performance
- [ ] Review `SAMPLE_BACKTEST_REPORT.md` to understand metrics
- [ ] Execute 2-3 paper trades using dry-run mode
- [ ] Review journal logs in `journal/` directory

### Week 2-4: Active Paper Trading
- [ ] Execute 10+ paper trades (without dry-run)
- [ ] Monitor trades daily using `python runner.py report`
- [ ] Review journal entries after each trade
- [ ] Verify risk management is working as expected
- [ ] Check that stops and targets are being hit appropriately
- [ ] Calculate actual win rate and average R-multiple
- [ ] Compare paper results to backtest results

### Week 4: System Validation
- [ ] Paper trading equity curve is positive (or understand why not)
- [ ] No unexpected behavior or errors encountered
- [ ] Risk limits never violated
- [ ] Comfortable with strategy logic
- [ ] Comfortable with position sizing
- [ ] Comfortable with exit management

## ⚠️ Before Live Trading (OPTIONAL - NOT RECOMMENDED)

### Final Checks
- [ ] **Minimum 4 weeks** of successful paper trading
- [ ] Win rate ≥ 50% on paper account
- [ ] Average R-multiple ≥ 1.0 on paper account
- [ ] Understand every line of code in:
  - `config.py`
  - `position_sizing.py`
  - `risk.py`
  - `broker.py`
- [ ] Read and accept all risks in README.md
- [ ] Have emergency plan to flatten all positions
- [ ] Know how to contact broker support
- [ ] Only using capital you can afford to lose
- [ ] Emotionally prepared to lose money

### Live Trading Authorization (If Proceeding)
- [ ] Update `ALLOW_LIVE_TRADING=true` in `.env`
- [ ] Start with MINIMUM capital (< $1,000)
- [ ] Set calendar reminder to review trades daily
- [ ] Set alert for large losses
- [ ] Plan to monitor first 10 live trades closely

## 🚨 Stop Trading Immediately If:
- [ ] Losing more than 5% of account in a day
- [ ] Risk limits being violated
- [ ] Unexpected errors occurring
- [ ] Emotional decision-making happening
- [ ] Not understanding why trades are winning/losing

## 📊 Ongoing Monitoring

### Daily
- [ ] Check positions and P&L
- [ ] Run `python runner.py report`
- [ ] Review journal entries
- [ ] Monitor for risk alerts

### Weekly
- [ ] Review all closed trades
- [ ] Calculate win rate and average R
- [ ] Check equity curve trend
- [ ] Verify strategy performance matches expectations
- [ ] Review and learn from losses

### Monthly
- [ ] Full performance review
- [ ] Compare to benchmark (SPY)
- [ ] Evaluate if strategy is still working
- [ ] Consider adjustments if needed
- [ ] Update journal with insights

## ⚠️ CRITICAL REMINDERS

1. **Paper trading is free and risk-free** - use it extensively
2. **This is research software** - no guarantees
3. **Markets are unpredictable** - past performance ≠ future results
4. **Start small** - if going live, start with minimum capital
5. **Have a kill switch** - know how to flatten all positions instantly
6. **Don't trade on emotion** - follow the system rules
7. **Keep learning** - markets evolve, strategies must adapt

---

## Support Resources

- **Alpaca Docs:** https://alpaca.markets/docs/
- **Alpaca Support:** support@alpaca.markets
- **Python Docs:** https://docs.python.org/3/
- **Risk Management:** https://www.investopedia.com/trading/risk-management/

---

**Sign below when you've completed paper trading and understand all risks:**

Date: ________________

Signature: ________________

**I understand that:**
- This software has no warranty
- I can lose money, potentially all of it
- Past performance does not guarantee future results
- I am solely responsible for my trading decisions
- The authors are not liable for any losses

---

*Keep this checklist and refer to it regularly.*

