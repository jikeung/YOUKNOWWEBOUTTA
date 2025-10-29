"""
Trading runner - CLI entrypoint for scanning, paper trading, and live trading.
"""
import sys
import argparse
from datetime import datetime, timedelta
from typing import Optional

import config
from data import DataClient, get_universe, add_technical_indicators
from strategies import MomentumStrategy, PullbackStrategy
from broker import Broker, LiveTradingError
from position_sizing import PositionSizer
from risk import RiskManager, format_risk_report
from journal import TradeJournal
from report import ReportGenerator


def scan_markets(
    strategy_name: str,
    timeframe: str,
    universe: Optional[list[str]] = None,
    show_top: int = 10
):
    """Scan markets for trading opportunities.
    
    Args:
        strategy_name: 'momentum' or 'pullback'
        timeframe: Data timeframe
        universe: List of symbols (None = default universe)
        show_top: Number of top setups to display
    """
    print("\n" + "=" * 80)
    print(f"MARKET SCAN: {strategy_name.upper()} STRATEGY")
    print("=" * 80)
    print(f"Timeframe: {timeframe}")
    print(f"Scanning universe...")
    
    # Get universe
    if universe is None:
        universe = get_universe()
    
    print(f"Symbols to scan: {len(universe)}")
    
    # Initialize strategy
    if strategy_name == 'momentum':
        strategy = MomentumStrategy()
    elif strategy_name == 'pullback':
        strategy = PullbackStrategy()
    else:
        print(f"[ERROR] Unknown strategy: {strategy_name}")
        return
    
    # Fetch data
    client = DataClient()
    end = datetime.now()
    start = end - timedelta(days=config.LOOKBACK_DAYS)
    
    print(f"\nFetching data for {len(universe)} symbols...")
    data = client.get_ohlcv(universe, start, end, timeframe)
    
    print(f"Data fetched for {len(data)} symbols")
    
    # Scan each symbol
    setups = []
    
    for symbol in universe:
        if symbol not in data:
            continue
        
        df = data[symbol]
        if df.empty or len(df) < 30:
            continue
        
        # Add indicators
        df = add_technical_indicators(df)
        
        # Scan for setup
        setup = strategy.scan(symbol, df)
        
        if setup:
            setups.append(setup)
    
    # Display results
    print("\n" + "-" * 80)
    print(f"FOUND {len(setups)} SETUPS")
    print("-" * 80)
    
    if not setups:
        print("No setups found matching criteria.")
        return
    
    # Sort by confidence
    setups.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Display top setups
    for i, setup in enumerate(setups[:show_top], 1):
        risk = setup['entry'] - setup['stop']
        reward = setup['target'] - setup['entry']
        r_ratio = reward / risk if risk > 0 else 0
        
        print(f"\n{i}. {setup['symbol']} - {setup['setup']}")
        print(f"   Confidence: {setup['confidence']:.1%}")
        print(f"   Entry: ${setup['entry']:.2f}")
        print(f"   Stop: ${setup['stop']:.2f}")
        print(f"   Target: ${setup['target']:.2f}")
        print(f"   Risk: ${risk:.2f} | Reward: ${reward:.2f} | R:R = 1:{r_ratio:.1f}")
        print(f"   Notes: {setup['notes']}")
    
    if len(setups) > show_top:
        print(f"\n... and {len(setups) - show_top} more setups")
    
    print("\n" + "=" * 80)


