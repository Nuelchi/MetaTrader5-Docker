"""
MT5 Account Manager
Handles MT5 account connections, monitoring, and credential management
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime
import json
import logging
from cryptography.fernet import Fernet

from config import settings

logger = logging.getLogger(__name__)

# Optional MT5 import for testing without MT5
try:
    # Try mt5linux first (Linux-compatible)
    import mt5linux as mt5
    logger.info("✅ mt5linux library loaded in account manager")
except ImportError:
    try:
        # Fallback to MetaTrader5 (Windows)
        import MetaTrader5 as mt5
        logger.info("✅ MetaTrader5 library loaded in account manager")
    except ImportError:
        mt5 = None
        logger.warning("⚠️  No MT5 library available in account manager - running in simulation mode")

class MT5AccountManager:
    """Manages MT5 account connections and monitoring"""

    def __init__(self):
        self.active_connections: Dict[str, Dict] = {}  # user_id -> connection_info
        self.cipher = Fernet(settings.mt5_encryption_key.encode())
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize the account manager"""
        logger.info("Initializing MT5 Account Manager")
        # Initialize MT5 if not already done
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")
        logger.info("MT5 Account Manager initialized successfully")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up MT5 Account Manager")
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        self.monitoring_tasks.clear()
        logger.info("MT5 Account Manager cleaned up")

    def encrypt_credentials(self, credentials: Dict) -> str:
        """Encrypt MT5 credentials for storage"""
        data = json.dumps(credentials).encode()
        return self.cipher.encrypt(data).decode()

    def decrypt_credentials(self, encrypted_data: str) -> Dict:
        """Decrypt MT5 credentials"""
        data = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(data.decode())

    async def connect_mt5_account(self, user_id: str, credentials: Dict) -> Dict:
        """Connect to MT5 account and maintain persistent connection"""
        try:
            logger.info(f"Connecting MT5 account for user {user_id}")

            # Login to account
            login_result = mt5.login(
                login=credentials['login'],
                password=credentials['password'],
                server=credentials['server']
            )

            if not login_result:
                error = mt5.last_error()
                logger.error(f"MT5 login failed for user {user_id}: {error}")
                return {
                    'success': False,
                    'error': f'MT5 login failed: {error}'
                }

            # Get account info
            account_info = mt5.account_info()
            if not account_info:
                logger.error(f"Failed to get account info for user {user_id}")
                return {
                    'success': False,
                    'error': 'Failed to get account info'
                }

            # Store encrypted credentials and connection info
            connection_info = {
                'login': credentials['login'],
                'server': credentials['server'],
                'encrypted_credentials': self.encrypt_credentials(credentials),
                'connected_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'account_info': {
                    'balance': float(account_info.balance),
                    'equity': float(account_info.equity),
                    'margin': float(account_info.margin),
                    'margin_free': float(account_info.margin_free),
                    'profit': float(account_info.profit),
                    'leverage': account_info.leverage,
                    'currency': account_info.currency
                }
            }

            self.active_connections[user_id] = connection_info

            # Start background monitoring task
            if user_id in self.monitoring_tasks:
                self.monitoring_tasks[user_id].cancel()

            self.monitoring_tasks[user_id] = asyncio.create_task(
                self.monitor_account(user_id)
            )

            logger.info(f"MT5 connection successful for user {user_id}")
            return {
                'success': True,
                'account_info': connection_info['account_info'],
                'message': f'Connected to MT5 account {credentials["login"]}'
            }

        except Exception as e:
            logger.error(f"MT5 connection error for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def monitor_account(self, user_id: str):
        """Monitor account status and maintain connection"""
        logger.info(f"Starting account monitoring for user {user_id}")

        while user_id in self.active_connections:
            try:
                # Check if still connected and get fresh account info
                account_info = mt5.account_info()
                if account_info:
                    # Update connection info
                    connection_info = self.active_connections[user_id]
                    connection_info['last_updated'] = datetime.now().isoformat()
                    connection_info['account_info'] = {
                        'balance': float(account_info.balance),
                        'equity': float(account_info.equity),
                        'margin': float(account_info.margin),
                        'margin_free': float(account_info.margin_free),
                        'profit': float(account_info.profit),
                        'leverage': account_info.leverage,
                        'currency': account_info.currency
                    }

                    # Check risk limits
                    await self.check_risk_limits(user_id, connection_info)

                else:
                    # Try to reconnect
                    logger.warning(f"Lost MT5 connection for user {user_id}, attempting reconnect")
                    await self.reconnect_account(user_id)

                await asyncio.sleep(settings.health_check_interval)

            except asyncio.CancelledError:
                logger.info(f"Account monitoring cancelled for user {user_id}")
                break
            except Exception as e:
                logger.error(f"Account monitoring error for user {user_id}: {e}")
                await asyncio.sleep(60)  # Wait longer on error

        logger.info(f"Stopped account monitoring for user {user_id}")

    async def reconnect_account(self, user_id: str) -> bool:
        """Attempt to reconnect MT5 account"""
        try:
            if user_id not in self.active_connections:
                return False

            connection_info = self.active_connections[user_id]
            credentials = self.decrypt_credentials(connection_info['encrypted_credentials'])

            login_result = mt5.login(
                login=credentials['login'],
                password=credentials['password'],
                server=credentials['server']
            )

            if login_result:
                logger.info(f"Successfully reconnected MT5 account for user {user_id}")
                return True
            else:
                logger.error(f"Failed to reconnect MT5 account for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Reconnection error for user {user_id}: {e}")
            return False

    async def check_risk_limits(self, user_id: str, connection_info: Dict):
        """Check and enforce risk management limits"""
        account_info = connection_info['account_info']

        # Check daily loss limit
        if account_info['profit'] < -(account_info['balance'] * settings.max_daily_loss_pct):
            logger.warning(f"Daily loss limit reached for user {user_id}")
            # Could implement auto-stop or notification here

        # Check margin usage
        margin_usage = account_info['margin'] / account_info['equity'] if account_info['equity'] > 0 else 1
        if margin_usage > 0.8:  # 80% margin usage
            logger.warning(f"High margin usage for user {user_id}: {margin_usage:.2%}")

    async def disconnect_mt5_account(self, user_id: str) -> Dict:
        """Disconnect MT5 account"""
        try:
            logger.info(f"Disconnecting MT5 account for user {user_id}")

            if user_id in self.active_connections:
                # Cancel monitoring task
                if user_id in self.monitoring_tasks:
                    self.monitoring_tasks[user_id].cancel()
                    del self.monitoring_tasks[user_id]

                # Remove connection info
                del self.active_connections[user_id]

                return {
                    'success': True,
                    'message': 'MT5 account disconnected'
                }
            else:
                return {
                    'success': False,
                    'error': 'No active connection found'
                }

        except Exception as e:
            logger.error(f"MT5 disconnection error for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_account_status(self, user_id: str) -> Optional[Dict]:
        """Get current account status"""
        if user_id not in self.active_connections:
            return None

        connection_info = self.active_connections[user_id]

        # Get fresh account info
        account_info = mt5.account_info()
        if account_info:
            connection_info['account_info'] = {
                'balance': float(account_info.balance),
                'equity': float(account_info.equity),
                'margin': float(account_info.margin),
                'margin_free': float(account_info.margin_free),
                'profit': float(account_info.profit),
                'leverage': account_info.leverage,
                'currency': account_info.currency
            }

        return {
            'connected': True,
            'account_info': connection_info['account_info'],
            'connected_at': connection_info['connected_at'],
            'last_updated': connection_info['last_updated']
        }

    async def get_account_info(self, user_id: str) -> Optional[Dict]:
        """Get detailed account information"""
        if user_id not in self.active_connections:
            return None

        account_info = mt5.account_info()
        if not account_info:
            return None

        return {
            'login': account_info.login,
            'name': account_info.name,
            'server': account_info.server,
            'currency': account_info.currency,
            'balance': float(account_info.balance),
            'equity': float(account_info.equity),
            'margin': float(account_info.margin),
            'margin_free': float(account_info.margin_free),
            'margin_level': float(account_info.margin_level) if account_info.margin_level else 0,
            'profit': float(account_info.profit),
            'leverage': account_info.leverage,
            'trade_allowed': account_info.trade_allowed,
            'trade_expert': account_info.trade_expert
        }

    def get_active_connections_count(self) -> int:
        """Get count of active connections"""
        return len(self.active_connections)

    def get_connection_summary(self) -> List[Dict]:
        """Get summary of all active connections"""
        return [
            {
                'user_id': user_id,
                'login': info['login'],
                'server': info['server'],
                'connected_at': info['connected_at'],
                'balance': info['account_info']['balance']
            }
            for user_id, info in self.active_connections.items()
        ]