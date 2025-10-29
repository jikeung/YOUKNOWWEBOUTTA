"""
Base strategy class defining the interface all strategies must implement.
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str):
        """Initialize strategy.
        
        Args:
            name: Strategy name
        """
        self.name = name
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data and indicators
        
        Returns:
            DataFrame with additional columns:
            - signal: 1 (long), 0 (neutral), -1 (short/exit)
            - entry: suggested entry price
            - stop: suggested stop price
            - target: suggested target price
        """
        pass
    
    @abstractmethod
    def scan(self, symbol: str, df: pd.DataFrame) -> Optional[dict]:
        """Scan a single symbol for trade setup.
        
        Args:
            symbol: Ticker symbol
            df: DataFrame with OHLCV data and indicators
        
        Returns:
            Trade plan dict if setup found, None otherwise:
            {
                'symbol': str,
                'setup': str,
                'entry': float,
                'stop': float,
                'target': float,
                'timeframe': str,
                'confidence': float (0-1),
                'notes': str
            }
        """
        pass
    
    def __str__(self) -> str:
        return f"{self.name}Strategy"

