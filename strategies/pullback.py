"""
Breakout-Pullback strategy.

Entry: Prior breakout confirmed; pullback to EMA(20) with diminishing volume, 
       re-break on rising volume
Stop: Below pullback low or entry - (ATR * multiplier)
Target: Entry + (Risk * R-multiple)
Exit: Target hit or trailing stop triggered
"""
from typing import Optional
import pandas as pd
import numpy as np

from .base import BaseStrategy
import config


class PullbackStrategy(BaseStrategy):
    """Breakout-pullback reentry strategy."""
    
    def __init__(
        self,
        ema_period: int = config.PULLBACK_EMA_PERIOD,
        volume_decline: float = config.PULLBACK_VOLUME_DECLINE,
        atr_stop_mult: float = config.PULLBACK_ATR_STOP_MULT,
        target_r: float = config.PULLBACK_TARGET_R
    ):
        """Initialize pullback strategy.
        
        Args:
            ema_period: EMA period for pullback level
            volume_decline: Pullback volume threshold (< this * breakout volume)
            atr_stop_mult: ATR multiplier for stop distance
            target_r: Target as R-multiple
        """
        super().__init__("Pullback")
        self.ema_period = ema_period
        self.volume_decline = volume_decline
        self.atr_stop_mult = atr_stop_mult
        self.target_r = target_r
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate pullback signals.
        
        Conditions:
        1. Prior breakout identified (high > previous 20-day high)
        2. Pullback to EMA with declining volume
        3. Re-break above recent high with volume increase
        
        Args:
            df: DataFrame with OHLCV and indicators
        
        Returns:
            DataFrame with signal columns
        """
        df = df.copy()
        
        # Ensure we have required indicators
        if 'ema_20' not in df.columns or 'volume_20' not in df.columns:
            from data import add_technical_indicators
            df = add_technical_indicators(df)
        
        # Initialize signal columns
        df['signal'] = 0
        df['entry'] = np.nan
        df['stop'] = np.nan
        df['target'] = np.nan
        
        # Identify breakouts (for context)
        df['breakout'] = (df['high'] > df['high_20'].shift(1))
        
        # Identify pullbacks (price touches or crosses EMA from above)
        df['near_ema'] = np.abs(df['low'] - df['ema_20']) / df['ema_20'] < 0.02  # Within 2%
        df['volume_declining'] = df['volume'] < df['volume'].shift(1)
        
        # Re-break conditions
        df['price_rising'] = df['close'] > df['high'].shift(1)
        df['volume_rising'] = df['volume'] > df['volume'].shift(1)
        
        # Look for pullback pattern over last 5-10 bars
        for i in range(10, len(df)):
            # Check if there was a breakout 5-10 bars ago
            lookback = df.iloc[i-10:i-2]
            if not lookback['breakout'].any():
                continue
            
            # Check if there was a pullback to EMA in last 2-5 bars
            pullback_window = df.iloc[i-5:i]
            had_pullback = pullback_window['near_ema'].any()
            had_volume_decline = pullback_window['volume_declining'].sum() >= 2
            
            if not (had_pullback and had_volume_decline):
                continue
            
            # Check for re-break on current bar
            current = df.iloc[i]
            if current['price_rising'] and current['volume_rising']:
                df.iloc[i, df.columns.get_loc('signal')] = 1
        
        # Calculate entry, stop, target for signals
        for idx in df[df['signal'] == 1].index:
            entry = df.loc[idx, 'close']
            
            # Stop: below pullback low
            pullback_window = df.loc[:idx].tail(5)
            pullback_low = pullback_window['low'].min()
            
            # Also consider ATR-based stop
            atr_stop = entry - (df.loc[idx, 'atr_14'] * self.atr_stop_mult)
            
            # Use the higher of the two (less aggressive)
            stop = max(pullback_low, atr_stop)
            
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
    
    def scan(self, symbol: str, df: pd.DataFrame, debug: bool = False) -> Optional[dict]:
        """Scan for pullback setup.
        
        Args:
            symbol: Ticker symbol
            df: DataFrame with OHLCV data
            debug: Enable detailed debug logging
        
        Returns:
            Trade plan if setup found, None otherwise
        """
        if debug:
            print(f"\n[DEBUG] === PULLBACK SCAN START: {symbol} ===")
        
        # Step 1: Validate input data
        if df.empty:
            if debug:
                print(f"[DEBUG] FAILED: DataFrame is empty")
            return None
        
        if len(df) < 30:
            if debug:
                print(f"[DEBUG] FAILED: Insufficient data - {len(df)} bars (need 30+)")
            return None
        
        if debug:
            print(f"[DEBUG] Step 1 PASSED: Data shape = {df.shape}")
            print(f"[DEBUG] Date range: {df.index[0]} to {df.index[-1]}")
            print(f"[DEBUG] Last close: ${df['close'].iloc[-1]:.2f}")
        
        # Step 2: Add indicators
        from data import add_technical_indicators
        df = add_technical_indicators(df)
        
        if debug:
            print(f"[DEBUG] Step 2 PASSED: Indicators added")
            last_bar = df.iloc[-1]
            print(f"[DEBUG] Last bar indicators:")
            print(f"  - EMA(20): ${last_bar.get('ema_20', 'N/A'):.2f}")
            print(f"  - Volume: {last_bar.get('volume', 'N/A'):,.0f}")
            print(f"  - Volume(20): {last_bar.get('volume_20', 'N/A'):,.0f}")
            print(f"  - ATR(14): {last_bar.get('atr_14', 'N/A'):.2f}")
            print(f"  - High(20): ${last_bar.get('high_20', 'N/A'):.2f}")
        
        # Step 3: Generate signals
        df = self.generate_signals(df)
        
        # Count signals found
        signals_found = (df['signal'] == 1).sum()
        if debug:
            print(f"[DEBUG] Step 3 PASSED: Signal generation complete")
            print(f"[DEBUG] Total signals in data: {signals_found}")
        
        # Step 4: Check for signal on last bar
        last_idx = df.index[-1]
        last_signal = df.loc[last_idx, 'signal']
        
        if debug:
            print(f"[DEBUG] Step 4: Checking last bar signal")
            print(f"[DEBUG] Last bar signal value: {last_signal}")
            
            # Show recent bars and their signals
            print(f"[DEBUG] Recent 5 bars signals:")
            for i in range(max(0, len(df)-5), len(df)):
                bar = df.iloc[i]
                print(f"  [{df.index[i].date()}] Signal: {bar['signal']}, Close: ${bar['close']:.2f}")
        
        if last_signal != 1:
            if debug:
                print(f"[DEBUG] FAILED: No signal on last bar (value={last_signal})")
                # Check why no signal
                last_bar = df.iloc[-1]
                print(f"[DEBUG] Checking signal conditions:")
                if 'is_breakout' in df.columns:
                    print(f"  - Breakout in history: {df['is_breakout'].iloc[-10:].sum()} (last 10 bars)")
                if 'near_ema' in df.columns:
                    print(f"  - Near EMA (last 5): {df['near_ema'].iloc[-5:].sum()}")
                if 'price_rising' in df.columns:
                    print(f"  - Price rising: {last_bar.get('price_rising', 'N/A')}")
                if 'volume_rising' in df.columns:
                    print(f"  - Volume rising: {last_bar.get('volume_rising', 'N/A')}")
            return None
        
        if debug:
            print(f"[DEBUG] Step 4 PASSED: Signal found on last bar!")
        
        # Step 5: Extract setup details
        entry = df.loc[last_idx, 'entry']
        stop = df.loc[last_idx, 'stop']
        target = df.loc[last_idx, 'target']
        
        if debug:
            print(f"[DEBUG] Step 5: Extracted values")
            print(f"  - Entry: {entry}")
            print(f"  - Stop: {stop}")
            print(f"  - Target: {target}")
        
        if pd.isna(entry) or pd.isna(stop) or pd.isna(target):
            if debug:
                print(f"[DEBUG] FAILED: NaN values detected")
                print(f"  - Entry is NaN: {pd.isna(entry)}")
                print(f"  - Stop is NaN: {pd.isna(stop)}")
                print(f"  - Target is NaN: {pd.isna(target)}")
            return None
        
        if debug:
            print(f"[DEBUG] Step 5 PASSED: All values valid")
        
        # Step 6: Calculate confidence
        volume_strength = df.loc[last_idx, 'volume'] / df.loc[last_idx, 'volume_20']
        ema_distance = abs(df.loc[last_idx, 'low'] - df.loc[last_idx, 'ema_20']) / df.loc[last_idx, 'ema_20']
        
        # Closer to EMA is better (inverse relationship)
        ema_score = max(0, 1 - (ema_distance / 0.05))  # Normalize to 0-1
        volume_score = min(volume_strength / 2.0, 1.0)  # Volume > 2x = max score
        
        confidence = (ema_score * 0.4 + volume_score * 0.6)
        
        if debug:
            print(f"[DEBUG] Step 6: Confidence calculation")
            print(f"  - Volume strength: {volume_strength:.2f}x")
            print(f"  - EMA distance: {ema_distance:.2%}")
            print(f"  - EMA score: {ema_score:.2f}")
            print(f"  - Volume score: {volume_score:.2f}")
            print(f"  - Final confidence: {confidence:.2%}")
        
        setup = {
            'symbol': symbol,
            'setup': 'breakout_pullback',
            'entry': float(entry),
            'stop': float(stop),
            'target': float(target),
            'timeframe': 'swing',
            'confidence': float(confidence),
            'notes': (
                f"Pullback to EMA({self.ema_period}), re-break with volume. "
                f"Volume: {volume_strength:.1f}x avg. "
                f"R:R = 1:{self.target_r}"
            )
        }
        
        if debug:
            print(f"[DEBUG] === PULLBACK SCAN SUCCESS ===")
            print(f"[DEBUG] Setup: {setup}")
            print()
        
        return setup
    
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
        
        # Trailing stop after +1.5R (more conservative than momentum)
        if r_multiple >= config.PULLBACK_TRAIL_R:
            trailing = current_price - (current_atr * self.atr_stop_mult)
            new_stop = max(new_stop, trailing)
        
        # Check if stop hit
        should_exit = current_price <= new_stop
        reason = "Stop hit" if should_exit else "Holding"
        
        return should_exit, new_stop, reason


if __name__ == "__main__":
    # Test pullback strategy
    print("Testing Pullback Strategy\n")
    print("=" * 70)
    
    strategy = PullbackStrategy()
    print(f"Strategy: {strategy}")
    print(f"EMA Period: {strategy.ema_period}")
    print(f"Volume Decline: {strategy.volume_decline}")
    print(f"ATR Stop Multiple: {strategy.atr_stop_mult}x")
    print(f"Target R: {strategy.target_r}R")
    print()
    
    # Create sample data with breakout-pullback pattern
    dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='D')
    
    # Simulate: consolidation -> breakout -> pullback -> continuation
    prices = np.concatenate([
        np.random.uniform(95, 105, 20),   # Consolidation
        np.linspace(105, 125, 10),        # Breakout
        np.linspace(125, 115, 8),         # Pullback
        np.linspace(115, 135, 22)         # Continuation
    ])
    
    volumes = np.concatenate([
        np.random.uniform(1e6, 1.5e6, 20),  # Normal
        np.random.uniform(2e6, 3e6, 10),    # High on breakout
        np.random.uniform(0.8e6, 1.2e6, 8), # Low on pullback
        np.random.uniform(1.5e6, 2.5e6, 22) # Rising on continuation
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
    print(f"Found {len(signals)} pullback signals:")
    print()
    
    for idx, row in signals.iterrows():
        print(f"Date: {idx.date()}")
        print(f"  Entry: ${row['entry']:.2f}")
        print(f"  Stop:  ${row['stop']:.2f}")
        print(f"  Target: ${row['target']:.2f}")
        print(f"  Risk: ${row['entry'] - row['stop']:.2f}")
        print(f"  Reward: ${row['target'] - row['entry']:.2f}")
        if (row['entry'] - row['stop']) > 0:
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
    
    print("\n✅ Pullback strategy tests complete")

