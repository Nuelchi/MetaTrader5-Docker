"""
WebSocket Server
Handles real-time data streaming and client connections
"""

import asyncio
import json
import logging
from typing import Dict, Set, Callable, Optional
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

from auth import jwt_verifier
from market_data_service import MarketDataService
from config import settings

logger = logging.getLogger(__name__)

class MT5WebSocketServer:
    """WebSocket server for real-time MT5 data streaming"""

    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.market_data_service = MarketDataService()
        self.streaming_tasks: Dict[str, asyncio.Task] = {}
        self.mt5_initialized = False

    async def initialize(self):
        """Initialize the WebSocket server"""
        logger.info("Initializing WebSocket Server")
        await self.market_data_service.initialize()
        self.mt5_initialized = True
        logger.info("WebSocket Server initialized successfully")

    async def cleanup(self):
        """Cleanup WebSocket server resources"""
        logger.info("Cleaning up WebSocket Server")

        # Cancel all streaming tasks
        for task in self.streaming_tasks.values():
            task.cancel()
        self.streaming_tasks.clear()

        # Close all client connections
        for client_set in self.clients.values():
            for websocket in client_set:
                try:
                    await websocket.close()
                except:
                    pass
        self.clients.clear()

        await self.market_data_service.cleanup()
        logger.info("WebSocket Server cleaned up")

    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        client_id = None

        try:
            logger.info(f"New WebSocket connection from {websocket.remote_address}")

            # Authenticate client
            client_id = await self.authenticate_client(websocket)
            if not client_id:
                return

            # Register client
            if client_id not in self.clients:
                self.clients[client_id] = set()
            self.clients[client_id].add(websocket)

            logger.info(f"Client {client_id} authenticated and registered")

            # Handle client messages
            await self.handle_client_messages(websocket, client_id)

        except ConnectionClosedError:
            logger.info(f"WebSocket connection closed for client {client_id}")
        except WebSocketException as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error handling client {client_id}: {e}")
        finally:
            # Cleanup
            if client_id and client_id in self.clients:
                self.clients[client_id].discard(websocket)
                if not self.clients[client_id]:
                    del self.clients[client_id]

                    # Cancel streaming task if no more clients
                    if client_id in self.streaming_tasks:
                        self.streaming_tasks[client_id].cancel()
                        del self.streaming_tasks[client_id]

    async def authenticate_client(self, websocket: websockets.WebSocketServerProtocol) -> Optional[str]:
        """Authenticate WebSocket client"""
        try:
            # Wait for authentication message
            auth_message = await asyncio.wait_for(
                websocket.recv(),
                timeout=settings.ws_ping_timeout
            )

            auth_data = json.loads(auth_message)

            if auth_data.get('type') != 'auth':
                await self.send_error(websocket, "First message must be authentication")
                return None

            token = auth_data.get('token')
            if not token:
                await self.send_error(websocket, "Authentication token required")
                return None

            # Verify JWT token
            user = jwt_verifier.get_user_from_token(token)
            if not user:
                await self.send_error(websocket, "Invalid authentication token")
                return None

            # Send authentication success
            await websocket.send(json.dumps({
                'type': 'auth_success',
                'user_id': user['user_id'],
                'timestamp': datetime.now().isoformat()
            }))

            return user['user_id']

        except asyncio.TimeoutError:
            await self.send_error(websocket, "Authentication timeout")
            return None
        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON format")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self.send_error(websocket, "Authentication failed")
            return None

    async def handle_client_messages(self, websocket: websockets.WebSocketServerProtocol, client_id: str):
        """Handle messages from authenticated client"""
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get('type')

                if message_type == 'subscribe_market_data':
                    await self.handle_market_data_subscription(websocket, client_id, data)
                elif message_type == 'unsubscribe_market_data':
                    await self.handle_market_data_unsubscription(client_id, data)
                elif message_type == 'ping':
                    await websocket.send(json.dumps({'type': 'pong'}))
                else:
                    await self.send_error(websocket, f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                await self.send_error(websocket, "Invalid JSON format")
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await self.send_error(websocket, "Message processing error")

    async def handle_market_data_subscription(self, websocket, client_id: str, data: Dict):
        """Handle market data subscription request"""
        symbol = data.get('symbol')
        if not symbol:
            await self.send_error(websocket, "Symbol required for market data subscription")
            return

        logger.info(f"Client {client_id} subscribing to market data for {symbol}")

        # Start streaming if not already streaming for this client
        if client_id not in self.streaming_tasks:
            self.streaming_tasks[client_id] = asyncio.create_task(
                self.stream_market_data_to_client(client_id, symbol)
            )

        await websocket.send(json.dumps({
            'type': 'subscription_success',
            'symbol': symbol,
            'message': f'Subscribed to {symbol} market data'
        }))

    async def handle_market_data_unsubscription(self, client_id: str, data: Dict):
        """Handle market data unsubscription request"""
        symbol = data.get('symbol')
        logger.info(f"Client {client_id} unsubscribing from market data for {symbol}")

        # Note: In a full implementation, you'd track per-symbol subscriptions
        # For now, we keep streaming until client disconnects

    async def stream_market_data_to_client(self, client_id: str, symbol: str):
        """Stream market data to a specific client"""
        logger.info(f"Starting market data stream for client {client_id}, symbol {symbol}")

        last_tick = None

        try:
            while client_id in self.clients and self.clients[client_id]:
                # Get real-time data
                tick_data = await self.market_data_service.get_real_time_data(symbol)

                if tick_data and (last_tick is None or tick_data['timestamp'] != last_tick):
                    # Send to all client's connections
                    message = json.dumps({
                        'type': 'market_data',
                        'symbol': symbol,
                        'data': tick_data,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Send to all connections for this client
                    disconnected_clients = []
                    for websocket in self.clients[client_id]:
                        try:
                            await websocket.send(message)
                        except (ConnectionClosedError, WebSocketException):
                            disconnected_clients.append(websocket)

                    # Remove disconnected clients
                    for websocket in disconnected_clients:
                        self.clients[client_id].discard(websocket)

                    last_tick = tick_data['timestamp']

                await asyncio.sleep(settings.market_data_update_interval / 1000)

        except asyncio.CancelledError:
            logger.info(f"Market data streaming cancelled for client {client_id}")
        except Exception as e:
            logger.error(f"Error streaming market data to client {client_id}: {e}")

    async def broadcast_to_client(self, client_id: str, message: Dict):
        """Broadcast message to specific client"""
        if client_id not in self.clients:
            return

        message_json = json.dumps(message)

        disconnected_clients = []
        for websocket in self.clients[client_id]:
            try:
                await websocket.send(message_json)
            except (ConnectionClosedError, WebSocketException):
                disconnected_clients.append(websocket)

        # Remove disconnected clients
        for websocket in disconnected_clients:
            self.clients[client_id].discard(websocket)

    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all connected clients"""
        message_json = json.dumps(message)

        all_disconnected = []
        for client_id, client_set in self.clients.items():
            disconnected_clients = []
            for websocket in client_set:
                try:
                    await websocket.send(message_json)
                except (ConnectionClosedError, WebSocketException):
                    disconnected_clients.append(websocket)

            # Remove disconnected clients
            for websocket in disconnected_clients:
                client_set.discard(websocket)
                all_disconnected.append((client_id, websocket))

        # Clean up empty client sets
        for client_id, websocket in all_disconnected:
            if not self.clients[client_id]:
                del self.clients[client_id]

    async def send_error(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """Send error message to client"""
        try:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }))
        except:
            pass  # Connection might be closed

    def get_connection_count(self) -> int:
        """Get total number of connected clients"""
        return sum(len(client_set) for client_set in self.clients.values())

    def get_client_count(self) -> int:
        """Get number of unique clients"""
        return len(self.clients)