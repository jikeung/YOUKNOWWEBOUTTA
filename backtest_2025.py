"""
Backtest trading strategies on 2025 data (Jan 1 to Oct 27, 2025)
Starting capital: $100,000
"""
from datetime import datetime
from strategies import MomentumStrategy, PullbackStrategy
from backtest import Backtester
import pandas as pd

print("=" * 80)
print("2025 BACKTEST: Testing Trading Strategies")
print("=" * 80)
print(f"Period: January 1, 2025 to October 27, 2025")
print(f"Starting Capital: $100,000.00")
print(f"Includes realistic costs: 0.10% slippage per side")
print("=" * 80)

# Test symbols (diverse set)
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY', 'QQQ']
strategies = [
    ('Momentum', MomentumStrategy()),
    ('Pullback', PullbackStrategy())
]

results_summary = []

for strategy_name, strategy in strategies:
    print(f"\n{'='*80}")
    print(f"TESTING: {strategy_name.upper()} STRATEGY")
    print(f"{'='*80}")
    
    strategy_total_pnl = 0
    strategy_total_trades = 0
    strategy_winning_trades = 0
    best_symbol = None
    best_pnl = float('-inf')
    
    for symbol in symbols:
        print(f"\n{symbol}:", end=" ")
        
        backtester = Backtester(initial_capital=100000.0)
        
        result = backtester.run(
            strategy=strategy,
            symbol=symbol,
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 10, 27),
            timeframe='1Day'
        )
        
        if result and result.total_trades > 0:
            strategy_total_pnl += result.total_return
            strategy_total_trades += result.total_trades
            strategy_winning_trades += result.winning_trades
            
            if result.total_return > best_pnl:
                best_pnl = result.total_return
                best_symbol = symbol
            
            # Print summary
            print(f"{result.total_trades} trades, ${result.total_return:,.2f} P&L, {result.win_rate:.1%} win rate")
            
            results_summary.append({
                'Strategy': strategy_name,
                'Symbol': symbol,
                'Trades': result.total_trades,
                'Winners': result.winning_trades,
                'Win_Rate': result.win_rate,
                'PnL': result.total_return,
                'Return_Pct': result.total_return_pct,
                'Avg_R': result.avg_r_multiple,
                'Slippage': result.total_slippage
            })
        else:
            print("No trades")
    
    # Strategy summary
    print(f"\n{'-'*80}")
    print(f"{strategy_name} Strategy Summary:")
    print(f"  Total Trades: {strategy_total_trades}")
    print(f"  Total P&L: ${strategy_total_pnl:,.2f}")
    print(f"  Winning Trades: {strategy_winning_trades}")
    if strategy_total_trades > 0:
        print(f"  Overall Win Rate: {strategy_winning_trades/strategy_total_trades:.1%}")
    print(f"  Best Symbol: {best_symbol} (${best_pnl:,.2f})")

# Overall Summary
print(f"\n{'='*80}")
print("OVERALL RESULTS - 2025 BACKTEST")
print(f"{'='*80}")

df_results = pd.DataFrame(results_summary)

if not df_results.empty:
    print("\nDetailed Results by Strategy and Symbol:")
    print("-" * 80)
    print(df_results.to_string(index=False))
    
    print(f"\n{'='*80}")
    print("FINAL ACCOUNT BALANCE SCENARIOS")
    print(f"{'='*80}")
    
    for strategy_name in ['Momentum', 'Pullback']:
        strategy_df = df_results[df_results['Strategy'] == strategy_name]
        if not strategy_df.empty:
            total_pnl = strategy_df['PnL'].sum()
            total_trades = strategy_df['Trades'].sum()
            total_winners = strategy_df['Winners'].sum()
            final_balance = 100000 + total_pnl
            
            print(f"\n{strategy_name} Strategy - Trading ALL Symbols:")
            print(f"  Starting Capital: $100,000.00")
            print(f"  Total P&L: ${total_pnl:,.2f}")
            print(f"  Final Balance: ${final_balance:,.2f}")
            print(f"  Return: {(total_pnl/100000)*100:.2f}%")
            print(f"  Total Trades: {total_trades}")
            print(f"  Win Rate: {(total_winners/total_trades)*100:.1f}%")
    
    # Best overall symbol
    best_row = df_results.loc[df_results['PnL'].idxmax()]
    print(f"\n{'-'*80}")
    print("BEST SINGLE STRATEGY+SYMBOL COMBINATION:")
    print(f"  {best_row['Strategy']} on {best_row['Symbol']}")
    print(f"  Starting: $100,000.00")
    print(f"  Final Balance: ${100000 + best_row['PnL']:,.2f}")
    print(f"  Return: {best_row['Return_Pct']:.2%}")
    print(f"  Trades: {best_row['Trades']}, Win Rate: {best_row['Win_Rate']:.1%}")
    
    # Combined approach
    total_all_pnl = df_results['PnL'].sum()
    total_all_trades = df_results['Trades'].sum()
    print(f"\n{'-'*80}")
    print("COMBINED (Both Strategies on All Symbols):")
    print(f"  Starting: $100,000.00")
    print(f"  Total P&L: ${total_all_pnl:,.2f}")
    print(f"  Final Balance: ${100000 + total_all_pnl:,.2f}")
    print(f"  Return: {(total_all_pnl/100000)*100:.2f}%")
    print(f"  Total Trades: {total_all_trades}")
    
else:
    print("No trades generated in this period")

print(f"\n{'='*80}")
print("NOTES:")
print("  - These results include 0.10% slippage per side (realistic)")
print("  - Past performance does NOT guarantee future results")
print("  - This is for research/educational purposes only")
print("  - Always paper trade extensively before going live")
print(f"{'='*80}\n")

