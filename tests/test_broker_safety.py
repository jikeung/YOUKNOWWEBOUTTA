"""
Unit tests for broker safety guards.
"""
import pytest
from broker import Broker, LiveTradingError
import config


class TestBrokerSafety:
    """Test broker safety mechanisms."""
    
    def test_paper_trading_initialization(self):
        """Test that paper trading can be initialized."""
        try:
            broker = Broker(paper=True)
            assert broker.paper is True
        except Exception as e:
            pytest.fail(f"Paper trading initialization failed: {e}")
    
    def test_live_trading_blocked_without_env_var(self):
        """Test that live trading is blocked without ALLOW_LIVE_TRADING env var."""
        # Save original value
        original = config.ALLOW_LIVE_TRADING
        
        try:
            # Disable live trading in config
            config.ALLOW_LIVE_TRADING = False
            
            with pytest.raises(LiveTradingError) as exc_info:
                Broker(paper=False, cli_confirm=True)
            
            assert 'ALLOW_LIVE_TRADING' in str(exc_info.value)
            
        finally:
            # Restore original value
            config.ALLOW_LIVE_TRADING = original
    
    def test_live_trading_blocked_without_cli_confirm(self):
        """Test that live trading is blocked without CLI confirmation."""
        # Save original value
        original = config.ALLOW_LIVE_TRADING
        
        try:
            # Enable live trading in config but no CLI confirm
            config.ALLOW_LIVE_TRADING = True
            
            with pytest.raises(LiveTradingError) as exc_info:
                Broker(paper=False, cli_confirm=False)
            
            assert 'CLI confirmation' in str(exc_info.value) or 'accept-live-risk' in str(exc_info.value)
            
        finally:
            # Restore original value
            config.ALLOW_LIVE_TRADING = original
    
    def test_double_confirmation_required(self):
        """Test that BOTH env var AND CLI flag are required for live trading."""
        original = config.ALLOW_LIVE_TRADING
        
        try:
            # Test 1: Env enabled, CLI disabled
            config.ALLOW_LIVE_TRADING = True
            with pytest.raises(LiveTradingError):
                Broker(paper=False, cli_confirm=False)
            
            # Test 2: Env disabled, CLI enabled
            config.ALLOW_LIVE_TRADING = False
            with pytest.raises(LiveTradingError):
                Broker(paper=False, cli_confirm=True)
            
            # Test 3: Both disabled
            config.ALLOW_LIVE_TRADING = False
            with pytest.raises(LiveTradingError):
                Broker(paper=False, cli_confirm=False)
            
        finally:
            config.ALLOW_LIVE_TRADING = original


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_config_validation(self):
        """Test that config validation catches errors."""
        errors = config.validate_config()
        
        # Should either have no errors or specific error messages
        if errors:
            for error in errors:
                assert isinstance(error, str)
                assert len(error) > 0
    
    def test_risk_limits_in_range(self):
        """Test that risk limits are within acceptable ranges."""
        assert 0 < config.MAX_POSITION_SIZE_PCT <= 1.0
        assert 0 < config.MAX_RISK_PER_TRADE_PCT <= 0.1
        assert config.MAX_POSITIONS >= 1
        assert config.MIN_STOCK_PRICE > 0
        assert config.MIN_AVG_DOLLAR_VOLUME > 0
    
    def test_transaction_costs_non_negative(self):
        """Test that transaction costs are non-negative."""
        assert config.COMMISSION_PER_TRADE >= 0
        assert config.SLIPPAGE_PCT >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