def execute_trade(
    symbol: str,
    strategy_name: str,
    paper: bool,
    cli_confirm: bool,
    dry_run: bool = False
):
    """Execute a trade based on strategy signal.
    
    Args:
        symbol: Symbol to trade
        strategy_name: Strategy name
        paper: Paper trading mode
        cli_confirm: CLI confirmation for live trading
        dry_run: If True, simulate without actual execution
    """
    print("\n" + "=" * 80)
    print(f"TRADE EXECUTION: {symbol}")
    print("=" * 80)
    
    # Initialize components
    try:
        broker = Broker(paper=paper, cli_confirm=cli_confirm)
    except LiveTradingError as e:
        print(f"\n{e}\n")
        return
    
    # Get account info
    account = broker.get_account()
    equity = account.get('equity', 0)
    
    if equity <= 0:
        print("[ERROR] Invalid account equity")
        return
    
    print(f"Account Equity: ${equity:,.2f}")
    
    # Initialize strategy
    if strategy_name == 'momentum':
        strategy = MomentumStrategy()
    elif strategy_name == 'pullback':
        strategy = PullbackStrategy()
    else:
        print(f"[ERROR] Unknown strategy: {strategy_name}")
        return
    
    # Fetch data
    client = DataClient()
    end = datetime.now()
    start = end - timedelta(days=config.LOOKBACK_DAYS)
    
    data = client.get_ohlcv([symbol], start, end, '15Min')
    
    if symbol not in data:
        print(f"[ERROR] No data for {symbol}")
        return
    
    df = data[symbol]
    df = add_technical_indicators(df)
    
    # Scan for setup
    setup = strategy.scan(symbol, df)
    
    if not setup:
        print(f"[ERROR] No valid setup for {symbol}")
        return
    
    # Create trade plan
    print(f"\n[SUCCESS] Setup found: {setup['setup']}")
    print(f"   Confidence: {setup['confidence']:.1%}")
    
    # Size position
    sizer = PositionSizer(equity)
    sizing = sizer.calculate_shares(setup['entry'], setup['stop'])
    
    if not sizing['valid']:
        print(f"[ERROR] Position sizing failed: {sizing['reason']}")
        return
    
    # Risk checks
    risk_mgr = RiskManager(equity)
    positions = broker.get_positions()
    
    approved, reasons = risk_mgr.check_pre_trade(
        symbol=symbol,
        entry_price=setup['entry'],
        position_value=sizing['position_value'],
        risk_dollars=sizing['risk_dollars'],
        current_positions=positions
    )
    
    # Display risk check
    print(format_risk_report(approved, reasons, setup))
    
    if not approved:
        print("\n[ERROR] Trade rejected by risk management")
        return
    
    # Display trade plan
    print("\n[TRADE PLAN]")
    print("-" * 80)
    print(f"Symbol: {symbol}")
    print(f"Strategy: {strategy_name}")
    print(f"Shares: {sizing['shares']}")
    print(f"Entry: ${setup['entry']:.2f}")
    print(f"Stop: ${setup['stop']:.2f}")
    print(f"Target: ${setup['target']:.2f}")
    print(f"Position Value: ${sizing['position_value']:,.2f} ({sizing['position_pct']:.1%} of equity)")
    print(f"Risk: ${sizing['risk_dollars']:.2f} ({sizing['risk_pct']:.2%} of equity)")
    print("-" * 80)
    
    if dry_run:
        print("\n[SEARCH] DRY RUN - No order placed")
        return
    
    # Execute trade
    print("\n[LAUNCH] Placing order...")
    
    # Use limit order at entry price
    order = broker.place_order(
        symbol=symbol,
        side='buy',
        qty=sizing['shares'],
        order_type='limit',
        limit_price=setup['entry'],
        time_in_force='day'
    )
    
    if order:
        print(f"[SUCCESS] Order placed successfully: {order['order_id']}")
        
        # Log to journal
        journal = TradeJournal()
        
        # Log signal
        journal.log_signal(
            timestamp=datetime.now(),
            symbol=symbol,
            strategy=strategy_name,
            setup=setup['setup'],
            entry=setup['entry'],
            stop=setup['stop'],
            target=setup['target'],
            confidence=setup['confidence'],
            action_taken='executed',
            notes=setup['notes']
        )
        
        # Log entry (if filled immediately - in practice, check order status)
        trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        journal.log_entry(
            timestamp=datetime.now(),
            trade_id=trade_id,
            symbol=symbol,
            strategy=strategy_name,
            shares=sizing['shares'],
            entry_price=setup['entry'],
            stop_price=setup['stop'],
            target_price=setup['target'],
            position_value=sizing['position_value'],
            risk_dollars=sizing['risk_dollars'],
            risk_pct=sizing['risk_pct'],
            order_id=order['order_id']
        )
        
        print(f"[NOTE] Trade logged: {trade_id}")
    else:
        print("[ERROR] Order failed")
        
        # Log rejected signal
        journal = TradeJournal()
        journal.log_signal(
            timestamp=datetime.now(),
            symbol=symbol,
            strategy=strategy_name,
            setup=setup['setup'],
            entry=setup['entry'],
            stop=setup['stop'],
            target=setup['target'],
            confidence=setup['confidence'],
            action_taken='rejected',
            rejection_reason='Order placement failed'
        )


