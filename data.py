"""
Market data access module.
Handles data fetching from Alpaca API with liquidity and price filters.
"""
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestQuoteRequest,
    StockSnapshotRequest
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

import config


class DataClient:
    """Wrapper around Alpaca data API with filtering and validation."""
    
    def __init__(self):
        """Initialize data client."""
        self.client = StockHistoricalDataClient(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY
        )
    
    def _parse_timeframe(self, timeframe: str) -> TimeFrame:
        """Convert string timeframe to Alpaca TimeFrame object.
        
        Args:
            timeframe: e.g., '1Min', '5Min', '15Min', '1Hour', '1Day'
        
        Returns:
            Alpaca TimeFrame object
        """
        tf_map = {
            '1Min': TimeFrame(1, TimeFrameUnit.Minute),
            '5Min': TimeFrame(5, TimeFrameUnit.Minute),
            '15Min': TimeFrame(15, TimeFrameUnit.Minute),
            '30Min': TimeFrame(30, TimeFrameUnit.Minute),
            '1Hour': TimeFrame(1, TimeFrameUnit.Hour),
            '1Day': TimeFrame(1, TimeFrameUnit.Day),
        }
        
        if timeframe not in tf_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Use: {list(tf_map.keys())}")
        
        return tf_map[timeframe]
    
    def get_ohlcv(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = '1Day'
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV data for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            start: Start datetime
            end: End datetime
            timeframe: Bar timeframe (e.g., '1Min', '5Min', '1Day')
        
        Returns:
            Dict mapping symbol -> DataFrame with columns [open, high, low, close, volume]
        """
        if not symbols:
            return {}
        
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=self._parse_timeframe(timeframe),
                start=start,
                end=end
            )
            
            bars = self.client.get_stock_bars(request)
            
            # Convert to dict of DataFrames
            result = {}
            for symbol in symbols:
                if symbol in bars.data:
                    df = bars.df
                    if isinstance(df.index, pd.MultiIndex):
                        # Multi-symbol response
                        symbol_data = df.xs(symbol, level='symbol')
                    else:
                        symbol_data = df
                    
                    # Ensure we have the required columns
                    if not symbol_data.empty:
                        result[symbol] = symbol_data
            
            return result
            
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return {}
    
    def get_latest_quote(self, symbols: list[str]) -> dict[str, dict]:
        """Get latest quote (bid/ask) for symbols.
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            Dict mapping symbol -> {'bid': float, 'ask': float, 'bid_size': int, 'ask_size': int}
        """
        if not symbols:
            return {}
        
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self.client.get_stock_latest_quote(request)
            
            result = {}
            for symbol, quote in quotes.items():
                result[symbol] = {
                    'bid': float(quote.bid_price) if quote.bid_price else 0.0,
                    'ask': float(quote.ask_price) if quote.ask_price else 0.0,
                    'bid_size': int(quote.bid_size) if quote.bid_size else 0,
                    'ask_size': int(quote.ask_size) if quote.ask_size else 0,
                }
            
            return result
            
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}
    
    def get_snapshot(self, symbols: list[str]) -> dict[str, dict]:
        """Get current snapshot (latest price, volume, quote) for symbols.
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            Dict with latest trade info and daily stats
        """
        if not symbols:
            return {}
        
        try:
            request = StockSnapshotRequest(symbol_or_symbols=symbols)
            snapshots = self.client.get_stock_snapshot(request)
            
            result = {}
            for symbol, snapshot in snapshots.items():
                latest_trade = snapshot.latest_trade
                daily_bar = snapshot.daily_bar
                
                result[symbol] = {
                    'price': float(latest_trade.price) if latest_trade else 0.0,
                    'volume': int(daily_bar.volume) if daily_bar else 0,
                    'open': float(daily_bar.open) if daily_bar else 0.0,
                    'high': float(daily_bar.high) if daily_bar else 0.0,
                    'low': float(daily_bar.low) if daily_bar else 0.0,
                    'close': float(daily_bar.close) if daily_bar else 0.0,
                }
            
            return result
            
        except Exception as e:
            print(f"Error fetching snapshots: {e}")
            return {}


def calculate_avg_dollar_volume(df: pd.DataFrame, periods: int = 20) -> float:
    """Calculate average dollar volume over N periods.
    
    Args:
        df: DataFrame with 'close' and 'volume' columns
        periods: Number of periods to average
    
    Returns:
        Average dollar volume
    """
    if df.empty or len(df) < periods:
        return 0.0
    
    dollar_volume = df['close'] * df['volume']
    return dollar_volume.tail(periods).mean()


def filter_by_liquidity(
    data: dict[str, pd.DataFrame],
    min_price: float = config.MIN_STOCK_PRICE,
    min_dollar_volume: float = config.MIN_AVG_DOLLAR_VOLUME,
    periods: int = 20
) -> dict[str, pd.DataFrame]:
    """Filter symbols by price and liquidity requirements.
    
    Args:
        data: Dict of symbol -> DataFrame
        min_price: Minimum stock price
        min_dollar_volume: Minimum average dollar volume
        periods: Periods for volume average
    
    Returns:
        Filtered dict with only qualifying symbols
    """
    filtered = {}
    
    for symbol, df in data.items():
        if df.empty:
            continue
        
        # Check latest price
        latest_price = df['close'].iloc[-1]
        if latest_price < min_price:
            continue
        
        # Check average dollar volume
        avg_dv = calculate_avg_dollar_volume(df, periods)
        if avg_dv < min_dollar_volume:
            continue
        
        filtered[symbol] = df
    
    return filtered


def get_universe(
    symbols: Optional[list[str]] = None,
    min_price: float = config.MIN_STOCK_PRICE,
    min_dollar_volume: float = config.MIN_AVG_DOLLAR_VOLUME,
    lookback_days: int = 30
) -> list[str]:
    """Get tradeable universe of stocks meeting liquidity and price filters.
    
    Args:
        symbols: Optional list of symbols to filter. If None, uses a default set.
        min_price: Minimum stock price
        min_dollar_volume: Minimum average dollar volume
        lookback_days: Days of data to check
    
    Returns:
        List of qualifying ticker symbols
    """
    # Default universe: popular liquid stocks and ETFs
    if symbols is None:
        symbols = [
            # Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'NFLX',
            # Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS',
            # Consumer
            'WMT', 'HD', 'NKE', 'SBUX', 'MCD',
            # Healthcare
            'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO',
            # Energy
            'XOM', 'CVX', 'COP',
            # ETFs
            'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLP'
        ]
    
    client = DataClient()
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    
    # Fetch data
    data = client.get_ohlcv(symbols, start, end, timeframe='1Day')
    
    # Filter by liquidity
    filtered = filter_by_liquidity(data, min_price, min_dollar_volume)
    
    qualifying = list(filtered.keys())
    print(f"Universe: {len(qualifying)}/{len(symbols)} symbols qualify")
    
    return qualifying


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add common technical indicators to OHLCV DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with additional indicator columns
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Moving averages
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr_14'] = true_range.rolling(14).mean()
    
    # Volume average
    df['volume_20'] = df['volume'].rolling(20).mean()
    
    # Rolling high/low
    df['high_20'] = df['high'].rolling(20).max()
    df['low_20'] = df['low'].rolling(20).min()
    
    return df


if __name__ == "__main__":
    # Test data access
    print("Testing data access...")
    
    client = DataClient()
    end = datetime.now()
    start = end - timedelta(days=5)
    
    # Test OHLCV
    print("\n1. Testing OHLCV fetch...")
    data = client.get_ohlcv(['AAPL', 'MSFT'], start, end, '1Day')
    for symbol, df in data.items():
        print(f"  {symbol}: {len(df)} bars")
        if not df.empty:
            print(f"    Latest close: ${df['close'].iloc[-1]:.2f}")
    
    # Test quotes
    print("\n2. Testing latest quotes...")
    quotes = client.get_latest_quote(['AAPL', 'MSFT'])
    for symbol, quote in quotes.items():
        print(f"  {symbol}: Bid ${quote['bid']:.2f}, Ask ${quote['ask']:.2f}")
    
    # Test universe
    print("\n3. Testing universe filtering...")
    universe = get_universe(symbols=['AAPL', 'MSFT', 'SPY', 'QQQ'], lookback_days=30)
    print(f"  Qualifying symbols: {universe}")
    
    print("\n✅ Data module tests complete")

