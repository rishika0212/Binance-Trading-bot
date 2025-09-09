#!/usr/bin/env python3
"""
Test script for the Binance Trading Bot
This script helps verify that your bot is working correctly
"""

from trading_bot import TradingBot
import os
import time

def test_bot_functionality():
    """Test basic bot functionality"""
    
    print("🧪 Testing Trading Bot Functionality")
    print("=" * 50)
    
    # Get API credentials (replace with your testnet credentials)
    api_key = input("Enter your Binance Testnet API Key: ").strip()
    api_secret = input("Enter your Binance Testnet API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("❌ API credentials are required!")
        return False
    
    try:
        # Initialize bot
        print("\n1️⃣ Initializing bot...")
        bot = TradingBot(api_key, api_secret, testnet=True)
        print("✅ Bot initialized successfully!")
        
        # Test connection
        print("\n2️⃣ Testing API connection...")
        if bot.test_connection():
            print("✅ API connection successful!")
        else:
            print("❌ API connection failed!")
            return False
        
        # Test account balance
        print("\n3️⃣ Testing account balance retrieval...")
        balance_result = bot.get_account_balance()
        if balance_result['success']:
            print("✅ Account balance retrieved successfully!")
            balance = balance_result['balance']
            print(f"   Available Balance: {balance['available_balance']} USDT")
        else:
            print(f"❌ Failed to get balance: {balance_result['error']}")
            return False
        
        # Test symbol validation
        print("\n4️⃣ Testing symbol validation...")
        test_symbol = "BTCUSDT"
        symbol_info = bot.get_symbol_info(test_symbol)
        if symbol_info:
            print(f"✅ Symbol {test_symbol} is valid!")
        else:
            print(f"❌ Symbol {test_symbol} validation failed!")
            return False
        
        # Test order validation (without placing actual orders)
        print("\n5️⃣ Testing order parameter validation...")
        
        # Valid parameters
        if bot.validate_order_params("BTCUSDT", "BUY", "MARKET", 0.001):
            print("✅ Valid market order parameters accepted!")
        else:
            print("❌ Valid parameters rejected!")
            
        # Invalid parameters
        if not bot.validate_order_params("INVALID", "BUY", "MARKET", 0.001):
            print("✅ Invalid symbol correctly rejected!")
        else:
            print("❌ Invalid symbol was accepted!")
            
        if not bot.validate_order_params("BTCUSDT", "INVALID", "MARKET", 0.001):
            print("✅ Invalid side correctly rejected!")
        else:
            print("❌ Invalid side was accepted!")
        
        print("\n6️⃣ All basic tests passed! ✅")
        print("\n" + "=" * 50)
        print("🎉 Your trading bot is working correctly!")
        print("📝 Check 'trading_bot.log' for detailed logs")
        
        # Ask if user wants to test actual order placement
        test_orders = input("\nDo you want to test actual order placement? (y/N): ").strip().lower()
        
        if test_orders == 'y':
            print("\n🚨 WARNING: This will place actual orders on testnet!")
            confirm = input("Are you sure? Type 'YES' to confirm: ").strip()
            
            if confirm == 'YES':
                test_order_placement(bot)
            else:
                print("Order placement test skipped.")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_order_placement(bot):
    """Test actual order placement (optional)"""
    print("\n🔥 Testing Order Placement")
    print("=" * 30)
    
    try:
        # Test 1: Small market buy order
        print("\n📈 Test 1: Small Market Buy Order")
        symbol = "BTCUSDT"
        side = "BUY"
        quantity = 0.001  # Very small quantity for testing
        
        print(f"Placing market order: {side} {quantity} {symbol}")
        result = bot.place_market_order(symbol, side, quantity)
        
        if result['success']:
            print(f"✅ Market order successful! Order ID: {result['order_id']}")
            market_order_id = result['order_id']
            
            # Check order status
            time.sleep(2)  # Wait a bit
            status_result = bot.get_order_status(symbol, market_order_id)
            if status_result['success']:
                print(f"✅ Order status check successful: {status_result['order']['status']}")
            else:
                print(f"❌ Order status check failed: {status_result['error']}")
        else:
            print(f"❌ Market order failed: {result['error']}")
            return False
        
        # Test 2: Limit order (far from market price, will not execute immediately)
        print("\n📊 Test 2: Limit Order (Far from Market)")
        
        # Get current price first
        try:
            ticker = bot.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Place a buy limit order 20% below current price (won't execute)
            limit_price = current_price * 0.8
            
            print(f"Current price: ${current_price:.2f}")
            print(f"Placing limit order at: ${limit_price:.2f} (20% below market)")
            
            result = bot.place_limit_order(symbol, "BUY", quantity, limit_price)
            
            if result['success']:
                print(f"✅ Limit order placed! Order ID: {result['order_id']}")
                limit_order_id = result['order_id']
                
                # Wait a bit then cancel the order
                time.sleep(3)
                print("Cancelling limit order...")
                cancel_result = bot.cancel_order(symbol, limit_order_id)
                
                if cancel_result['success']:
                    print("✅ Limit order cancelled successfully!")
                else:
                    print(f"❌ Failed to cancel order: {cancel_result['error']}")
                    
            else:
                print(f"❌ Limit order failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ Limit order test failed: {e}")
        
        # Test 3: Stop-limit order (bonus feature)
        print("\n🛡️ Test 3: Stop-Limit Order")
        
        try:
            # Get current price
            ticker = bot.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Set stop-limit order parameters (sell order)
            stop_price = current_price * 0.95  # Stop at 5% below current
            limit_price = current_price * 0.94  # Limit at 6% below current
            
            print(f"Current price: ${current_price:.2f}")
            print(f"Stop price: ${stop_price:.2f}")
            print(f"Limit price: ${limit_price:.2f}")
            
            result = bot.place_stop_limit_order(symbol, "SELL", quantity, limit_price, stop_price)
            
            if result['success']:
                print(f"✅ Stop-limit order placed! Order ID: {result['order_id']}")
                stop_order_id = result['order_id']
                
                # Cancel the order after a short wait
                time.sleep(3)
                print("Cancelling stop-limit order...")
                cancel_result = bot.cancel_order(symbol, stop_order_id)
                
                if cancel_result['success']:
                    print("✅ Stop-limit order cancelled successfully!")
                else:
                    print(f"❌ Failed to cancel stop-limit order: {cancel_result['error']}")
                    
            else:
                print(f"❌ Stop-limit order failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ Stop-limit order test failed: {e}")
        
        print("\n🎊 Order placement tests completed!")
        print("📋 Check your Binance testnet account to verify orders")
        
    except Exception as e:
        print(f"❌ Order placement test failed: {e}")

def generate_sample_config():
    """Generate a sample configuration file"""
    config_content = """# Binance Trading Bot Configuration
# Copy this file to 'config.py' and fill in your credentials

# Binance Testnet API Credentials
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# Bot Settings
TESTNET = True
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_QUANTITY = 0.001

# Risk Management
MAX_POSITION_SIZE = 0.1
STOP_LOSS_PERCENTAGE = 0.05  # 5%
TAKE_PROFIT_PERCENTAGE = 0.10  # 10%

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "trading_bot.log"
"""
    
    try:
        with open("config_sample.py", "w") as f:
            f.write(config_content)
        print("✅ Sample configuration file created: config_sample.py")
    except Exception as e:
        print(f"❌ Failed to create config file: {e}")

def main():
    """Main test function"""
    print("🤖 Binance Trading Bot Test Suite")
    print("=" * 50)
    print("This script will test your trading bot setup")
    print("Make sure you have:")
    print("- Binance testnet account created")
    print("- API keys generated with futures trading permission")
    print("- python-binance library installed")
    print("=" * 50)
    
    # Ask what to test
    print("\nSelect test mode:")
    print("1. Full functionality test (recommended)")
    print("2. Generate sample config file")
    print("3. Quick connection test only")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        success = test_bot_functionality()
        if success:
            print("\n🎉 All tests passed! Your bot is ready for submission.")
        else:
            print("\n❌ Some tests failed. Please check the logs and fix issues.")
            
    elif choice == "2":
        generate_sample_config()
        print("\nEdit the config_sample.py file with your credentials,")
        print("then rename it to config.py")
        
    elif choice == "3":
        # Quick connection test
        api_key = input("Enter your Binance Testnet API Key: ").strip()
        api_secret = input("Enter your Binance Testnet API Secret: ").strip()
        
        try:
            bot = TradingBot(api_key, api_secret, testnet=True)
            if bot.test_connection():
                print("✅ Connection successful!")
            else:
                print("❌ Connection failed!")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()