"""
Unit tests for risk management module.
"""
import pytest
from risk import RiskManager
import config


class TestRiskManager:
    """Test risk management checks."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.equity = 25000.0
        self.risk_mgr = RiskManager(self.equity)
    
    def test_valid_trade_passes(self):
        """Test that valid trade passes all checks."""
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='AAPL',
            entry_price=150.0,
            position_value=7500.0,  # 30% of equity
            risk_dollars=250.0,      # 1% of equity
            current_positions=[],
            liquidity_check={'avg_dollar_volume': 5_000_000_000}
        )
        
        assert approved is True
        assert any('passed' in r.lower() for r in reasons)
    
    def test_max_positions_enforced(self):
        """Test that max positions limit is enforced."""
        # Create max positions
        current_positions = [
            {'symbol': 'MSFT', 'market_value': 5000},
            {'symbol': 'GOOGL', 'market_value': 5000}
        ]
        
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='AAPL',
            entry_price=150.0,
            position_value=7500.0,
            risk_dollars=250.0,
            current_positions=current_positions
        )
        
        assert approved is False
        assert any('max positions' in r.lower() for r in reasons)
    
    def test_position_size_limit_enforced(self):
        """Test that position size limit is enforced."""
        # Try to open position larger than 30% of equity
        oversized_position = self.equity * 0.35  # 35% > 30% limit
        
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='AAPL',
            entry_price=150.0,
            position_value=oversized_position,
            risk_dollars=250.0,
            current_positions=[]
        )
        
        assert approved is False
        assert any('position size' in r.lower() for r in reasons)
    
    def test_risk_limit_enforced(self):
        """Test that risk per trade limit is enforced."""
        # Try to risk more than 1% of equity
        excessive_risk = self.equity * 0.02  # 2% > 1% limit
        
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='AAPL',
            entry_price=150.0,
            position_value=7500.0,
            risk_dollars=excessive_risk,
            current_positions=[]
        )
        
        assert approved is False
        assert any('risk' in r.lower() for r in reasons)
    
    def test_min_price_enforced(self):
        """Test that minimum price requirement is enforced."""
        low_price = config.MIN_STOCK_PRICE - 0.50  # Below minimum
        
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='PENNY',
            entry_price=low_price,
            position_value=1000.0,
            risk_dollars=100.0,
            current_positions=[]
        )
        
        assert approved is False
        assert any('price' in r.lower() for r in reasons)
    
    def test_liquidity_check(self):
        """Test that liquidity requirements are enforced."""
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='ILLIQUID',
            entry_price=50.0,
            position_value=5000.0,
            risk_dollars=200.0,
            current_positions=[],
            liquidity_check={'avg_dollar_volume': 500_000}  # Below 1M minimum
        )
        
        assert approved is False
        assert any('volume' in r.lower() or 'liquidity' in r.lower() for r in reasons)
    
    def test_duplicate_position_rejected(self):
        """Test that duplicate positions are rejected."""
        current_positions = [
            {'symbol': 'AAPL', 'market_value': 5000}
        ]
        
        approved, reasons = self.risk_mgr.check_pre_trade(
            symbol='AAPL',
            entry_price=150.0,
            position_value=5000.0,
            risk_dollars=200.0,
            current_positions=current_positions
        )
        
        assert approved is False
        assert any('duplicate' in r.lower() or 'already' in r.lower() for r in reasons)
    
    def test_max_shares_calculation(self):
        """Test maximum shares calculation."""
        entry = 100.0
        stop = 95.0
        
        max_shares = self.risk_mgr.calculate_max_shares(entry, stop)
        
        # Verify it respects both risk and position size limits
        assert max_shares > 0
        
        # Check risk limit
        risk_per_share = entry - stop
        risk_dollars = max_shares * risk_per_share
        assert risk_dollars <= self.equity * config.MAX_RISK_PER_TRADE_PCT * 1.01  # Small tolerance
        
        # Check position size limit
        position_value = max_shares * entry
        assert position_value <= self.equity * config.MAX_POSITION_SIZE_PCT * 1.01  # Small tolerance
    
    def test_intraday_alerts(self):
        """Test intraday risk monitoring."""
        positions = [
            {
                'symbol': 'AAPL',
                'qty': 50,
                'market_value': 7000,
                'unrealized_plpc': -0.03  # Down 3%
            }
        ]
        
        alerts = self.risk_mgr.check_intraday(positions)
        
        # Should generate alert for large loss
        assert 'AAPL' in alerts
        assert len(alerts['AAPL']) > 0


class TestRiskIntegration:
    """Integration tests for risk management."""
    
    def test_multiple_violations(self):
        """Test that multiple violations are all reported."""
        equity = 25000.0
        risk_mgr = RiskManager(equity)
        
        # Create scenario with multiple violations
        current_positions = [
            {'symbol': 'MSFT', 'market_value': 8000},
            {'symbol': 'GOOGL', 'market_value': 8000}
        ]
        
        approved, reasons = risk_mgr.check_pre_trade(
            symbol='PENNY',
            entry_price=1.50,  # Below min price
            position_value=10000,  # Too large
            risk_dollars=500,  # Too much risk
            current_positions=current_positions,  # Too many positions
            liquidity_check={'avg_dollar_volume': 500_000}  # Illiquid
        )
        
        assert approved is False
        # Should have multiple violation reasons
        assert len([r for r in reasons if 'exceed' in r.lower() or 'below' in r.lower()]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

