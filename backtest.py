"""
Backtesting engine with vectorized execution and transaction cost modeling.
"""
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass

import config
from data import DataClient, add_technical_indicators
from strategies.base import BaseStrategy
from position_sizing import PositionSizer


@dataclass
class BacktestResult:
    """Container for backtest results."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: str
    
    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Returns
    total_return: float
    total_return_pct: float
    cagr: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    
    # Trade metrics
    avg_win: float
    avg_loss: float
    avg_r_multiple: float
    largest_win: float
    largest_loss: float
    
    # Exposure
    avg_exposure: float  # Average % of time in market
    
    # Costs
    total_commission: float
    total_slippage: float
    
    # Equity curve
    equity_curve: pd.Series
    trades: pd.DataFrame
    
    def print_summary(self):
        """Print formatted backtest summary."""
        print("=" * 80)
        print(f"BACKTEST RESULTS: {self.strategy_name}")
        print("=" * 80)
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"Timeframe: {self.timeframe}")
        print()
        
        print("PERFORMANCE")
        print("-" * 80)
        print(f"Total Return: ${self.total_return:,.2f} ({self.total_return_pct:.2%})")
        print(f"CAGR: {self.cagr:.2%}")
        print(f"Max Drawdown: ${self.max_drawdown:,.2f} ({self.max_drawdown_pct:.2%})")
        print(f"Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print()
        
        print("TRADES")
        print("-" * 80)
        print(f"Total Trades: {self.total_trades}")
        print(f"Winners: {self.winning_trades} ({self.win_rate:.1%})")
        print(f"Losers: {self.losing_trades}")
        print(f"Profit Factor: {self.profit_factor:.2f}")
        print(f"Average R-Multiple: {self.avg_r_multiple:.2f}R")
        print()
        
        print("TRADE STATISTICS")
        print("-" * 80)
        print(f"Average Win: ${self.avg_win:,.2f}")
        print(f"Average Loss: ${self.avg_loss:,.2f}")
        print(f"Largest Win: ${self.largest_win:,.2f}")
        print(f"Largest Loss: ${self.largest_loss:,.2f}")
        print()
        
        print("COSTS & EXPOSURE")
        print("-" * 80)
        print(f"Total Commission: ${self.total_commission:.2f}")
        print(f"Total Slippage: ${self.total_slippage:.2f}")
        print(f"Average Exposure: {self.avg_exposure:.1%}")
        print("=" * 80)


class Backtester:
    """Vectorized backtesting engine."""
    
    def __init__(
        self,
        initial_capital: float = 25000.0,
        commission: float = config.COMMISSION_PER_TRADE,
        slippage_pct: float = config.SLIPPAGE_PCT
    ):
        """Initialize backtester.
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade
            slippage_pct: Slippage as percentage
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage_pct = slippage_pct
    
    def run(
        self,
        strategy: BaseStrategy,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1Day'
    ) -> Optional[BacktestResult]:
        """Run backtest for a strategy on a single symbol.
        
        Args:
            strategy: Strategy instance
            symbol: Ticker symbol
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe
        
        Returns:
            BacktestResult or None if insufficient data
        """
        # Fetch data
        client = DataClient()
        data = client.get_ohlcv([symbol], start_date, end_date, timeframe)
        
        if symbol not in data or data[symbol].empty:
            print(f"No data for {symbol}")
            return None
        
        df = data[symbol].copy()
        
        # Add technical indicators
        df = add_technical_indicators(df)
        
        # Generate signals
        df = strategy.generate_signals(df)
        
        # Execute trades
        trades = self._execute_trades(df, strategy)
        
        if trades.empty:
            print(f"No trades generated for {symbol}")
            return None
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(trades)
        
        # Calculate metrics
        result = self._calculate_metrics(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            trades=trades,
            equity_curve=equity_curve
        )
        
        return result
    
    def _execute_trades(self, df: pd.DataFrame, strategy: BaseStrategy) -> pd.DataFrame:
        """Execute trades based on signals with cost modeling.
        
        Args:
            df: DataFrame with signals
            strategy: Strategy instance
        
        Returns:
            DataFrame of executed trades
        """
        trades = []
        equity = self.initial_capital
        
        # Get all entry signals
        signals = df[df['signal'] == 1].copy()
        
        for idx, signal in signals.iterrows():
            entry_price = signal['entry']
            stop_price = signal['stop']
            target_price = signal['target']
            
            if pd.isna(entry_price) or pd.isna(stop_price) or pd.isna(target_price):
                continue
            
            # Apply entry slippage (buy higher)
            entry_price_actual = entry_price * (1 + self.slippage_pct)
            
            # Size position
            sizer = PositionSizer(equity)
            sizing = sizer.calculate_shares(entry_price_actual, stop_price)
            
            if not sizing['valid']:
                continue
            
            shares = sizing['shares']
            position_value = shares * entry_price_actual
            
            # Entry commission
            entry_commission = self.commission
            
            # Find exit
            exit_info = self._find_exit(
                df=df,
                entry_idx=idx,
                entry_price=entry_price_actual,
                stop_price=stop_price,
                target_price=target_price,
                strategy=strategy
            )
            
            if exit_info is None:
                continue
            
            exit_idx, exit_price, exit_reason = exit_info
            
            # Apply exit slippage (sell lower)
            exit_price_actual = exit_price * (1 - self.slippage_pct)
            
            # Exit commission
            exit_commission = self.commission
            
            # Calculate P&L
            gross_pnl = shares * (exit_price_actual - entry_price_actual)
            costs = entry_commission + exit_commission
            net_pnl = gross_pnl - costs
            
            # Update equity
            equity += net_pnl
            
            # Calculate metrics
            risk = entry_price_actual - stop_price
            r_multiple = (exit_price_actual - entry_price_actual) / risk if risk > 0 else 0
            
            # Record trade
            trades.append({
                'entry_date': idx,
                'exit_date': exit_idx,
                'entry_price': entry_price_actual,
                'exit_price': exit_price_actual,
                'shares': shares,
                'position_value': position_value,
                'stop_price': stop_price,
                'target_price': target_price,
                'gross_pnl': gross_pnl,
                'commission': costs,
                'slippage': shares * entry_price * self.slippage_pct * 2,  # Both sides
                'net_pnl': net_pnl,
                'return_pct': net_pnl / position_value,
                'r_multiple': r_multiple,
                'exit_reason': exit_reason,
                'equity_after': equity
            })
        
        return pd.DataFrame(trades)
    
    def _find_exit(
        self,
        df: pd.DataFrame,
        entry_idx: pd.Timestamp,
        entry_price: float,
        stop_price: float,
        target_price: float,
        strategy: BaseStrategy
    ) -> Optional[tuple]:
        """Find exit for a trade.
        
        Args:
            df: Full DataFrame
            entry_idx: Entry timestamp
            entry_price: Entry price
            stop_price: Initial stop price
            target_price: Target price
            strategy: Strategy instance for exit logic
        
        Returns:
            Tuple of (exit_idx, exit_price, exit_reason) or None
        """
        # Get data after entry
        future_data = df.loc[entry_idx:].iloc[1:]  # Skip entry bar
        
        current_stop = stop_price
        
        for idx, bar in future_data.iterrows():
            current_price = bar['close']
            current_atr = bar['atr_14'] if 'atr_14' in bar and not pd.isna(bar['atr_14']) else 0
            
            # Check if target hit (sell at high if reached)
            if bar['high'] >= target_price:
                return (idx, target_price, 'target')
            
            # Check if stop hit (sell at low if breached)
            if bar['low'] <= current_stop:
                return (idx, current_stop, 'stop')
            
            # Update trailing stop if strategy supports it
            if hasattr(strategy, 'check_exit'):
                should_exit, new_stop, reason = strategy.check_exit(
                    entry_price, current_price, current_atr, stop_price
                )
                current_stop = max(current_stop, new_stop)  # Only trail up
                
                if should_exit:
                    return (idx, current_price, reason)
        
        # No exit found in data (still open at end)
        return None
    
    def _calculate_equity_curve(self, trades: pd.DataFrame) -> pd.Series:
        """Calculate equity curve from trades.
        
        Args:
            trades: DataFrame of trades
        
        Returns:
            Series of equity over time
        """
        if trades.empty:
            return pd.Series([self.initial_capital])
        
        # Create equity points at each trade exit
        equity_points = [(trades.iloc[0]['entry_date'], self.initial_capital)]
        
        for _, trade in trades.iterrows():
            equity_points.append((trade['exit_date'], trade['equity_after']))
        
        equity_curve = pd.Series(
            [e for _, e in equity_points],
            index=[d for d, _ in equity_points]
        )
        
        return equity_curve
    
    def _calculate_metrics(
        self,
        strategy: BaseStrategy,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
        trades: pd.DataFrame,
        equity_curve: pd.Series
    ) -> BacktestResult:
        """Calculate performance metrics from trades.
        
        Args:
            strategy: Strategy instance
            symbol: Symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe
            trades: DataFrame of trades
            equity_curve: Equity curve series
        
        Returns:
            BacktestResult
        """
        # Trade statistics
        total_trades = len(trades)
        winning_trades = len(trades[trades['net_pnl'] > 0])
        losing_trades = len(trades[trades['net_pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Returns
        final_equity = equity_curve.iloc[-1]
        total_return = final_equity - self.initial_capital
        total_return_pct = total_return / self.initial_capital
        
        # CAGR
        years = (end_date - start_date).days / 365.25
        cagr = (final_equity / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0
        
        # Drawdown
        running_max = equity_curve.cummax()
        drawdown = running_max - equity_curve
        max_drawdown = drawdown.max()
        max_drawdown_pct = (max_drawdown / running_max[drawdown.idxmax()]) if max_drawdown > 0 else 0
        
        # Sharpe ratio (daily returns)
        returns = equity_curve.pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0
        
        # Profit factor
        gross_profit = trades[trades['net_pnl'] > 0]['net_pnl'].sum()
        gross_loss = abs(trades[trades['net_pnl'] < 0]['net_pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        
        # Trade metrics
        winners = trades[trades['net_pnl'] > 0]
        losers = trades[trades['net_pnl'] < 0]
        
        avg_win = winners['net_pnl'].mean() if not winners.empty else 0
        avg_loss = losers['net_pnl'].mean() if not losers.empty else 0
        avg_r_multiple = trades['r_multiple'].mean()
        largest_win = trades['net_pnl'].max() if not trades.empty else 0
        largest_loss = trades['net_pnl'].min() if not trades.empty else 0
        
        # Exposure
        # Calculate total days in trades vs total days
        total_days = (end_date - start_date).days
        trade_days = sum((trades['exit_date'] - trades['entry_date']).dt.days)
        avg_exposure = trade_days / total_days if total_days > 0 else 0
        
        # Costs
        total_commission = trades['commission'].sum()
        total_slippage = trades['slippage'].sum()
        
        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=cagr,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_r_multiple=avg_r_multiple,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_exposure=avg_exposure,
            total_commission=total_commission,
            total_slippage=total_slippage,
            equity_curve=equity_curve,
            trades=trades
        )


if __name__ == "__main__":
    # Test backtesting
    from strategies import MomentumStrategy
    
    print("Testing Backtest Engine\n")
    
    strategy = MomentumStrategy()
    backtester = Backtester(initial_capital=25000.0)
    
    # Test on a symbol
    end = datetime.now()
    start = datetime(2024, 1, 1)
    
    print(f"Running backtest: {strategy.name} on AAPL")
    print(f"Period: {start.date()} to {end.date()}")
    print()
    
    result = backtester.run(
        strategy=strategy,
        symbol='AAPL',
        start_date=start,
        end_date=end,
        timeframe='1Day'
    )
    
    if result:
        result.print_summary()
        
        print("\nSample Trades:")
        print(result.trades.head(10).to_string())
    else:
        print("Backtest failed or no trades generated")

