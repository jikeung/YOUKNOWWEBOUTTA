"""
Position sizing module with risk-based calculations.
Ensures proper risk management and adherence to position limits.
"""
from typing import Optional
import config


class PositionSizer:
    """Calculate position sizes based on risk parameters."""
    
    def __init__(
        self,
        equity: float,
        max_position_pct: float = config.MAX_POSITION_SIZE_PCT,
        max_risk_pct: float = config.MAX_RISK_PER_TRADE_PCT
    ):
        """Initialize position sizer.
        
        Args:
            equity: Total account equity
            max_position_pct: Maximum position size as % of equity
            max_risk_pct: Maximum risk per trade as % of equity
        """
        self.equity = equity
        self.max_position_pct = max_position_pct
        self.max_risk_pct = max_risk_pct
    
    def calculate_shares(
        self,
        entry_price: float,
        stop_price: float,
        risk_pct: Optional[float] = None
    ) -> dict:
        """Calculate position size based on risk.
        
        Args:
            entry_price: Entry price per share
            stop_price: Stop loss price per share
            risk_pct: Risk as % of equity (uses max_risk_pct if None)
        
        Returns:
            Dict with sizing details:
            {
                'shares': int,
                'position_value': float,
                'position_pct': float,
                'risk_dollars': float,
                'risk_pct': float,
                'risk_per_share': float,
                'valid': bool,
                'reason': str (if invalid)
            }
        """
        if risk_pct is None:
            risk_pct = self.max_risk_pct
        
        result = {
            'shares': 0,
            'position_value': 0.0,
            'position_pct': 0.0,
            'risk_dollars': 0.0,
            'risk_pct': 0.0,
            'risk_per_share': 0.0,
            'valid': False,
            'reason': ''
        }
        
        # Validation
        if entry_price <= 0:
            result['reason'] = "Entry price must be positive"
            return result
        
        if stop_price <= 0:
            result['reason'] = "Stop price must be positive"
            return result
        
        if entry_price <= stop_price:
            result['reason'] = "Stop price must be below entry price (long only)"
            return result
        
        if self.equity <= 0:
            result['reason'] = "Equity must be positive"
            return result
        
        # Calculate risk per share
        risk_per_share = entry_price - stop_price
        result['risk_per_share'] = risk_per_share
        
        # Calculate position size based on risk
        max_risk_dollars = self.equity * risk_pct
        shares_by_risk = int(max_risk_dollars / risk_per_share)
        
        # Calculate maximum shares based on position size limit
        max_position_dollars = self.equity * self.max_position_pct
        shares_by_position_size = int(max_position_dollars / entry_price)
        
        # Use the smaller of the two
        shares = min(shares_by_risk, shares_by_position_size)
        
        if shares < 1:
            result['reason'] = "Position size rounds to 0 shares (insufficient equity or risk too small)"
            return result
        
        # Calculate final metrics
        position_value = shares * entry_price
        position_pct = position_value / self.equity
        risk_dollars = shares * risk_per_share
        actual_risk_pct = risk_dollars / self.equity
        
        # Final validation
        if position_pct > self.max_position_pct:
            result['reason'] = f"Position size {position_pct:.1%} exceeds max {self.max_position_pct:.1%}"
            return result
        
        if actual_risk_pct > self.max_risk_pct:
            result['reason'] = f"Risk {actual_risk_pct:.2%} exceeds max {self.max_risk_pct:.2%}"
            return result
        
        # Success
        result.update({
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_dollars': risk_dollars,
            'risk_pct': actual_risk_pct,
            'valid': True,
            'reason': 'OK'
        })
        
        return result
    
    def calculate_target_price(
        self,
        entry_price: float,
        stop_price: float,
        r_multiple: float = 2.0
    ) -> float:
        """Calculate target price based on R-multiple.
        
        Args:
            entry_price: Entry price
            stop_price: Stop price
            r_multiple: Reward/Risk ratio (e.g., 2.0 = 2R target)
        
        Returns:
            Target price
        """
        risk = entry_price - stop_price
        target = entry_price + (risk * r_multiple)
        return target
    
    def adjust_stop_to_breakeven(
        self,
        entry_price: float,
        current_price: float,
        original_stop: float,
        breakeven_r: float = 1.0
    ) -> float:
        """Determine if stop should be moved to breakeven.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            original_stop: Original stop price
            breakeven_r: R-multiple at which to move stop to breakeven
        
        Returns:
            New stop price (either breakeven or original)
        """
        risk = entry_price - original_stop
        profit = current_price - entry_price
        r_gained = profit / risk if risk > 0 else 0
        
        if r_gained >= breakeven_r:
            return entry_price  # Move to breakeven
        
        return original_stop  # Keep original stop
    
    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        atr_multiplier: float = 2.0,
        original_stop: float = None
    ) -> float:
        """Calculate trailing stop based on ATR.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            atr: Average True Range value
            atr_multiplier: ATR multiplier for stop distance
            original_stop: Original stop (won't trail below this)
        
        Returns:
            Trailing stop price
        """
        trailing_stop = current_price - (atr * atr_multiplier)
        
        # Don't trail below original stop
        if original_stop is not None:
            trailing_stop = max(trailing_stop, original_stop)
        
        # Don't trail below entry (lock in profits)
        trailing_stop = max(trailing_stop, entry_price)
        
        return trailing_stop


