"""
Broker module - wrapper around Alpaca TradingClient with safety guards.
Implements double-confirmation for live trading.
"""
from typing import Optional, Literal
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopLossRequest,
    TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.common.exceptions import APIError

import config


class LiveTradingError(Exception):
    """Raised when attempting live trading without proper authorization."""
    pass


class Broker:
    """Wrapper around Alpaca TradingClient with safety guards."""
    
    def __init__(self, paper: bool = True, cli_confirm: bool = False):
        """Initialize broker client.
        
        Args:
            paper: Use paper trading account
            cli_confirm: CLI confirmation for live trading
        
        Raises:
            LiveTradingError: If attempting live trading without proper auth
        """
        # SAFETY CHECK: Enforce paper trading unless explicitly authorized
        if not paper:
            if not config.ALLOW_LIVE_TRADING:
                raise LiveTradingError(
                    "[ERROR] Live trading blocked: ALLOW_LIVE_TRADING=False in environment\n"
                    "   Set ALLOW_LIVE_TRADING=true in .env to enable"
                )
            
            if not cli_confirm:
                raise LiveTradingError(
                    "[ERROR] Live trading blocked: CLI confirmation required\n"
                    "   Use --i-accept-live-risk flag when running"
                )
            
            # Final warning
            print("\n" + "!" * 80)
            print("[WARNING]  LIVE TRADING MODE ENABLED - REAL MONEY AT RISK [WARNING]")
            print("!" * 80 + "\n")
        
        self.paper = paper
        self.client = TradingClient(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            paper=paper
        )
        
        mode = "PAPER" if paper else "LIVE"
        print(f"[OK] Broker initialized in {mode} mode")
    
    def get_account(self) -> dict:
        """Get account information.
        
        Returns:
            Dict with account details
        """
        try:
            account = self.client.get_account()
            return {
                'account_number': account.account_number,
                'status': account.status,
                'cash': float(account.cash),
                'equity': float(account.equity),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
            }
        except APIError as e:
            print(f"Error fetching account: {e}")
            return {}
    
    def get_positions(self) -> list[dict]:
        """Get current positions.
        
        Returns:
            List of position dicts
        """
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'qty': int(pos.qty),
                    'side': pos.side,
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                }
                for pos in positions
            ]
        except APIError as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def place_order(
        self,
        symbol: str,
        side: Literal['buy', 'sell'],
        qty: int,
        order_type: Literal['market', 'limit'] = 'market',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = 'day'
    ) -> Optional[dict]:
        """Place an order with validation.
        
        Args:
            symbol: Ticker symbol
            side: 'buy' or 'sell'
            qty: Number of shares
            order_type: 'market' or 'limit'
            limit_price: Limit price for limit orders
            stop_price: Stop loss price
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
        
        Returns:
            Order details dict or None if failed
        """
        # Validate
        if qty <= 0:
            print(f"[ERROR] Invalid quantity: {qty}")
            return None
        
        if not config.TRADING_MODE == 'long_only' or side != 'buy':
            if not config.SHORTING_ALLOWED and side == 'sell':
                # Check if this is closing a position
                positions = self.get_positions()
                has_position = any(p['symbol'] == symbol and int(p['qty']) > 0 for p in positions)
                if not has_position:
                    print(f"[ERROR] Shorting not allowed by config")
                    return None
        
        # Convert types
        order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
        tif = TimeInForce.DAY if time_in_force == 'day' else TimeInForce.GTC
        
        try:
            # Create order request
            if order_type == 'market':
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif
                )
            elif order_type == 'limit':
                if limit_price is None:
                    print("[ERROR] Limit price required for limit orders")
                    return None
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif,
                    limit_price=limit_price
                )
            else:
                print(f"[ERROR] Unsupported order type: {order_type}")
                return None
            
            # Submit order
            order = self.client.submit_order(order_request)
            
            print(f"[OK] Order placed: {side.upper()} {qty} {symbol} @ {order_type}")
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': int(order.qty),
                'side': str(order.side),
                'type': str(order.type),
                'status': str(order.status),
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            }
            
        except APIError as e:
            print(f"[ERROR] Order failed: {e}")
            return None
    
    def place_bracket_order(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        stop_price: float,
        target_price: float
    ) -> Optional[dict]:
        """Place a bracket order (entry + stop + target).
        
        Args:
            symbol: Ticker symbol
            qty: Number of shares
            limit_price: Entry limit price
            stop_price: Stop loss price
            target_price: Take profit price
        
        Returns:
            Order details or None
        """
        try:
            # Create bracket order
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
                stop_loss=StopLossRequest(stop_price=stop_price),
                take_profit=TakeProfitRequest(limit_price=target_price)
            )
            
            order = self.client.submit_order(order_request)
            
            print(f"[OK] Bracket order placed: BUY {qty} {symbol}")
            print(f"  Entry: ${limit_price:.2f}")
            print(f"  Stop: ${stop_price:.2f}")
            print(f"  Target: ${target_price:.2f}")
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': int(order.qty),
                'status': str(order.status),
            }
            
        except APIError as e:
            print(f"[ERROR] Bracket order failed: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if cancelled, False otherwise
        """
        try:
            self.client.cancel_order_by_id(order_id)
            print(f"[OK] Order {order_id} cancelled")
            return True
        except APIError as e:
            print(f"[ERROR] Cancel failed: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders.
        
        Returns:
            True if successful
        """
        try:
            self.client.cancel_orders()
            print("[OK] All orders cancelled")
            return True
        except APIError as e:
            print(f"[ERROR] Cancel all failed: {e}")
            return False
    
    def flatten_position(self, symbol: str) -> bool:
        """Close a position completely.
        
        Args:
            symbol: Symbol to close
        
        Returns:
            True if successful
        """
        try:
            self.client.close_position(symbol)
            print(f"[OK] Position {symbol} closed")
            return True
        except APIError as e:
            print(f"[ERROR] Close position failed: {e}")
            return False
    
    def flatten_all_positions(self) -> bool:
        """Close all positions.
        
        Returns:
            True if successful
        """
        try:
            self.client.close_all_positions(cancel_orders=True)
            print("[OK] All positions closed")
            return True
        except APIError as e:
            print(f"[ERROR] Close all positions failed: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[dict]:
        """Get order details.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order details dict or None
        """
        try:
            order = self.client.get_order_by_id(order_id)
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': int(order.qty),
                'side': str(order.side),
                'type': str(order.type),
                'status': str(order.status),
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            }
        except APIError as e:
            print(f"[ERROR] Get order failed: {e}")
            return None


if __name__ == "__main__":
    # Test broker (paper trading)
    print("Testing Broker Module\n")
    print("=" * 70)
    
    # Test 1: Initialize in paper mode (should succeed)
    print("Test 1: Initialize paper trading")
    try:
        broker = Broker(paper=True)
        print("[SUCCESS] Paper broker initialized\n")
    except Exception as e:
        print(f"[ERROR] Failed: {e}\n")
    
    # Test 2: Get account info
    print("Test 2: Get account info")
    account = broker.get_account()
    if account:
        print(f"[SUCCESS] Account: {account['account_number']}")
        print(f"   Equity: ${account['equity']:,.2f}")
        print(f"   Buying Power: ${account['buying_power']:,.2f}\n")
    else:
        print("[ERROR] Failed to get account\n")
    
    # Test 3: Get positions
    print("Test 3: Get positions")
    positions = broker.get_positions()
    print(f"[SUCCESS] Found {len(positions)} positions")
    for pos in positions[:3]:  # Show first 3
        print(f"   {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
    print()
    
    # Test 4: Try to initialize live trading without authorization (should fail)
    print("Test 4: Try live trading without authorization")
    try:
        live_broker = Broker(paper=False, cli_confirm=False)
        print("[ERROR] Should have failed!\n")
    except LiveTradingError as e:
        print(f"[SUCCESS] Correctly blocked: {str(e).split(chr(10))[0]}\n")
    
    # Test 5: Try live trading without CLI confirm (should fail)
    print("Test 5: Try live trading without CLI confirmation")
    # Temporarily enable in config
    original = config.ALLOW_LIVE_TRADING
    config.ALLOW_LIVE_TRADING = True
    try:
        live_broker = Broker(paper=False, cli_confirm=False)
        print("[ERROR] Should have failed!\n")
    except LiveTradingError as e:
        print(f"[SUCCESS] Correctly blocked: {str(e).split(chr(10))[0]}\n")
    finally:
        config.ALLOW_LIVE_TRADING = original
    
    print("=" * 70)
    print("[SUCCESS] Broker tests complete")
    print("\n[WARNING]  Note: Live trading requires BOTH:")
    print("   1. ALLOW_LIVE_TRADING=true in .env")
    print("   2. --i-accept-live-risk CLI flag")

