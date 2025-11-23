"""
Order Manager
Handles order placement, modification, cancellation, and position management via MT5 Flask API
"""

import asyncio
from typing import Dict, List, Optional
import logging
from datetime import datetime
import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# MT5 Flask API configuration
MT5_API_BASE_URL = "http://mt5:5001"  # Internal Docker network

class OrderManager:
    """Manages trading orders and positions"""

    ORDER_TYPE_MAP = {
        'buy': getattr(mt5, 'ORDER_TYPE_BUY', 0),
        'sell': getattr(mt5, 'ORDER_TYPE_SELL', 1),
        'buylimit': getattr(mt5, 'ORDER_TYPE_BUY_LIMIT', 2),
        'selllimit': getattr(mt5, 'ORDER_TYPE_SELL_LIMIT', 3),
        'buystop': getattr(mt5, 'ORDER_TYPE_BUY_STOP', 4),
        'sellstop': getattr(mt5, 'ORDER_TYPE_SELL_STOP', 5)
    }

    def __init__(self):
        self.active_orders = {}

    async def initialize(self):
        """Initialize the order manager"""
        logger.info("Initializing Order Manager")
        logger.info("Order Manager initialized successfully")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Order Manager")
        self.active_orders.clear()

    def create_mt5_order_request(self, order_data: Dict) -> Dict:
        """Create MT5 order request from order data"""
        order_type = order_data.get('order_type', 'buy').lower()

        request = {
            "action": getattr(mt5, 'TRADE_ACTION_DEAL', 1),
            "symbol": order_data['symbol'],
            "volume": order_data['volume'],
            "type": self.ORDER_TYPE_MAP.get(order_type, getattr(mt5, 'ORDER_TYPE_BUY', 0)),
            "price": order_data.get('price'),
            "sl": order_data.get('stop_loss'),
            "tp": order_data.get('take_profit'),
            "deviation": 10,  # Allow 10 points deviation
            "magic": 123456,  # Magic number for order identification
            "comment": "TrainFlow AI Trade",
            "type_time": getattr(mt5, 'ORDER_TIME_GTC', 0),  # Good till cancelled
            "type_filling": getattr(mt5, 'ORDER_FILLING_IOC', 1),  # Immediate or cancel
        }

        # Remove None values
        request = {k: v for k, v in request.items() if v is not None}

        return request

    async def execute_trade(self, user_id: str, order_request: Dict) -> Dict:
        """Execute a trade via MT5 Flask API"""
        try:
            logger.info(f"Executing trade for user {user_id}: {order_request}")

            # Convert our internal format to Flask API format
            api_order_data = {
                'symbol': order_request['symbol'],
                'volume': order_request['volume'],
                'type': 'BUY' if order_request.get('type') == 0 else 'SELL',  # MT5 constants
                'deviation': order_request.get('deviation', 20),
                'magic': order_request.get('magic', 123456),
                'comment': order_request.get('comment', 'TrainFlow AI Trade')
            }

            # Add optional SL/TP
            if 'sl' in order_request and order_request['sl']:
                api_order_data['sl'] = order_request['sl']
            if 'tp' in order_request and order_request['tp']:
                api_order_data['tp'] = order_request['tp']

            # Send order via Flask API
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(f"{MT5_API_BASE_URL}/order", json=api_order_data, timeout=30) as response:
                        response_data = await response.json()

                        if response.status == 200:
                            # Store order details
                            order_info = {
                                'ticket': response_data.get('result', {}).get('order'),
                                'user_id': user_id,
                                'symbol': order_request['symbol'],
                                'type': order_request['type'],
                                'volume': order_request['volume'],
                                'price': response_data.get('result', {}).get('price'),
                                'status': 'filled',
                                'timestamp': datetime.now().isoformat()
                            }

                            ticket = response_data.get('result', {}).get('order')
                            if ticket:
                                self.active_orders[ticket] = order_info

                            logger.info(f"Trade executed successfully: {ticket}")
                            return {
                                'success': True,
                                'order_id': ticket,
                                'price': response_data.get('result', {}).get('price'),
                                'message': 'Trade executed successfully'
                            }
                        else:
                            error_msg = response_data.get('error', f'HTTP {response.status}')
                            logger.error(f"Trade failed: {error_msg}")
                            return {
                                'success': False,
                                'error': error_msg
                            }

                except asyncio.TimeoutError:
                    return {
                        'success': False,
                        'error': 'MT5 API request timeout'
                    }
                except Exception as e:
                    logger.error(f"MT5 API request error: {e}")
                    return {
                        'success': False,
                        'error': f'MT5 API error: {str(e)}'
                    }

        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def cancel_order(self, user_id: str, order_id: int) -> Dict:
        """Cancel a pending order"""
        try:
            logger.info(f"Cancelling order {order_id} for user {user_id}")

            # Get order info
            order = mt5.orders_get(ticket=order_id)
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found'
                }

            order = order[0]

            # Create cancel request
            cancel_request = {
                "action": getattr(mt5, 'TRADE_ACTION_REMOVE', 3),
                "order": order_id,
                "symbol": order.symbol
            }

            result = mt5.order_send(cancel_request)

            if result.retcode == getattr(mt5, 'TRADE_RETCODE_DONE', 10009):
                # Remove from active orders
                if order_id in self.active_orders:
                    del self.active_orders[order_id]

                logger.info(f"Order {order_id} cancelled successfully")
                return {
                    'success': True,
                    'message': 'Order cancelled successfully'
                }
            else:
                error_msg = f"Order cancellation failed: {result.comment}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_positions(self, user_id: str) -> List[Dict]:
        """Get all open positions via MT5 Flask API"""
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{MT5_API_BASE_URL}/position", timeout=10) as response:
                        if response.status == 200:
                            positions_data = await response.json()
                            # Assuming the API returns positions in a list
                            return positions_data.get('positions', [])
                        else:
                            logger.error(f"Failed to get positions: HTTP {response.status}")
                            return []
                except asyncio.TimeoutError:
                    logger.error("Positions request timeout")
                    return []
                except Exception as e:
                    logger.error(f"Positions API request error: {e}")
                    return []

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def close_position(self, user_id: str, ticket: int, volume: float = None) -> Dict:
        """Close a position"""
        try:
            logger.info(f"Closing position {ticket} for user {user_id}")

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return {
                    'success': False,
                    'error': 'Position not found'
                }

            position = position[0]
            close_volume = volume or position.volume

            # Create close request
            close_request = {
                "action": getattr(mt5, 'TRADE_ACTION_DEAL', 1),
                "symbol": position.symbol,
                "volume": close_volume,
                "type": getattr(mt5, 'ORDER_TYPE_SELL', 1) if position.type == getattr(mt5, 'POSITION_TYPE_BUY', 0) else getattr(mt5, 'ORDER_TYPE_BUY', 0),
                "position": ticket,
                "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 10,
                "magic": 123456,
                "comment": "Position Close"
            }

            result = mt5.order_send(close_request)

            if result.retcode == getattr(mt5, 'TRADE_RETCODE_DONE', 10009):
                logger.info(f"Position {ticket} closed successfully")
                return {
                    'success': True,
                    'close_price': result.price,
                    'profit': position.profit,
                    'message': 'Position closed successfully'
                }
            else:
                error_msg = f"Position close failed: {result.comment}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            logger.error(f"Position close error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_order_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get order history"""
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()

            history = mt5.history_orders_get(from_date, to_date)

            if not history:
                return []

            orders = []
            for order in history:
                orders.append({
                    'ticket': order.ticket,
                    'time_setup': order.time_setup,
                    'time_done': order.time_done,
                    'symbol': order.symbol,
                    'type': order.type,
                    'state': order.state,
                    'volume_initial': float(order.volume_initial),
                    'volume_current': float(order.volume_current),
                    'price_open': float(order.price_open),
                    'price_current': float(order.price_current),
                    'sl': float(order.sl) if order.sl else None,
                    'tp': float(order.tp) if order.tp else None,
                    'profit': float(order.profit) if order.profit else 0
                })

            return orders

        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []

    async def modify_position(self, user_id: str, ticket: int, sl: float = None, tp: float = None) -> Dict:
        """Modify position stop loss and take profit"""
        try:
            logger.info(f"Modifying position {ticket} for user {user_id}")

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return {
                    'success': False,
                    'error': 'Position not found'
                }

            position = position[0]

            # Create modify request
            modify_request = {
                "action": getattr(mt5, 'TRADE_ACTION_SLTP', 6),
                "symbol": position.symbol,
                "position": ticket,
                "sl": sl if sl is not None else position.sl,
                "tp": tp if tp is not None else position.tp
            }

            result = mt5.order_send(modify_request)

            if result.retcode == getattr(mt5, 'TRADE_RETCODE_DONE', 10009):
                logger.info(f"Position {ticket} modified successfully")
                return {
                    'success': True,
                    'message': 'Position modified successfully'
                }
            else:
                error_msg = f"Position modification failed: {result.comment}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            logger.error(f"Position modification error: {e}")
            return {
                'success': False,
                'error': str(e)
            }