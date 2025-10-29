"""
Risk management module - pre-trade and intraday checks.
Enforces position limits, exposure caps, and liquidity requirements.
"""
from typing import Optional
from datetime import datetime

import config


class RiskManager:
    """Enforce risk limits and trading rules."""
    
    def __init__(
        self,
        equity: float,
        max_positions: int = config.MAX_POSITIONS,
        max_position_pct: float = config.MAX_POSITION_SIZE_PCT,
        max_risk_pct: float = config.MAX_RISK_PER_TRADE_PCT
    ):
        """Initialize risk manager.
        
        Args:
            equity: Current account equity
            max_positions: Maximum simultaneous positions
            max_position_pct: Max position size as % of equity
            max_risk_pct: Max risk per trade as % of equity
        """
        self.equity = equity
        self.max_positions = max_positions
        self.max_position_pct = max_position_pct
        self.max_risk_pct = max_risk_pct
    
    def check_pre_trade(
        self,
        symbol: str,
        entry_price: float,
        position_value: float,
        risk_dollars: float,
        current_positions: list[dict],
        liquidity_check: Optional[dict] = None
    ) -> tuple[bool, list[str]]:
        """Run pre-trade risk checks.
        
        Args:
            symbol: Ticker symbol
            entry_price: Proposed entry price
            position_value: Position dollar value
            risk_dollars: Risk in dollars
            current_positions: List of current positions
            liquidity_check: Optional dict with liquidity info
        
        Returns:
            Tuple of (approved: bool, reasons: list[str])
        """
        reasons = []
        approved = True
        
        # Check 1: Maximum positions
        if len(current_positions) >= self.max_positions:
            # Check if we already have this symbol
            has_symbol = any(p['symbol'] == symbol for p in current_positions)
            if not has_symbol:
                approved = False
                reasons.append(
                    f"Max positions ({self.max_positions}) reached. "
                    f"Currently holding {len(current_positions)}"
                )
        
        # Check 2: Position size limit
        position_pct = position_value / self.equity
        if position_pct > self.max_position_pct:
            approved = False
            reasons.append(
                f"Position size {position_pct:.1%} exceeds max {self.max_position_pct:.1%}"
            )
        
        # Check 3: Risk limit
        risk_pct = risk_dollars / self.equity
        if risk_pct > self.max_risk_pct:
            approved = False
            reasons.append(
                f"Risk {risk_pct:.2%} exceeds max {self.max_risk_pct:.2%}"
            )
        
        # Check 4: Minimum price
        if entry_price < config.MIN_STOCK_PRICE:
            approved = False
            reasons.append(
                f"Price ${entry_price:.2f} below minimum ${config.MIN_STOCK_PRICE}"
            )
        
        # Check 5: Liquidity
        if liquidity_check:
            avg_volume = liquidity_check.get('avg_dollar_volume', 0)
            if avg_volume < config.MIN_AVG_DOLLAR_VOLUME:
                approved = False
                reasons.append(
                    f"Avg dollar volume ${avg_volume:,.0f} below minimum "
                    f"${config.MIN_AVG_DOLLAR_VOLUME:,.0f}"
                )
        
        # Check 6: Long-only constraint
        if config.TRADING_MODE == 'long_only':
            # This check is informational - we're only entering longs
            pass
        
        # Check 7: Leverage check
        if not config.LEVERAGE_ALLOWED:
            total_exposure = sum(p.get('market_value', 0) for p in current_positions)
            total_exposure += position_value
            if total_exposure > self.equity * 1.01:  # Allow 1% margin for rounding
                approved = False
                reasons.append(
                    f"Total exposure ${total_exposure:,.0f} would exceed equity "
                    f"${self.equity:,.0f} (leverage not allowed)"
                )
        
        # Check 8: Duplicate position
        has_position = any(p['symbol'] == symbol for p in current_positions)
        if has_position:
            approved = False
            reasons.append(f"Already have position in {symbol}")
        
        if approved:
            reasons.append("All risk checks passed")
        
        return approved, reasons
    
    def check_intraday(
        self,
        positions: list[dict],
        current_time: Optional[datetime] = None
    ) -> dict[str, list[str]]:
        """Run intraday risk checks on existing positions.
        
        Args:
            positions: List of current positions
            current_time: Current time (default: now)
        
        Returns:
            Dict mapping symbol -> list of alerts
        """
        if current_time is None:
            current_time = datetime.now()
        
        alerts = {}
        
        for pos in positions:
            symbol = pos['symbol']
            pos_alerts = []
            
            # Check 1: Unrealized loss > 2x expected (stop may not have triggered)
            unrealized_plpc = pos.get('unrealized_plpc', 0)
            if unrealized_plpc < -0.02:  # Down more than 2%
                pos_alerts.append(
                    f"Large unrealized loss: {unrealized_plpc:.1%}. "
                    "Verify stop is in place."
                )
            
            # Check 2: Market hours (if constraint enabled)
            if config.MARKET_HOURS_ONLY:
                hour = current_time.hour
                # Market hours: 9:30 AM - 4:00 PM ET
                # Simplified check (doesn't account for timezone)
                if hour < 9 or hour >= 16:
                    pos_alerts.append(
                        "Outside market hours. Consider closing positions."
                    )
            
            # Check 3: Position size drift
            market_value = pos.get('market_value', 0)
            if market_value > 0:
                position_pct = market_value / self.equity
                if position_pct > self.max_position_pct * 1.2:  # 20% buffer
                    pos_alerts.append(
                        f"Position size {position_pct:.1%} significantly exceeds "
                        f"limit {self.max_position_pct:.1%} due to appreciation. "
                        "Consider taking profits."
                    )
            
            if pos_alerts:
                alerts[symbol] = pos_alerts
        
        return alerts
    
    def calculate_max_shares(
        self,
        entry_price: float,
        stop_price: float
    ) -> int:
        """Calculate maximum shares based on risk limits.
        
        Args:
            entry_price: Entry price per share
            stop_price: Stop price per share
        
        Returns:
            Maximum number of shares
        """
        if entry_price <= stop_price or entry_price <= 0 or stop_price <= 0:
            return 0
        
        # Risk-based sizing
        risk_per_share = entry_price - stop_price
        max_risk_dollars = self.equity * self.max_risk_pct
        shares_by_risk = int(max_risk_dollars / risk_per_share)
        
        # Position size limit
        max_position_dollars = self.equity * self.max_position_pct
        shares_by_position = int(max_position_dollars / entry_price)
        
        # Return the smaller of the two
        return min(shares_by_risk, shares_by_position)
    
    def check_halt_conditions(self, symbol: str) -> tuple[bool, str]:
        """Check if symbol should be halted from trading.
        
        This is a placeholder for integration with news/halt APIs.
        
        Args:
            symbol: Symbol to check
        
        Returns:
            Tuple of (is_halted: bool, reason: str)
        """
        # Placeholder - in production, integrate with:
        # - LULD (Limit Up Limit Down) halt data
        # - News sentiment API
        # - Regulatory halt feeds
        
        # For now, return not halted
        return False, ""


