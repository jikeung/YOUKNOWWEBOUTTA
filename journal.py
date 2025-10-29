"""
Trade journal module - comprehensive logging of all trading activity.
Logs signals, fills, P&L, MAE/MFE, and rule adherence.
"""
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import config


class TradeJournal:
    """Log and track all trading activity."""
    
    def __init__(
        self,
        journal_dir: str = config.JOURNAL_DIR,
        format: Literal['jsonl', 'csv'] = 'jsonl'
    ):
        """Initialize trade journal.
        
        Args:
            journal_dir: Directory for journal files
            format: Output format ('jsonl' or 'csv')
        """
        self.journal_dir = Path(journal_dir)
        self.journal_dir.mkdir(exist_ok=True)
        self.format = format
        
        # Create separate files for signals, trades, and daily logs
        self.signals_file = self.journal_dir / f"signals.{format}"
        self.trades_file = self.journal_dir / f"trades.{format}"
        self.daily_file = self.journal_dir / f"daily.{format}"
    
    def log_signal(
        self,
        timestamp: datetime,
        symbol: str,
        strategy: str,
        setup: str,
        entry: float,
        stop: float,
        target: float,
        confidence: float,
        action_taken: Literal['executed', 'rejected', 'skipped'],
        rejection_reason: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Log a trading signal.
        
        Args:
            timestamp: Signal timestamp
            symbol: Ticker symbol
            strategy: Strategy name
            setup: Setup type
            entry: Entry price
            stop: Stop price
            target: Target price
            confidence: Signal confidence (0-1)
            action_taken: What happened with the signal
            rejection_reason: Why signal was rejected (if applicable)
            notes: Additional notes
        """
        record = {
            'timestamp': timestamp.isoformat(),
            'type': 'signal',
            'symbol': symbol,
            'strategy': strategy,
            'setup': setup,
            'entry': entry,
            'stop': stop,
            'target': target,
            'risk_per_share': entry - stop,
            'reward_per_share': target - entry,
            'r_ratio': (target - entry) / (entry - stop) if entry > stop else 0,
            'confidence': confidence,
            'action_taken': action_taken,
            'rejection_reason': rejection_reason or '',
            'notes': notes or ''
        }
        
        self._write_record(self.signals_file, record)
        print(f"[NOTE] Signal logged: {symbol} {setup} - {action_taken}")
    
    def log_entry(
        self,
        timestamp: datetime,
        trade_id: str,
        symbol: str,
        strategy: str,
        shares: int,
        entry_price: float,
        stop_price: float,
        target_price: float,
        position_value: float,
        risk_dollars: float,
        risk_pct: float,
        order_id: Optional[str] = None
    ):
        """Log trade entry.
        
        Args:
            timestamp: Entry timestamp
            trade_id: Unique trade identifier
            symbol: Ticker symbol
            strategy: Strategy name
            shares: Number of shares
            entry_price: Actual entry price (with slippage)
            stop_price: Stop loss price
            target_price: Target price
            position_value: Total position value
            risk_dollars: Dollar risk
            risk_pct: Risk as % of equity
            order_id: Broker order ID
        """
        record = {
            'timestamp': timestamp.isoformat(),
            'type': 'entry',
            'trade_id': trade_id,
            'symbol': symbol,
            'strategy': strategy,
            'shares': shares,
            'entry_price': entry_price,
            'stop_price': stop_price,
            'target_price': target_price,
            'position_value': position_value,
            'risk_dollars': risk_dollars,
            'risk_pct': risk_pct,
            'target_r': (target_price - entry_price) / (entry_price - stop_price) if entry_price > stop_price else 0,
            'order_id': order_id or '',
            'status': 'open'
        }
        
        self._write_record(self.trades_file, record)
        print(f"[CHART] Entry logged: {symbol} {shares} shares @ ${entry_price:.2f}")
    
    def log_exit(
        self,
        timestamp: datetime,
        trade_id: str,
        symbol: str,
        exit_price: float,
        exit_reason: Literal['target', 'stop', 'trailing_stop', 'manual', 'eod'],
        gross_pnl: float,
        net_pnl: float,
        commission: float,
        slippage: float,
        r_multiple: float,
        mae: float,
        mfe: float,
        bars_held: int,
        rule_adherence: bool,
        lesson_learned: str
    ):
        """Log trade exit.
        
        Args:
            timestamp: Exit timestamp
            trade_id: Trade identifier
            symbol: Ticker symbol
            exit_price: Actual exit price
            exit_reason: Reason for exit
            gross_pnl: Gross P&L
            net_pnl: Net P&L after costs
            commission: Total commission
            slippage: Total slippage cost
            r_multiple: R-multiple achieved
            mae: Maximum Adverse Excursion (worst drawdown during trade)
            mfe: Maximum Favorable Excursion (best profit during trade)
            bars_held: Number of bars/periods held
            rule_adherence: Whether rules were followed (True/False)
            lesson_learned: One-line lesson from this trade
        """
        record = {
            'timestamp': timestamp.isoformat(),
            'type': 'exit',
            'trade_id': trade_id,
            'symbol': symbol,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'commission': commission,
            'slippage': slippage,
            'r_multiple': r_multiple,
            'mae': mae,
            'mfe': mfe,
            'bars_held': bars_held,
            'rule_adherence': 'yes' if rule_adherence else 'no',
            'lesson_learned': lesson_learned,
            'status': 'closed'
        }
        
        self._write_record(self.trades_file, record)
        
        outcome = "[UP] PROFIT" if net_pnl > 0 else "[DOWN] LOSS"
        print(f"{outcome}: {symbol} closed @ ${exit_price:.2f} | P&L: ${net_pnl:,.2f} ({r_multiple:.2f}R)")
    
    def log_daily_summary(
        self,
        date: datetime,
        starting_equity: float,
        ending_equity: float,
        trades_today: int,
        winners: int,
        losers: int,
        total_pnl: float,
        total_fees: float,
        largest_win: float,
        largest_loss: float,
        positions_held: int,
        notes: str = ""
    ):
        """Log end-of-day summary.
        
        Args:
            date: Date
            starting_equity: Starting equity
            ending_equity: Ending equity
            trades_today: Number of trades closed
            winners: Number of winning trades
            losers: Number of losing trades
            total_pnl: Total P&L for the day
            total_fees: Total fees (commission + slippage)
            largest_win: Largest win
            largest_loss: Largest loss (as negative)
            positions_held: Open positions at EOD
            notes: Additional notes
        """
        record = {
            'date': date.date().isoformat(),
            'type': 'daily_summary',
            'starting_equity': starting_equity,
            'ending_equity': ending_equity,
            'daily_return': ending_equity - starting_equity,
            'daily_return_pct': (ending_equity - starting_equity) / starting_equity if starting_equity > 0 else 0,
            'trades_today': trades_today,
            'winners': winners,
            'losers': losers,
            'win_rate': winners / trades_today if trades_today > 0 else 0,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_pnl': total_pnl - total_fees,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'positions_held': positions_held,
            'notes': notes
        }
        
        self._write_record(self.daily_file, record)
        print(f"📅 Daily summary logged: ${total_pnl:,.2f} P&L, {trades_today} trades")
    
    def _write_record(self, file_path: Path, record: dict):
        """Write a record to file.
        
        Args:
            file_path: Target file
            record: Record dict
        """
        if self.format == 'jsonl':
            self._write_jsonl(file_path, record)
        elif self.format == 'csv':
            self._write_csv(file_path, record)
    
    def _write_jsonl(self, file_path: Path, record: dict):
        """Write JSONL record.
        
        Args:
            file_path: Target file
            record: Record dict
        """
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')
    
    def _write_csv(self, file_path: Path, record: dict):
        """Write CSV record.
        
        Args:
            file_path: Target file
            record: Record dict
        """
        file_exists = file_path.exists()
        
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(record)
    
    def read_trades(self, limit: Optional[int] = None) -> list[dict]:
        """Read trade records.
        
        Args:
            limit: Maximum number of records to return (most recent)
        
        Returns:
            List of trade records
        """
        if not self.trades_file.exists():
            return []
        
        records = []
        
        if self.format == 'jsonl':
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    records.append(json.loads(line))
        elif self.format == 'csv':
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
        
        if limit:
            return records[-limit:]
        return records
    
    def get_statistics(self) -> dict:
        """Calculate statistics from journal.
        
        Returns:
            Dict with statistics
        """
        trades = self.read_trades()
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_r_multiple': 0,
                'avg_pnl': 0
            }
        
        exits = [t for t in trades if t.get('type') == 'exit']
        
        if not exits:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_r_multiple': 0,
                'avg_pnl': 0
            }
        
        total_trades = len(exits)
        winners = sum(1 for t in exits if float(t.get('net_pnl', 0)) > 0)
        total_pnl = sum(float(t.get('net_pnl', 0)) for t in exits)
        total_r = sum(float(t.get('r_multiple', 0)) for t in exits)
        
        return {
            'total_trades': total_trades,
            'winners': winners,
            'losers': total_trades - winners,
            'win_rate': winners / total_trades if total_trades > 0 else 0,
            'avg_r_multiple': total_r / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0
        }


if __name__ == "__main__":
    # Test journal
    print("Testing Trade Journal\n")
    print("=" * 70)
    
    # Create journal
    journal = TradeJournal(format='jsonl')
    
    # Test 1: Log a signal
    print("\nTest 1: Log Signal")
    print("-" * 70)
    journal.log_signal(
        timestamp=datetime.now(),
        symbol='AAPL',
        strategy='Momentum',
        setup='momentum_breakout',
        entry=150.0,
        stop=145.0,
        target=160.0,
        confidence=0.75,
        action_taken='executed',
        notes='Strong volume breakout'
    )
    
    # Test 2: Log entry
    print("\nTest 2: Log Entry")
    print("-" * 70)
    trade_id = f"AAPL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    journal.log_entry(
        timestamp=datetime.now(),
        trade_id=trade_id,
        symbol='AAPL',
        strategy='Momentum',
        shares=50,
        entry_price=150.15,  # With slippage
        stop_price=145.0,
        target_price=160.0,
        position_value=7507.50,
        risk_dollars=257.50,
        risk_pct=0.0103,
        order_id='abc123'
    )
    
    # Test 3: Log exit
    print("\nTest 3: Log Exit")
    print("-" * 70)
    journal.log_exit(
        timestamp=datetime.now(),
        trade_id=trade_id,
        symbol='AAPL',
        exit_price=158.50,
        exit_reason='target',
        gross_pnl=417.50,
        net_pnl=402.50,
        commission=15.0,
        slippage=0.0,
        r_multiple=1.62,
        mae=-50.0,
        mfe=450.0,
        bars_held=5,
        rule_adherence=True,
        lesson_learned="Strong momentum follow-through as expected"
    )
    
    # Test 4: Log daily summary
    print("\nTest 4: Log Daily Summary")
    print("-" * 70)
    journal.log_daily_summary(
        date=datetime.now(),
        starting_equity=25000.0,
        ending_equity=25402.50,
        trades_today=1,
        winners=1,
        losers=0,
        total_pnl=402.50,
        total_fees=15.0,
        largest_win=402.50,
        largest_loss=0.0,
        positions_held=0,
        notes="Good day, followed plan"
    )
    
    # Test 5: Read statistics
    print("\nTest 5: Journal Statistics")
    print("-" * 70)
    stats = journal.get_statistics()
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1%}")
    print(f"Avg R-Multiple: {stats['avg_r_multiple']:.2f}R")
    print(f"Total P&L: ${stats['total_pnl']:,.2f}")
    print(f"Avg P&L: ${stats['avg_pnl']:,.2f}")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] Journal tests complete")
    print(f"\nJournal files created in: {journal.journal_dir}")
    print(f"  - {journal.signals_file.name}")
    print(f"  - {journal.trades_file.name}")
    print(f"  - {journal.daily_file.name}")