def generate_report():
    """Generate and display daily report."""
    print("\n" + "=" * 80)
    print("GENERATING DAILY REPORT")
    print("=" * 80)
    
    # Initialize broker (paper mode for reporting)
    broker = Broker(paper=True)
    
    # Get account and positions
    account = broker.get_account()
    positions = broker.get_positions()
    
    # Initialize journal and report generator
    journal = TradeJournal()
    generator = ReportGenerator()
    
    # Generate report
    report = generator.generate_daily_report(
        report_date=datetime.now().date(),
        account_info=account,
        positions=positions,
        journal=journal,
        save=True
    )
    
    # Print console summary
    stats = journal.get_statistics()
    generator.print_console_summary(account, positions, stats)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Trading System - Scan, Backtest, and Trade",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan markets for momentum setups
  python runner.py scan --strategy momentum --timeframe 15Min
  
  # Execute paper trade
  python runner.py trade --paper --symbol AAPL --strategy momentum
  
  # Execute LIVE trade (requires env var + CLI flag)
  python runner.py trade --live --symbol AAPL --strategy momentum --i-accept-live-risk
  
  # Generate daily report
  python runner.py report

Safety:
  Live trading requires BOTH:
    1. ALLOW_LIVE_TRADING=true in .env file
    2. --i-accept-live-risk CLI flag
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan markets for setups')
    scan_parser.add_argument('--strategy', required=True, choices=['momentum', 'pullback'],
                            help='Strategy to use')
    scan_parser.add_argument('--timeframe', default='15Min',
                            help='Data timeframe (default: 15Min)')
    scan_parser.add_argument('--top', type=int, default=10,
                            help='Number of top setups to show (default: 10)')
    
    # Trade command
    trade_parser = subparsers.add_parser('trade', help='Execute a trade')
    trade_parser.add_argument('--symbol', required=True, help='Symbol to trade')
    trade_parser.add_argument('--strategy', required=True, choices=['momentum', 'pullback'],
                             help='Strategy to use')
    
    trade_mode = trade_parser.add_mutually_exclusive_group(required=True)
    trade_mode.add_argument('--paper', action='store_true', help='Paper trading mode')
    trade_mode.add_argument('--live', action='store_true', help='Live trading mode')
    
    trade_parser.add_argument('--i-accept-live-risk', action='store_true',
                             help='Confirmation flag for live trading')
    trade_parser.add_argument('--dry-run', action='store_true',
                             help='Simulate without executing')
    
    # Report command
    subparsers.add_parser('report', help='Generate daily report')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Validate config
    errors = config.validate_config()
    if errors:
        print("[ERROR] Configuration Errors:")
        for error in errors:
            print(f"   {error}")
        return
    
    # Execute command
    if args.command == 'scan':
        scan_markets(
            strategy_name=args.strategy,
            timeframe=args.timeframe,
            show_top=args.top
        )
    
    elif args.command == 'trade':
        execute_trade(
            symbol=args.symbol,
            strategy_name=args.strategy,
            paper=args.paper,
            cli_confirm=args.i_accept_live_risk,
            dry_run=args.dry_run
        )
    
    elif args.command == 'report':
        generate_report()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING]  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

