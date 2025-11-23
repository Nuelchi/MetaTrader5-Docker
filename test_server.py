#!/usr/bin/env python3
"""
MT5 Server Test Script
Tests all components of the MT5 server setup
"""

import asyncio
import json
import sys
import time
from datetime import datetime
import requests
import websockets
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, '.')

try:
    from config import settings
    from auth import jwt_verifier
    from mt5_account_manager import MT5AccountManager
    from market_data_service import MarketDataService
    from order_manager import OrderManager
    from health_monitor import HealthMonitor
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required modules are available")
    sys.exit(1)

class MT5ServerTester:
    """Comprehensive test suite for MT5 server"""

    def __init__(self):
        self.results = []
        self.api_base = f"http://localhost:{settings.API_PORT}"
        self.ws_url = f"ws://localhost:{settings.WS_PORT}"

    def log_test(self, test_name: str, success: bool, message: str = "", details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            result["details"] = details

        self.results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")

    async def test_mt5_initialization(self):
        """Test MT5 initialization"""
        try:
            import MetaTrader5 as mt5

            if not mt5.initialize():
                self.log_test("MT5 Initialization", False, "MT5 initialization failed")
                return False

            terminal_info = mt5.terminal_info()
            if not terminal_info:
                self.log_test("MT5 Terminal Info", False, "Could not get terminal info")
                return False

            self.log_test("MT5 Initialization", True, "MT5 initialized successfully", {
                "terminal_name": terminal_info.name,
                "connected": terminal_info.connected
            })
            return True

        except Exception as e:
            self.log_test("MT5 Initialization", False, f"Exception: {e}")
            return False

    async def test_services_initialization(self):
        """Test service initialization"""
        try:
            account_manager = MT5AccountManager()
            market_service = MarketDataService()
            order_manager = OrderManager()
            health_monitor = HealthMonitor()

            await account_manager.initialize()
            await market_service.initialize()
            await order_manager.initialize()
            await health_monitor.initialize()

            self.log_test("Services Initialization", True, "All services initialized successfully")

            # Cleanup
            await account_manager.cleanup()
            await market_service.cleanup()
            await order_manager.cleanup()
            await health_monitor.cleanup()

            return True

        except Exception as e:
            self.log_test("Services Initialization", False, f"Service initialization failed: {e}")
            return False

    async def test_supabase_auth(self):
        """Test Supabase authentication"""
        try:
            # Test with invalid token (should fail)
            invalid_token = "invalid.jwt.token"
            result = auth_verifier.verify_jwt_token(invalid_token)

            if result:
                self.log_test("Supabase Auth", False, "Should reject invalid tokens")
                return False

            # Test user extraction with invalid token
            user = auth_verifier.get_user_from_token(invalid_token)
            if user:
                self.log_test("Supabase User Extraction", False, "Should not extract user from invalid token")
                return False

            self.log_test("Supabase Auth", True, "Supabase authentication correctly rejects invalid tokens")
            return True

        except Exception as e:
            self.log_test("Supabase Auth", False, f"Supabase auth test failed: {e}")
            return False

    async def test_market_data_service(self):
        """Test market data service"""
        try:
            service = MarketDataService()
            await service.initialize()

            # Test symbol list
            symbols = await service.get_available_symbols()
            if not symbols:
                self.log_test("Market Data Symbols", False, "No symbols available")
                return False

            self.log_test("Market Data Symbols", True, f"Retrieved {len(symbols)} symbols")

            # Test real-time data for EURUSD
            if 'EURUSD' in symbols:
                data = await service.get_real_time_data('EURUSD')
                if data:
                    self.log_test("Real-time Data", True, f"EURUSD data: {data['bid']}/{data['ask']}")
                else:
                    self.log_test("Real-time Data", False, "Could not get EURUSD data")
            else:
                self.log_test("Real-time Data", False, "EURUSD not in available symbols")

            # Test historical data
            historical = await service.get_historical_data('EURUSD', 'H1', 10)
            if historical and len(historical) > 0:
                self.log_test("Historical Data", True, f"Retrieved {len(historical)} bars")
            else:
                self.log_test("Historical Data", False, "Could not get historical data")

            await service.cleanup()
            return True

        except Exception as e:
            self.log_test("Market Data Service", False, f"Market data test failed: {e}")
            return False

    async def test_health_monitor(self):
        """Test health monitoring"""
        try:
            monitor = HealthMonitor()
            await monitor.initialize()

            health = await monitor.check_health()

            if health['status'] in ['healthy', 'degraded']:
                self.log_test("Health Monitor", True, f"Health status: {health['status']}", {
                    "uptime": health.get('uptime_seconds', 0),
                    "services": health.get('services', {}),
                    "system": health.get('system', {})
                })
                success = True
            else:
                self.log_test("Health Monitor", False, f"Health check failed: {health}")
                success = False

            await monitor.cleanup()
            return success

        except Exception as e:
            self.log_test("Health Monitor", False, f"Health monitor test failed: {e}")
            return False

    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            # Test basic connection (will fail without proper auth, but tests connectivity)
            async with websockets.connect(self.ws_url) as websocket:
                # Send ping
                await websocket.send(json.dumps({"type": "ping"}))
                response = await websocket.recv()
                data = json.loads(response)

                if data.get('type') == 'pong':
                    self.log_test("WebSocket Connection", True, "WebSocket ping/pong works")
                    return True
                else:
                    self.log_test("WebSocket Connection", False, f"Unexpected response: {data}")
                    return False

        except Exception as e:
            self.log_test("WebSocket Connection", False, f"WebSocket test failed: {e}")
            return False

    def test_configuration(self):
        """Test configuration loading"""
        try:
            # Test required settings
            required_settings = [
                'MT5_ENCRYPTION_KEY',
                'API_PORT',
                'WS_PORT'
            ]

            missing = []
            for setting in required_settings:
                if not hasattr(settings, setting.lower()) or not getattr(settings, setting.lower()):
                    missing.append(setting)

            if missing:
                self.log_test("Configuration", False, f"Missing required settings: {missing}")
                return False

            self.log_test("Configuration", True, "All required settings present")
            return True

        except Exception as e:
            self.log_test("Configuration", False, f"Configuration test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting MT5 Server Test Suite")
        print("=" * 50)

        # Configuration test (doesn't need async)
        self.test_configuration()

        # Async tests
        tests = [
            ("MT5 Initialization", self.test_mt5_initialization),
            ("Services Initialization", self.test_services_initialization),
            ("Supabase Authentication", self.test_supabase_auth),
            ("Market Data Service", self.test_market_data_service),
            ("Health Monitor", self.test_health_monitor),
            ("WebSocket Connection", self.test_websocket_connection),
        ]

        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                await test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Test execution failed: {e}")

        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")

        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")

        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed. Check details above.")
            # Print failed tests
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")

            return False

async def main():
    """Main test function"""
    tester = MT5ServerTester()
    success = await tester.run_all_tests()

    # Save results to file
    with open('test_results.json', 'w') as f:
        json.dump(tester.results, f, indent=2)

    print(f"\n📄 Detailed results saved to test_results.json")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())