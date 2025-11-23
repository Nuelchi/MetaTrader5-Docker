#!/usr/bin/env python3
"""
MT5 Trading Server - Production Ready
Provides REST API, WebSocket streaming, and MT5 integration
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator

# Optional MT5 import for testing without MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    logger.info("✅ MetaTrader5 library loaded successfully")
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    logger.warning("⚠️  MetaTrader5 library not available - running in simulation mode")

from auth import SupabaseJWTVerifier, get_current_user
from mt5_account_manager import MT5AccountManager
from market_data_service import MarketDataService
from order_manager import OrderManager
from websocket_server import MT5WebSocketServer
from health_monitor import HealthMonitor
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize services
jwt_verifier = SupabaseJWTVerifier(
    supabase_url=settings.SUPABASE_URL,
    supabase_anon_key=settings.SUPABASE_ANON_KEY
)

account_manager = MT5AccountManager()
market_data_service = MarketDataService()
order_manager = OrderManager()
websocket_server = MT5WebSocketServer()
health_monitor = HealthMonitor()

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting MT5 Trading Server")

    # Initialize services
    try:
        await account_manager.initialize()
        await market_data_service.initialize()
        await order_manager.initialize()
        await websocket_server.initialize()
        await health_monitor.initialize()

        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

    yield

    # Cleanup
    logger.info("🛑 Shutting down MT5 Trading Server")
    try:
        await account_manager.cleanup()
        await market_data_service.cleanup()
        await order_manager.cleanup()
        await websocket_server.cleanup()
        await health_monitor.cleanup()

        logger.info("✅ All services cleaned up successfully")
    except Exception as e:
        logger.error(f"❌ Service cleanup failed: {e}")

app = FastAPI(
    title="MT5 Trading Server API",
    description="Production-ready MT5 trading server with real-time capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class MT5Credentials(BaseModel):
    login: int
    password: str
    server: str

    @validator('login')
    def login_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Login must be a positive integer')
        return v

class TradeRequest(BaseModel):
    symbol: str
    order_type: str  # 'buy', 'sell', 'buylimit', 'selllimit', etc.
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @validator('volume')
    def volume_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Volume must be positive')
        return v

class MarketDataRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    bars: int = 100

    @validator('bars')
    def bars_must_be_reasonable(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('Bars must be between 1 and 10000')
        return v

# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "MT5 Trading Server is running",
        "version": "1.0.0",
        "mt5_available": MT5_AVAILABLE,
        "mode": "production" if MT5_AVAILABLE else "simulation"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    health_status = await health_monitor.check_health()
    return health_status

@app.post("/api/v1/accounts/connect")
async def connect_mt5_account(
    credentials: MT5Credentials,
    current_user: Dict = Depends(get_current_user)
):
    """Connect to MT5 account"""
    logger.info(f"User {current_user['user_id']} attempting to connect MT5 account {credentials.login}")

    result = await account_manager.connect_mt5_account(
        current_user['user_id'],
        credentials.dict()
    )

    if not result['success']:
        logger.warning(f"MT5 connection failed for user {current_user['user_id']}: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result['error'])

    logger.info(f"MT5 connection successful for user {current_user['user_id']}")
    return result

@app.post("/api/v1/accounts/disconnect")
async def disconnect_mt5_account(current_user: Dict = Depends(get_current_user)):
    """Disconnect MT5 account"""
    logger.info(f"User {current_user['user_id']} disconnecting MT5 account")

    result = await account_manager.disconnect_mt5_account(current_user['user_id'])

    if not result['success']:
        logger.warning(f"MT5 disconnection failed for user {current_user['user_id']}: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result['error'])

    logger.info(f"MT5 disconnection successful for user {current_user['user_id']}")
    return result

@app.get("/api/v1/accounts/status")
async def get_account_status(current_user: Dict = Depends(get_current_user)):
    """Get MT5 account status"""
    status = await account_manager.get_account_status(current_user['user_id'])

    if not status:
        return {"connected": False, "message": "No active MT5 connection"}

    return status

@app.post("/api/v1/trades")
async def execute_trade(
    trade_request: TradeRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Execute trade"""
    logger.info(f"User {current_user['user_id']} executing trade: {trade_request.dict()}")

    # Convert to MT5 format
    mt5_request = order_manager.create_mt5_order_request(trade_request.dict())

    result = await order_manager.execute_trade(
        current_user['user_id'],
        mt5_request
    )

    if not result['success']:
        logger.warning(f"Trade execution failed for user {current_user['user_id']}: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result['error'])

    logger.info(f"Trade executed successfully for user {current_user['user_id']}: {result}")
    return result

@app.get("/api/v1/positions")
async def get_positions(current_user: Dict = Depends(get_current_user)):
    """Get open positions"""
    positions = await order_manager.get_positions(current_user['user_id'])
    return {"positions": positions}

@app.get("/api/v1/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    timeframe: str = "H1",
    bars: int = 100,
    current_user: Dict = Depends(get_current_user)
):
    """Get historical market data"""
    try:
        data = await market_data_service.get_historical_data(symbol, timeframe, bars)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": data,
            "count": len(data) if data else 0
        }
    except Exception as e:
        logger.error(f"Market data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket_server.handle_connection(websocket)

@app.get("/api/v1/orders")
async def get_orders(current_user: Dict = Depends(get_current_user)):
    """Get order history"""
    orders = await order_manager.get_order_history(current_user['user_id'])
    return {"orders": orders}

@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(
    order_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Cancel pending order"""
    result = await order_manager.cancel_order(current_user['user_id'], order_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result

@app.get("/api/v1/symbols")
async def get_available_symbols():
    """Get available trading symbols"""
    symbols = await market_data_service.get_available_symbols()
    return {"symbols": symbols}

@app.get("/api/v1/account/info")
async def get_account_info(current_user: Dict = Depends(get_current_user)):
    """Get detailed account information"""
    account_info = await account_manager.get_account_info(current_user['user_id'])

    if not account_info:
        raise HTTPException(status_code=404, detail="Account not connected")

    return account_info

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return {
        "error": True,
        "status_code": 500,
        "detail": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Start the server
    uvicorn.run(
        "mt5_server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.API_DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )