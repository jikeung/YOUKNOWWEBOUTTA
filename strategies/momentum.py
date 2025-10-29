"""
Momentum continuation strategy.

Entry: Price breaks above N-day high with volume > 1.5x average
Stop: Below breakout level or entry - (ATR * multiplier)
Target: Entry + (Risk * R-multiple)
Exit: Target hit or trailing stop triggered
"""
from typing import Optional
import pandas as pd
import numpy as np

from .base import BaseStrategy
import config


class MomentumStrategy(BaseStrategy):
    """Momentum breakout strategy."""
    
    def __init__(
        self,
        lookback: int = config.MOMENTUM_LOOKBACK,
        volume_mult: float = config.MOMENTUM_VOLUME_MULT,
        atr_stop_mult: float = config.MOMENTUM_ATR_STOP_MULT,
        target_r: float = config.MOMENTUM_TARGET_R
    ):
        """Initialize momentum strategy.
        
        Args:
            lookback: Days for high detection
            volume_mult: Required volume multiple vs average
            atr_stop_mult: ATR multiplier for stop distance
            target_r: Target as R-multiple
        """
        super().__init__("Momentum")
        self.lookback = lookback
        self.volume_mult = volume_mult
        self.atr_stop_mult = atr_stop_mult
        self.target_r = target_r
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals.
        
        Conditions:
        1. Close > high of prior N days
        2. Volume > volume_mult * average volume
        3. Price above 20 EMA (trend confirmation)
        
        Args:
            df: DataFrame with OHLCV and indicators
        
        Returns:
            DataFrame with signal columns
        """
        df = df.copy()
        
        # Ensure we have required indicators
        if 'high_20' not in df.columns or 'volume_20' not in df.columns:
            from data import add_technical_indicators
            df = add_technical_indicators(df)
        
        # Initialize signal columns
        df['signal'] = 0
        df['entry'] = np.nan
        df['stop'] = np.nan
        df['target'] = np.nan
        
        # Breakout condition
        df['is_breakout'] = (df['close'] > df['high_20'].shift(1))
        
        # Volume condition
        df['volume_surge'] = (df['volume'] > self.volume_mult * df['volume_20'])
        
        # Trend condition (above 20 EMA)
        df['above_ema'] = (df['close'] > df['ema_20'])
        
        # Combined signal
        df['signal'] = np.where(
            df['is_breakout'] & df['volume_surge'] & df['above_ema'],
            1,  # Long signal
            0
        )
        
        # Calculate entry, stop, target for signals
        for idx in df[df['signal'] == 1].index:
            entry = df.loc[idx, 'close']
            
            # Stop: lower of (previous high or entry - ATR*mult)
            prev_high = df.loc[:idx, 'high'].iloc[-self.lookback-1:-1].max()
            atr_stop = entry - (df.loc[idx, 'atr_14'] * self.atr_stop_mult)
            stop = max(prev_high, atr_stop)
            
            # Ensure stop is below entry
            if stop >= entry:
                stop = entry * 0.97  # Emergency stop at 3% below entry
            
            # Target based on R-multiple
            risk = entry - stop
            target = entry + (risk * self.target_r)
            
            df.loc[idx, 'entry'] = entry
            df.loc[idx, 'stop'] = stop
            df.loc[idx, 'target'] = target
        
        return df
    
    def scan(self, symbol: str, df: pd.DataFrame) -> Optional[dict]:
        """Scan for momentum setup.
        
        Args:
            symbol: Ticker symbol
            df: DataFrame with OHLCV data
        
        Returns:
            Trade plan if setup found, None otherwise
        """
        if df.empty or len(df) < self.lookback + 20:
            return None
        
        # Add indicators
        from data import add_technical_indicators
        df = add_technical_indicators(df)
        
        # Generate signals
        df = self.generate_signals(df)
        
        # Check for signal on last bar
        last_idx = df.index[-1]
        if df.loc[last_idx, 'signal'] != 1:
            return None
        
        # Extract setup details
        entry = df.loc[last_idx, 'entry']
        stop = df.loc[last_idx, 'stop']
        target = df.loc[last_idx, 'target']
        
        if pd.isna(entry) or pd.isna(stop) or pd.isna(target):
            return None
        
        # Calculate confidence based on signal strength
        volume_ratio = df.loc[last_idx, 'volume'] / df.loc[last_idx, 'volume_20']
        trend_strength = (df.loc[last_idx, 'close'] - df.loc[last_idx, 'ema_20']) / df.loc[last_idx, 'ema_20']
        
        confidence = min(
            (volume_ratio / self.volume_mult) * 0.5 +  # 50% weight on volume
            (min(trend_strength * 10, 1.0)) * 0.5,      # 50% weight on trend
            1.0
        )
        
        return {
            'symbol': symbol,
            'setup': 'momentum_breakout',
            'entry': float(entry),
            'stop': float(stop),
            'target': float(target),
            'timeframe': 'intraday',
            'confidence': float(confidence),
            'notes': (
                f"Breakout above {self.lookback}-day high. "
                f"Volume: {volume_ratio:.1f}x avg. "
                f"R:R = 1:{self.target_r}"
            )
        }
    
    def check_exit(
        self,
        entry_price: float,
        current_price: float,
        current_atr: float,
        original_stop: float
    ) -> tuple[bool, float, str]:
        """Check if position should exit and calculate updated stop.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            current_atr: Current ATR value
            original_stop: Original stop price
        
        Returns:
            Tuple of (should_exit, new_stop, reason)
        """
        risk = entry_price - original_stop
        profit = current_price - entry_price
        r_multiple = profit / risk if risk > 0 else 0
        
        # Move to breakeven at +1R
        if r_multiple >= 1.0:
            new_stop = entry_price
        else:
            new_stop = original_stop
        
        # Trailing stop after +1.5R
        if r_multiple >= config.MOMENTUM_TRAIL_R:
            trailing = current_price - (current_atr * self.atr_stop_mult)
            new_stop = max(new_stop, trailing)
        
        # Check if stop hit
        should_exit = current_price <= new_stop
        reason = "Stop hit" if should_exit else "Holding"
        
        return should_exit, new_stop, reason


if __name__ == "__main__":
    # Test momentum strategy
    print("Testing Momentum Strategy\n")
    print("=" * 70)
    
    strategy = MomentumStrategy()
    print(f"Strategy: {strategy}")
    print(f"Lookback: {strategy.lookback} days")
    print(f"Volume Multiple: {strategy.volume_mult}x")
    print(f"ATR Stop Multiple: {strategy.atr_stop_mult}x")
    print(f"Target R: {strategy.target_r}R")
    print()
    
    # Create sample data with breakout pattern
    dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
    
    # Simulate consolidation then breakout
    prices = np.concatenate([
        np.random.uniform(95, 105, 30),  # Consolidation
        np.linspace(105, 120, 20)        # Breakout
    ])
    
    volumes = np.concatenate([
        np.random.uniform(1e6, 1.5e6, 30),  # Normal volume
        np.random.uniform(2e6, 3e6, 20)      # High volume
    ])
    
    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': volumes
    }, index=dates)
    
    # Add indicators
    from data import add_technical_indicators
    df = add_technical_indicators(df)
    
    # Generate signals
    df_signals = strategy.generate_signals(df)
    
    # Show signals
    signals = df_signals[df_signals['signal'] == 1]
    print(f"Found {len(signals)} momentum signals:")
    print()
    
    for idx, row in signals.iterrows():
        print(f"Date: {idx.date()}")
        print(f"  Entry: ${row['entry']:.2f}")
        print(f"  Stop:  ${row['stop']:.2f}")
        print(f"  Target: ${row['target']:.2f}")
        print(f"  Risk: ${row['entry'] - row['stop']:.2f}")
        print(f"  Reward: ${row['target'] - row['entry']:.2f}")
        print(f"  R:R: 1:{(row['target'] - row['entry']) / (row['entry'] - row['stop']):.1f}")
        print()
    
    # Test scan
    print("-" * 70)
    print("Testing scan function:")
    setup = strategy.scan('TEST', df)
    if setup:
        print(f"✅ Setup found: {setup['setup']}")
        print(f"   Confidence: {setup['confidence']:.1%}")
        print(f"   Entry: ${setup['entry']:.2f}")
        print(f"   Stop: ${setup['stop']:.2f}")
        print(f"   Target: ${setup['target']:.2f}")
        print(f"   Notes: {setup['notes']}")
    else:
        print("❌ No setup found")
    
    print("\n✅ Momentum strategy tests complete")

