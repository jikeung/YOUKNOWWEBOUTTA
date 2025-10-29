"""
Simple Alpaca API connection demo.

This is a basic connection test. For the full trading system, see:
  - README.md for setup instructions
  - runner.py for CLI commands
  - backtest.py for strategy testing
"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

# Load environment variables
load_dotenv()

# Get API credentials from environment variables
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'

def main():
    """Test Alpaca API connection."""
    print("\n" + "="*70)
    print("ALPACA API CONNECTION TEST")
    print("="*70)
    
    # Initialize the trading client
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=PAPER_TRADING)
    
    # Initialize the data client
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    
    # Test the connection by getting account information
    try:
        account = trading_client.get_account()
        print("[OK] Successfully connected to Alpaca API!")
        print(f"\nAccount Information:")
        print(f"  Account Number: {account.account_number}")
        print(f"  Status: {account.status}")
        print(f"  Cash: ${float(account.cash):,.2f}")
        print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"  Buying Power: ${float(account.buying_power):,.2f}")
        print(f"  Paper Trading: {PAPER_TRADING}")
        
        # Example: Get latest quote for a stock
        print("\n" + "-"*70)
        print("Example: Getting latest quote for AAPL")
        print("-"*70)
        
        request_params = StockLatestQuoteRequest(symbol_or_symbols=["AAPL"])
        latest_quote = data_client.get_stock_latest_quote(request_params)
        
        if "AAPL" in latest_quote:
            quote = latest_quote["AAPL"]
            print(f"\nAAPL Latest Quote:")
            print(f"  Ask Price: ${quote.ask_price}")
            print(f"  Bid Price: ${quote.bid_price}")
            print(f"  Ask Size: {quote.ask_size}")
            print(f"  Bid Size: {quote.bid_size}")
        
        print("\n" + "="*70)
        print("[SUCCESS] Connection test successful!")
        print("="*70)
        
        print("\nNext Steps:")
        print("  1. Read README.md for full system documentation")
        print("  2. Run: python runner.py scan --strategy momentum --timeframe 15Min")
        print("  3. Run: python runner.py trade --paper --symbol AAPL --strategy momentum --dry-run")
        print("  4. Run: python backtest.py (to test strategies on historical data)")
        print("\n")
            
    except Exception as e:
        print(f"[ERROR] Error connecting to Alpaca API: {e}")
        print("\nMake sure you have:")
        print("  1. Created a .env file with your API credentials")
        print("  2. Set ALPACA_API_KEY and ALPACA_SECRET_KEY")
        print("  3. Get your keys from: https://app.alpaca.markets/paper/dashboard/overview")
        print("\nSee .env.example for template")

if __name__ == "__main__":
    main()

