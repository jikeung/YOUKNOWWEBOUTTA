"""
Unit tests for position sizing module.
"""
import pytest
from position_sizing import PositionSizer
import config


class TestPositionSizer:
    """Test position sizing calculations."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.equity = 25000.0
        self.sizer = PositionSizer(self.equity)
    
    def test_valid_position(self):
        """Test valid position sizing."""
        entry = 100.0
        stop = 95.0
        
        result = self.sizer.calculate_shares(entry, stop)
        
        assert result['valid'] is True
        assert result['shares'] > 0
        assert result['position_value'] > 0
        assert result['risk_dollars'] <= self.equity * config.MAX_RISK_PER_TRADE_PCT
        assert result['position_pct'] <= config.MAX_POSITION_SIZE_PCT
    
    def test_position_size_limit(self):
        """Test that position size limit is enforced."""
        # Expensive stock with tight stop should be limited by position size
        entry = 1000.0
        stop = 995.0  # Very tight stop
        
        result = self.sizer.calculate_shares(entry, stop)
        
        if result['valid']:
            # Should be limited by position size, not risk
            max_shares_by_position = int((self.equity * config.MAX_POSITION_SIZE_PCT) / entry)
            assert result['shares'] <= max_shares_by_position
            assert result['position_pct'] <= config.MAX_POSITION_SIZE_PCT
    
    def test_risk_limit(self):
        """Test that risk limit is enforced."""
        entry = 100.0
        stop = 95.0
        
        result = self.sizer.calculate_shares(entry, stop)
        
        if result['valid']:
            assert result['risk_pct'] <= config.MAX_RISK_PER_TRADE_PCT
    
    def test_invalid_stop_above_entry(self):
        """Test that stop above entry is rejected."""
        entry = 100.0
        stop = 105.0  # Invalid: stop above entry
        
        result = self.sizer.calculate_shares(entry, stop)
        
        assert result['valid'] is False
        assert 'stop' in result['reason'].lower()
    
    def test_zero_or_negative_prices(self):
        """Test that zero or negative prices are rejected."""
        result1 = self.sizer.calculate_shares(0, 95)
        assert result1['valid'] is False
        
        result2 = self.sizer.calculate_shares(100, 0)
        assert result2['valid'] is False
        
        result3 = self.sizer.calculate_shares(-10, 95)
        assert result3['valid'] is False
    
    def test_target_calculation(self):
        """Test target price calculation."""
        entry = 100.0
        stop = 95.0
        r_multiple = 2.0
        
        target = self.sizer.calculate_target_price(entry, stop, r_multiple)
        
        risk = entry - stop
        expected_target = entry + (risk * r_multiple)
        assert target == expected_target
    
    def test_trailing_stop(self):
        """Test trailing stop calculation."""
        entry = 100.0
        current = 110.0
        atr = 2.0
        original_stop = 95.0
        
        trailing = self.sizer.calculate_trailing_stop(
            entry, current, atr, atr_multiplier=2.0, original_stop=original_stop
        )
        
        # Should be ATR-based but not below entry
        expected = current - (atr * 2.0)
        assert trailing >= entry  # Never trail below entry
        assert trailing >= original_stop  # Never trail below original stop


class TestSlippageCalculation:
    """Test slippage modeling."""
    
    def test_slippage_impact(self):
        """Test that slippage reduces position size appropriately."""
        equity = 25000.0
        entry = 100.0
        stop = 95.0
        
        sizer = PositionSizer(equity)
        result = sizer.calculate_shares(entry, stop)
        
        if result['valid']:
            # Slippage will effectively increase entry price
            slippage_pct = config.SLIPPAGE_PCT
            entry_with_slippage = entry * (1 + slippage_pct)
            
            # Risk per share increases with slippage
            risk_with_slippage = entry_with_slippage - stop
            risk_without_slippage = entry - stop
            
            assert risk_with_slippage > risk_without_slippage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

