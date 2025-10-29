"""
Reporting module - generates daily performance reports.
"""
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import config
from journal import TradeJournal


class ReportGenerator:
    """Generate daily and periodic performance reports."""
    
    def __init__(self, reports_dir: str = config.REPORTS_DIR):
        """Initialize report generator.
        
        Args:
            reports_dir: Directory for report files
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_daily_report(
        self,
        report_date: date,
        account_info: dict,
        positions: list[dict],
        journal: TradeJournal,
        save: bool = True
    ) -> str:
        """Generate daily performance report.
        
        Args:
            report_date: Date of report
            account_info: Account information dict
            positions: Current positions
            journal: Trade journal instance
            save: Whether to save to file
        
        Returns:
            Report as markdown string
        """
        # Get journal statistics
        stats = journal.get_statistics()
        
        # Calculate metrics
        equity = account_info.get('equity', 0)
        cash = account_info.get('cash', 0)
        
        # Position summary
        total_position_value = sum(p.get('market_value', 0) for p in positions)
        exposure_pct = total_position_value / equity if equity > 0 else 0
        
        total_unrealized_pl = sum(p.get('unrealized_pl', 0) for p in positions)
        
        # Build report
        lines = [
            f"# Daily Trading Report - {report_date.strftime('%Y-%m-%d')}",
            "",
            "## Account Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Total Equity** | ${equity:,.2f} |",
            f"| **Cash** | ${cash:,.2f} |",
            f"| **Buying Power** | ${account_info.get('buying_power', 0):,.2f} |",
            f"| **Exposure** | {exposure_pct:.1%} |",
            "",
            "## Positions",
            "",
        ]
        
        if positions:
            lines.extend([
                f"| Symbol | Qty | Entry | Current | Value | P&L | P&L% |",
                f"|--------|-----|-------|---------|-------|-----|------|"
            ])
            
            for pos in positions:
                symbol = pos['symbol']
                qty = pos['qty']
                entry = pos['avg_entry_price']
                current = pos['current_price']
                value = pos['market_value']
                pl = pos['unrealized_pl']
                plpc = pos['unrealized_plpc'] * 100
                
                pl_sign = "+" if pl >= 0 else ""
                lines.append(
                    f"| {symbol} | {qty} | ${entry:.2f} | ${current:.2f} | "
                    f"${value:,.2f} | {pl_sign}${pl:,.2f} | {pl_sign}{plpc:.2f}% |"
                )
            
            lines.extend([
                "",
                f"**Total Unrealized P&L:** ${total_unrealized_pl:,.2f}",
                ""
            ])
        else:
            lines.append("*No open positions*\n")
        
        # Trading Activity
        lines.extend([
            "## Trading Activity (All Time)",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Total Trades** | {stats['total_trades']} |",
            f"| **Winners** | {stats.get('winners', 0)} |",
            f"| **Losers** | {stats.get('losers', 0)} |",
            f"| **Win Rate** | {stats['win_rate']:.1%} |",
            f"| **Avg R-Multiple** | {stats['avg_r_multiple']:.2f}R |",
            f"| **Total P&L** | ${stats.get('total_pnl', 0):,.2f} |",
            f"| **Avg P&L/Trade** | ${stats.get('avg_pnl', 0):,.2f} |",
            "",
        ])
        
        # Recent Trades
        recent_trades = journal.read_trades(limit=10)
        exits = [t for t in recent_trades if t.get('type') == 'exit']
        
        if exits:
            lines.extend([
                "## Recent Trades",
                "",
                "| Symbol | Exit Date | Exit Price | P&L | R-Multiple | Reason |",
                "|--------|-----------|------------|-----|------------|--------|"
            ])
            
            for trade in reversed(exits[-5:]):  # Last 5 exits
                timestamp = trade.get('timestamp', '')
                exit_date = timestamp.split('T')[0] if 'T' in timestamp else timestamp[:10]
                symbol = trade.get('symbol', '')
                exit_price = float(trade.get('exit_price', 0))
                net_pnl = float(trade.get('net_pnl', 0))
                r_mult = float(trade.get('r_multiple', 0))
                reason = trade.get('exit_reason', '')
                
                pnl_sign = "+" if net_pnl >= 0 else ""
                
                lines.append(
                    f"| {symbol} | {exit_date} | ${exit_price:.2f} | "
                    f"{pnl_sign}${net_pnl:.2f} | {r_mult:.2f}R | {reason} |"
                )
            
            lines.append("")
        
        # Risk Metrics
        lines.extend([
            "## Risk Management",
            "",
            f"| Parameter | Limit | Current |",
            f"|-----------|-------|---------|",
            f"| **Max Positions** | {config.MAX_POSITIONS} | {len(positions)} |",
            f"| **Max Position Size** | {config.MAX_POSITION_SIZE_PCT:.0%} | "
            f"{max([p['market_value'] / equity for p in positions], default=0):.1%} |",
            f"| **Max Risk/Trade** | {config.MAX_RISK_PER_TRADE_PCT:.1%} | - |",
            "",
        ])
        
        # Footer
        lines.extend([
            "---",
            "",
            f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "*This is research software. Past performance does not guarantee future results.*",
        ])
        
        report = "\n".join(lines)
        
        # Save to file
        if save:
            filename = f"{report_date.strftime('%Y-%m-%d')}.md"
            filepath = self.reports_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"[FILE] Report saved: {filepath}")
        
        return report
    
    def print_console_summary(
        self,
        account_info: dict,
        positions: list[dict],
        stats: dict
    ):
        """Print a concise summary to console.
        
        Args:
            account_info: Account information
            positions: Current positions
            stats: Trading statistics
        """
        print("\n" + "=" * 70)
        print("DAILY SUMMARY")
        print("=" * 70)
        
        equity = account_info.get('equity', 0)
        cash = account_info.get('cash', 0)
        
        print(f"\n[MONEY] Account")
        print(f"   Equity: ${equity:,.2f}")
        print(f"   Cash: ${cash:,.2f}")
        
        if positions:
            total_pl = sum(p.get('unrealized_pl', 0) for p in positions)
            print(f"\n[CHART] Positions ({len(positions)})")
            for pos in positions:
                pl_emoji = "[UP]" if pos['unrealized_pl'] >= 0 else "[DOWN]"
                print(
                    f"   {pl_emoji} {pos['symbol']}: {pos['qty']} shares, "
                    f"P&L: ${pos['unrealized_pl']:,.2f} ({pos['unrealized_plpc']:.1%})"
                )
            print(f"   Total Unrealized P&L: ${total_pl:,.2f}")
        else:
            print(f"\n[CHART] Positions: None")
        
        print(f"\n[UP] Performance (All Time)")
        print(f"   Trades: {stats['total_trades']}")
        print(f"   Win Rate: {stats['win_rate']:.1%}")
        print(f"   Avg R: {stats['avg_r_multiple']:.2f}R")
        print(f"   Total P&L: ${stats.get('total_pnl', 0):,.2f}")
        
        print("=" * 70 + "\n")


if __name__ == "__main__":
    # Test report generation
    print("Testing Report Generator\n")
    
    # Create sample data
    account_info = {
        'equity': 25402.50,
        'cash': 17895.00,
        'buying_power': 50000.00
    }
    
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 50,
            'avg_entry_price': 150.15,
            'current_price': 152.30,
            'market_value': 7615.00,
            'cost_basis': 7507.50,
            'unrealized_pl': 107.50,
            'unrealized_plpc': 0.0143
        }
    ]
    
    # Create journal with sample data
    journal = TradeJournal(format='jsonl')
    
    # Generate report
    generator = ReportGenerator()
    
    print("Generating daily report...")
    report = generator.generate_daily_report(
        report_date=datetime.now().date(),
        account_info=account_info,
        positions=positions,
        journal=journal,
        save=True
    )
    
    print("\n" + "=" * 70)
    print("REPORT PREVIEW")
    print("=" * 70)
    print(report)
    
    print("\n" + "=" * 70)
    print("CONSOLE SUMMARY")
    print("=" * 70)
    
    stats = journal.get_statistics()
    generator.print_console_summary(account_info, positions, stats)
    
    print("[SUCCESS] Report generation tests complete")