def format_position_size(sizing: dict) -> str:
    """Format position sizing result as readable string.
    
    Args:
        sizing: Result from calculate_shares()
    
    Returns:
        Formatted string
    """
    if not sizing['valid']:
        return f"❌ Invalid: {sizing['reason']}"
    
    return (
        f"✅ {sizing['shares']} shares @ ${sizing['position_value']:,.2f} "
        f"({sizing['position_pct']:.1%} of equity), "
        f"Risk: ${sizing['risk_dollars']:.2f} ({sizing['risk_pct']:.2%})"
    )


if __name__ == "__main__":
    # Test position sizing
    print("Testing Position Sizing\n")
    print("=" * 70)
    
    # Example account
    equity = 25000.0
    sizer = PositionSizer(equity)
    
    print(f"Account Equity: ${equity:,.2f}")
    print(f"Max Position Size: {config.MAX_POSITION_SIZE_PCT:.0%} = ${equity * config.MAX_POSITION_SIZE_PCT:,.2f}")
    print(f"Max Risk Per Trade: {config.MAX_RISK_PER_TRADE_PCT:.1%} = ${equity * config.MAX_RISK_PER_TRADE_PCT:.2f}")
    print()
    
    # Test case 1: Normal position
    print("Test 1: Normal Position")
    print("-" * 70)
    entry = 150.0
    stop = 145.0
    sizing = sizer.calculate_shares(entry, stop)
    print(f"Entry: ${entry}, Stop: ${stop}, Risk/Share: ${entry - stop}")
    print(format_position_size(sizing))
    print()
    
    # Test case 2: Expensive stock (position size limited)
    print("Test 2: Expensive Stock (position size constraint)")
    print("-" * 70)
    entry = 1000.0
    stop = 980.0
    sizing = sizer.calculate_shares(entry, stop)
    print(f"Entry: ${entry}, Stop: ${stop}, Risk/Share: ${entry - stop}")
    print(format_position_size(sizing))
    print()
    
    # Test case 3: Tight stop (risk limited)
    print("Test 3: Tight Stop (risk constraint)")
    print("-" * 70)
    entry = 50.0
    stop = 49.50
    sizing = sizer.calculate_shares(entry, stop)
    print(f"Entry: ${entry}, Stop: ${stop}, Risk/Share: ${entry - stop}")
    print(format_position_size(sizing))
    print()
    
    # Test case 4: Invalid (stop above entry)
    print("Test 4: Invalid Stop (above entry)")
    print("-" * 70)
    entry = 50.0
    stop = 55.0
    sizing = sizer.calculate_shares(entry, stop)
    print(f"Entry: ${entry}, Stop: ${stop}")
    print(format_position_size(sizing))
    print()
    
    # Test target calculation
    print("Test 5: Target Calculation (2R)")
    print("-" * 70)
    entry = 100.0
    stop = 95.0
    target = sizer.calculate_target_price(entry, stop, r_multiple=2.0)
    print(f"Entry: ${entry}, Stop: ${stop}, Target (2R): ${target}")
    print(f"Risk: ${entry - stop}, Reward: ${target - entry}, R:R = 1:{(target - entry) / (entry - stop):.1f}")
    print()
    
    # Test trailing stop
    print("Test 6: Trailing Stop")
    print("-" * 70)
    entry = 100.0
    current = 110.0
    atr = 2.5
    stop = sizer.calculate_trailing_stop(entry, current, atr, atr_multiplier=2.0, original_stop=95.0)
    print(f"Entry: ${entry}, Current: ${current}, ATR: {atr}")
    print(f"Trailing Stop (2*ATR): ${stop:.2f}")
    print()
    
    print("✅ Position sizing tests complete")