def format_risk_report(
    approved: bool,
    reasons: list[str],
    trade_plan: dict
) -> str:
    """Format risk check results as readable report.
    
    Args:
        approved: Whether trade is approved
        reasons: List of reasons/checks
        trade_plan: Trade plan dict
    
    Returns:
        Formatted string
    """
    status = "[SUCCESS] APPROVED" if approved else "[ERROR] REJECTED"
    
    report = [
        "=" * 70,
        f"RISK CHECK: {trade_plan['symbol']} - {status}",
        "=" * 70,
        f"Setup: {trade_plan.get('setup', 'N/A')}",
        f"Entry: ${trade_plan['entry']:.2f}",
        f"Stop: ${trade_plan['stop']:.2f}",
        f"Target: ${trade_plan.get('target', 0):.2f}",
        "",
        "Checks:",
    ]
    
    for reason in reasons:
        prefix = "  [OK] " if approved else "  [ERROR] "
        report.append(f"{prefix}{reason}")
    
    report.append("=" * 70)
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test risk management
    print("Testing Risk Management\n")
    print("=" * 70)
    
    # Setup
    equity = 25000.0
    risk_mgr = RiskManager(equity)
    
    print(f"Account Equity: ${equity:,.2f}")
    print(f"Max Positions: {risk_mgr.max_positions}")
    print(f"Max Position Size: {risk_mgr.max_position_pct:.0%}")
    print(f"Max Risk Per Trade: {risk_mgr.max_risk_pct:.1%}")
    print()
    
    # Test 1: Valid trade
    print("Test 1: Valid Trade")
    print("-" * 70)
    trade_plan = {
        'symbol': 'AAPL',
        'setup': 'momentum',
        'entry': 150.0,
        'stop': 145.0,
        'target': 160.0
    }
    
    approved, reasons = risk_mgr.check_pre_trade(
        symbol='AAPL',
        entry_price=150.0,
        position_value=7500.0,  # 50 shares
        risk_dollars=250.0,      # 50 * (150-145)
        current_positions=[],
        liquidity_check={'avg_dollar_volume': 5_000_000_000}
    )
    
    print(format_risk_report(approved, reasons, trade_plan))
    print()
    
    # Test 2: Too many positions
    print("Test 2: Too Many Positions")
    print("-" * 70)
    current_positions = [
        {'symbol': 'MSFT', 'market_value': 7000},
        {'symbol': 'GOOGL', 'market_value': 6500},
    ]
    
    approved, reasons = risk_mgr.check_pre_trade(
        symbol='AAPL',
        entry_price=150.0,
        position_value=7500.0,
        risk_dollars=250.0,
        current_positions=current_positions,
    )
    
    print(format_risk_report(approved, reasons, trade_plan))
    print()
    
    # Test 3: Position too large
    print("Test 3: Position Too Large")
    print("-" * 70)
    approved, reasons = risk_mgr.check_pre_trade(
        symbol='AAPL',
        entry_price=150.0,
        position_value=10000.0,  # 40% of equity (exceeds 30% limit)
        risk_dollars=250.0,
        current_positions=[],
    )
    
    print(format_risk_report(approved, reasons, trade_plan))
    print()
    
    # Test 4: Risk too high
    print("Test 4: Risk Too High")
    print("-" * 70)
    approved, reasons = risk_mgr.check_pre_trade(
        symbol='AAPL',
        entry_price=150.0,
        position_value=7500.0,
        risk_dollars=500.0,  # 2% risk (exceeds 1% limit)
        current_positions=[],
    )
    
    print(format_risk_report(approved, reasons, trade_plan))
    print()
    
    # Test 5: Intraday checks
    print("Test 5: Intraday Checks")
    print("-" * 70)
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 50,
            'market_value': 7500,
            'unrealized_plpc': -0.03  # Down 3%
        }
    ]
    
    alerts = risk_mgr.check_intraday(positions)
    if alerts:
        for symbol, symbol_alerts in alerts.items():
            print(f"{symbol}:")
            for alert in symbol_alerts:
                print(f"  [WARNING]  {alert}")
    else:
        print("[SUCCESS] No alerts")
    
    print()
    print("=" * 70)
    print("[SUCCESS] Risk management tests complete")

