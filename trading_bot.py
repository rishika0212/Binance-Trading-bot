import logging
import json
import time
import threading
import sqlite3
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, Any, List
from binance import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import argparse
import sys
import os
from dotenv import load_dotenv

# New modules
from app.orders.oco import OCOManager
from app.orders.twap import TWAPExecutor
from app.orders.grid import GridTrader
from app.market.ws import PriceFeed
from app.strategy.sma_crossover import SMACrossover
from app.risk.manager import RiskManager
from app.storage.db import init_db, save_order
from app.api.server import create_app, Services
from app.backtest.data import DataFetcher
from app.backtest.engine import Backtester

class TradingBot:
    """
    A simplified trading bot for Binance Spot Testnet
    Supports market, limit, stop-limit orders, OCO, and comprehensive logging
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize the trading bot with API credentials
        
        Args:
            api_key (str): Binance API key
            api_secret (str): Binance API secret
            testnet (bool): Whether to use testnet (default: True)
        """
        try:
            # Spot Testnet: use testnet host explicitly
            if testnet:
                self.client = Client(api_key, api_secret, testnet=True)
                try:
                    # Ensure base_url is correct for spot testnet
                    if hasattr(self.client, 'BASE_URL'):
                        setattr(self.client, 'BASE_URL', 'https://testnet.binance.vision')
                except Exception:
                    pass
            else:
                self.client = Client(api_key, api_secret)

            # Setup logging
            self.setup_logging()
            
            # Test connection and fail early with helpful message
            if not self.test_connection():
                msg = ("API connection failed. For Spot Testnet, ensure keys are from testnet.binance.vision "
                       "and IP whitelist (if configured) allows access.")
                self.logger.error(msg)
                raise RuntimeError(msg)
            
            self.logger.info("Trading Bot initialized successfully")
            
        except Exception as e:
            # If logger not yet configured, print plain error too
            try:
                self.logger.error(f"Failed to initialize trading bot: {e}")
            except Exception:
                pass
            raise
    
    def setup_logging(self):
        """Setup comprehensive logging system"""
        # Create logger
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        file_handler = logging.FileHandler('trading_bot.log')
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def test_connection(self):
        """Test API connection and log response"""
        try:
            # Spot ping + account to verify connectivity and auth
            self.client.ping()
            account_info = self.client.get_account()
            self.logger.info("API connection successful")
            self.logger.debug(f"Account info: {json.dumps(account_info, indent=2)}")
            return True
        except Exception as e:
            self.logger.error(f"API connection failed: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information for validation"""
        try:
            exchange_info = self.client.get_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    return s
            return None
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return None
    
    def validate_order_params(self, symbol: str, side: str, order_type: str, 
                            quantity: float, price: float = None) -> bool:
        """Validate order parameters"""
        # Get symbol info
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            self.logger.error(f"Invalid symbol: {symbol}")
            return False
        
        # Validate side
        if side.upper() not in ['BUY', 'SELL']:
            self.logger.error(f"Invalid side: {side}")
            return False
        
        # Validate order type (Spot)
        valid_types = ['MARKET', 'LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']
        if order_type.upper() not in valid_types:
            self.logger.error(f"Invalid order type: {order_type}")
            return False
        
        # Validate quantity
        if quantity <= 0:
            self.logger.error(f"Invalid quantity: {quantity}")
            return False
        
        # Validate price for limit orders
        if order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'] and (price is None or price <= 0):
            self.logger.error(f"Price required for {order_type} orders")
            return False
        
        return True
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity according to LOT_SIZE step size"""
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            for f in symbol_info['filters']:
                if f.get('filterType') == 'LOT_SIZE':
                    step = Decimal(str(f['stepSize']))
                    # Quantize down to the nearest step
                    q = (Decimal(str(quantity)) // step) * step
                    # Normalize to string without scientific notation
                    return format(q.normalize(), 'f')
        return str(quantity)

    def format_price(self, symbol: str, price: float) -> str:
        """Format price according to PRICE_FILTER tick size"""
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            for f in symbol_info['filters']:
                if f.get('filterType') == 'PRICE_FILTER':
                    tick = Decimal(str(f['tickSize']))
                    p = (Decimal(str(price)) // tick) * tick
                    return format(p.normalize(), 'f')
        return str(price)
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            
        Returns:
            Dict: Order response
        """
        try:
            # Validate parameters
            if not self.validate_order_params(symbol, side, 'MARKET', quantity):
                raise ValueError("Invalid order parameters")
            
            # Format quantity
            formatted_quantity = self.format_quantity(symbol, quantity)
            
            # Log the order request
            self.logger.info(f"Placing MARKET order: {side} {formatted_quantity} {symbol}")
            
            # Place the order
            order = self.client.create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type='MARKET',
                quantity=formatted_quantity
            )
            
            # Persist and log
            try:
                save_order(order)
            except Exception:
                self.logger.warning("Failed to persist order to DB")
            self.logger.info(f"Market order placed successfully: {order['orderId']}")
            self.logger.debug(f"Order details: {json.dumps(order, indent=2)}")
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': order['origQty'],
                'status': order['status'],
                'order_details': order
            }
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            price (float): Order price
            
        Returns:
            Dict: Order response
        """
        try:
            # Validate parameters
            if not self.validate_order_params(symbol, side, 'LIMIT', quantity, price):
                raise ValueError("Invalid order parameters")
            
            # Format quantity and price
            formatted_quantity = self.format_quantity(symbol, quantity)
            formatted_price = self.format_price(symbol, price)
            
            # Log the order request
            self.logger.info(f"Placing LIMIT order: {side} {formatted_quantity} {symbol} at ${formatted_price}")
            
            # Place the order
            order = self.client.create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type='LIMIT',
                timeInForce='GTC',
                quantity=formatted_quantity,
                price=str(formatted_price)
            )
            
            # Persist and log
            try:
                save_order(order)
            except Exception:
                self.logger.warning("Failed to persist order to DB")
            self.logger.info(f"Limit order placed successfully: {order['orderId']}")
            self.logger.debug(f"Order details: {json.dumps(order, indent=2)}")
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': order['origQty'],
                'price': order['price'],
                'status': order['status'],
                'order_details': order
            }
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float, 
                             price: float, stop_price: float) -> Dict[str, Any]:
        """
        Place a stop-limit order (Bonus feature)
        
        Args:
            symbol (str): Trading pair
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            price (float): Limit price
            stop_price (float): Stop price
            
        Returns:
            Dict: Order response
        """
        try:
            # Validate parameters
            if not self.validate_order_params(symbol, side, 'STOP_LOSS_LIMIT', quantity, price):
                raise ValueError("Invalid order parameters")
            
            if stop_price <= 0:
                raise ValueError("Invalid stop price")
            
            # Format quantity
            formatted_quantity = self.format_quantity(symbol, quantity)
            formatted_price = self.format_price(symbol, price)
            formatted_stop = self.format_price(symbol, stop_price)
            
            # Log the order request
            self.logger.info(f"Placing STOP_LIMIT order: {side} {formatted_quantity} {symbol} "
                           f"at ${formatted_price}, stop: ${formatted_stop}")
            
            # Place the order
            order = self.client.create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type='STOP_LOSS_LIMIT',
                timeInForce='GTC',
                quantity=formatted_quantity,
                price=str(formatted_price),
                stopPrice=str(formatted_stop)
            )
            
            # Persist and log
            try:
                save_order(order)
            except Exception:
                self.logger.warning("Failed to persist order to DB")
            self.logger.info(f"Stop-limit order placed successfully: {order['orderId']}")
            self.logger.debug(f"Order details: {json.dumps(order, indent=2)}")
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': order['origQty'],
                'price': order['price'],
                'stop_price': order.get('stopPrice'),
                'status': order['status'],
                'order_details': order
            }
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            self.logger.error(f"Error placing stop-limit order: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get order status"""
        try:
            order = self.client.get_order(symbol=symbol.upper(), orderId=order_id)
            self.logger.info(f"Retrieved order status for {order_id}: {order.get('status')}")
            return {'success': True, 'order': order}
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            return {'success': False, 'error': str(e)}
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            result = self.client.cancel_order(symbol=symbol.upper(), orderId=order_id)
            self.logger.info(f"Order {order_id} cancelled successfully")
            return {'success': True, 'result': result}
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        try:
            account = self.client.get_account()
            # Spot account fields differ; compute available and totals from balances
            usdt = next((b for b in account.get('balances', []) if b.get('asset') == 'USDT'), None)
            free = usdt and usdt.get('free') or '0'
            locked = usdt and usdt.get('locked') or '0'
            balance_info = {
                'total_wallet_balance': str(float(free) + float(locked)),
                'total_unrealized_pnl': '0',  # Not applicable for spot
                'total_margin_balance': '0',   # Not applicable for spot
                'available_balance': free
            }
            self.logger.info(f"Retrieved account balance")
            return {'success': True, 'balance': balance_info}
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Binance Spot Trading Bot')
    parser.add_argument('--api-key', help='Binance API Key (or set BINANCE_API_KEY)')
    parser.add_argument('--api-secret', help='Binance API Secret (or set BINANCE_API_SECRET)')
    parser.add_argument('--testnet', action='store_true', default=True, help='Use testnet (default)')
    
    args = parser.parse_args()
    
    # Load .env if present
    load_dotenv()
    
    # Resolve API credentials from args or environment
    api_key = args.api_key or os.getenv('BINANCE_API_KEY')
    api_secret = args.api_secret or os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ Missing API credentials. Provide --api-key/--api-secret or set BINANCE_API_KEY/BINANCE_API_SECRET env vars.")
        return
    
    # Initialize bot
    try:
        bot = TradingBot(api_key, api_secret, args.testnet)
        # Initialize local storage
        init_db()

        # Instantiate helpers
        oco = OCOManager(bot.client, bot.logger)
        twap = TWAPExecutor(bot.client, bot.logger)
        grid = GridTrader(bot.client, bot.logger)
        price_feed = None
        ws_symbols: List[str] = ["BTCUSDT", "ETHUSDT"]
        strategy = SMACrossover()
        risk = RiskManager()
        api_thread = None
        api_services = None

        print("🚀 Trading Bot initialized successfully!")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        return
    
    # Interactive CLI
    while True:
        print("\n📊 Trading Bot Menu:")
        print("1. Place Market Order")
        print("2. Place Limit Order")
        print("3. Place Stop-Limit Order")
        print("4. Check Order Status")
        print("5. Cancel Order")
        print("6. Check Account Balance")
        print("7. Exit")
        print("8. OCO: Attach TP/SL (native if available, else client-side)")
        print("9. TWAP: Execute over time")
        print("10. Grid: Build grid around price")
        print("11. WS: Start live prices (BTCUSDT, ETHUSDT)")
        print("12. WS: Show latest prices")
        print("13. API: Start Flask on :5000")
        print("14. Backtest: SMA crossover (BTCUSDT)")
        
        choice = input("\nSelect an option (1-14): ").strip()
        
        try:
            if choice == '1':
                # Market Order
                symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
                side = input("Enter side (BUY/SELL): ").strip().upper()
                quantity = float(input("Enter quantity: ").strip())
                
                result = bot.place_market_order(symbol, side, quantity)
                if result['success']:
                    print(f"✅ Market order placed successfully!")
                    print(f"Order ID: {result['order_id']}")
                    print(f"Status: {result['status']}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '2':
                # Limit Order
                symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
                side = input("Enter side (BUY/SELL): ").strip().upper()
                quantity = float(input("Enter quantity: ").strip())
                price = float(input("Enter price: ").strip())
                
                result = bot.place_limit_order(symbol, side, quantity, price)
                if result['success']:
                    print(f"✅ Limit order placed successfully!")
                    print(f"Order ID: {result['order_id']}")
                    print(f"Status: {result['status']}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '3':
                # Stop-Limit Order
                symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
                side = input("Enter side (BUY/SELL): ").strip().upper()
                quantity = float(input("Enter quantity: ").strip())
                price = float(input("Enter limit price: ").strip())
                stop_price = float(input("Enter stop price: ").strip())
                
                result = bot.place_stop_limit_order(symbol, side, quantity, price, stop_price)
                if result['success']:
                    print(f"✅ Stop-limit order placed successfully!")
                    print(f"Order ID: {result['order_id']}")
                    print(f"Status: {result['status']}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '4':
                # Check Order Status
                symbol = input("Enter symbol: ").strip().upper()
                order_id = int(input("Enter order ID: ").strip())
                
                result = bot.get_order_status(symbol, order_id)
                if result['success']:
                    order = result['order']
                    print(f"✅ Order Status:")
                    print(f"Order ID: {order['orderId']}")
                    print(f"Symbol: {order['symbol']}")
                    print(f"Side: {order['side']}")
                    print(f"Status: {order['status']}")
                    print(f"Executed Qty: {order['executedQty']}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '5':
                # Cancel Order
                symbol = input("Enter symbol: ").strip().upper()
                order_id = int(input("Enter order ID: ").strip())
                
                result = bot.cancel_order(symbol, order_id)
                if result['success']:
                    print(f"✅ Order cancelled successfully!")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '6':
                # Check Balance
                result = bot.get_account_balance()
                if result['success']:
                    balance = result['balance']
                    print(f"✅ Account Balance:")
                    print(f"Total Wallet Balance: {balance['total_wallet_balance']} USDT")
                    print(f"Available Balance: {balance['available_balance']} USDT")
                    print(f"Total Unrealized PnL: {balance['total_unrealized_pnl']} USDT")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == '7':
                print("👋 Goodbye!")
                break

            elif choice == '8':
                # OCO submit
                symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
                side = input("Entry side (BUY/SELL) to hedge (will place opposite exits): ").strip().upper()
                qty = input("Quantity (formatted, e.g., 0.001): ").strip()
                tp = input("Take-profit price: ").strip()
                sl = input("Stop-loss price: ").strip()
                res = oco.submit(symbol, side, qty, tp, sl)
                if res.get('success'): print("✅ OCO submitted (client-side TP/SL)")
                else: print(f"❌ Error: {res.get('error')}")

            elif choice == '9':
                # TWAP
                symbol = input("Enter symbol: ").strip().upper()
                side = input("BUY/SELL: ").strip().upper()
                total_qty = float(input("Total quantity: ").strip())
                duration = int(input("Duration seconds: ").strip())
                slices = int(input("Number of slices: ").strip())
                res = twap.execute(symbol, side, total_qty, duration, slices)
                if res.get('success'): print("✅ TWAP completed")
                else: print(f"❌ Error: {res.get('error')}")

            elif choice == '10':
                # Grid
                symbol = input("Enter symbol: ").strip().upper()
                base_price = float(input("Base price: ").strip())
                levels = int(input("Levels: ").strip())
                step_pct = float(input("Step percent (e.g., 0.005 for 0.5%): ").strip())
                qty = input("Quantity per order (formatted): ").strip()
                side = input("Grid side (BUY places below, SELL places above): ").strip().upper()
                res = grid.build_grid(symbol, base_price, levels, step_pct, qty, side)
                if res.get('success'): print(f"✅ Grid orders placed: {len(res.get('orders', []))}")
                else: print(f"❌ Error: {res.get('error')}")

            elif choice == '11':
                # Start WebSocket
                if price_feed is None:
                    price_feed = PriceFeed(api_key, api_secret, args.testnet, bot.logger)
                    price_feed.start(ws_symbols)
                    print("✅ WebSocket started for:", ", ".join(ws_symbols))
                else:
                    print("ℹ️ WebSocket already running.")

            elif choice == '12':
                # Show latest prices
                if price_feed is None:
                    print("❌ WebSocket not started. Choose option 11 first.")
                else:
                    for s in ws_symbols:
                        print(f"{s}: {price_feed.get_price(s)}")

            elif choice == '13':
                # Start Flask API
                if api_thread is None:
                    api_services = Services(price_feed=price_feed)
                    app = create_app(api_services)
                    def run_api():
                        app.run(host='0.0.0.0', port=5000, debug=False)
                    api_thread = threading.Thread(target=run_api, daemon=True)
                    api_thread.start()
                    print("✅ API server started at http://localhost:5000")
                else:
                    print("ℹ️ API already running.")

            elif choice == '14':
                # Backtest SMA crossover
                symbol = input("Symbol for backtest (default BTCUSDT): ").strip().upper() or 'BTCUSDT'
                interval = Client.KLINE_INTERVAL_1MINUTE
                limit = 500
                fetcher = DataFetcher(bot.client)
                bars = fetcher.klines(symbol, interval=interval, limit=limit)
                bt = Backtester(strategy)
                res = bt.run(symbol, bars)
                print(f"✅ Backtest finished. Trades: {len(res['trades'])}")

            else:
                print("❌ Invalid choice. Please select 1-14.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()