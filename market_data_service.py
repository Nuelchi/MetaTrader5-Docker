"""
Market Data Service
Handles historical and real-time market data retrieval
"""

import asyncio
import MetaTrader5 as mt5
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging
from datetime import datetime, timedelta
import time

from config import settings

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for retrieving market data from MT5"""

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1
    }

    def __init__(self):
        self.cache = {}
        self.last_update = {}

    async def initialize(self):
        """Initialize the market data service"""
        logger.info("Initializing Market Data Service")
        # MT5 should already be initialized by account manager
        logger.info("Market Data Service initialized successfully")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Market Data Service")
        self.cache.clear()
        self.last_update.clear()

    async def get_historical_data(self, symbol: str, timeframe: str, bars: int = 100) -> List[Dict]:
        """Get historical market data"""
        try:
            logger.debug(f"Getting historical data: {symbol} {timeframe} {bars} bars")

            tf = self.TIMEFRAME_MAP.get(timeframe.upper(), mt5.TIMEFRAME_H1)

            # Get data from MT5
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)

            if rates is None:
                logger.error(f"Failed to get historical data for {symbol}")
                return []

            # Convert to list of dictionaries
            data = []
            for rate in rates:
                data.append({
                    'timestamp': int(rate['time']) * 1000,  # Convert to milliseconds
                    'open': float(rate['open']),
                    'high': float(rate['high']),
                    'low': float(rate['low']),
                    'close': float(rate['close']),
                    'volume': int(rate['volume'])
                })

            logger.debug(f"Retrieved {len(data)} bars for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []

    async def get_real_time_data(self, symbol: str) -> Optional[Dict]:
        """Get real-time market data"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return {
                    'symbol': symbol,
                    'bid': float(tick.bid),
                    'ask': float(tick.ask),
                    'last': float(tick.last) if tick.last else None,
                    'volume': int(tick.volume) if tick.volume else 0,
                    'timestamp': int(tick.time)
                }
            return None
        except Exception as e:
            logger.error(f"Error getting real-time data for {symbol}: {e}")
            return None

    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols"""
        try:
            symbols = mt5.symbols_get()
            if symbols:
                return [symbol.name for symbol in symbols]
            return []
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []

    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get detailed symbol information"""
        try:
            info = mt5.symbol_info(symbol)
            if info:
                return {
                    'name': info.name,
                    'description': info.description,
                    'currency_base': info.currency_base,
                    'currency_profit': info.currency_profit,
                    'point': info.point,
                    'digits': info.digits,
                    'spread': info.spread,
                    'volume_min': info.volume_min,
                    'volume_max': info.volume_max,
                    'volume_step': info.volume_step,
                    'trade_mode': info.trade_mode,
                    'trade_allowed': info.select
                }
            return None
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None

    async def stream_market_data(self, symbol: str, callback):
        """Stream real-time market data"""
        last_tick = None

        while True:
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick and (last_tick is None or tick.time != last_tick.time):
                    data = {
                        'symbol': symbol,
                        'bid': float(tick.bid),
                        'ask': float(tick.ask),
                        'last': float(tick.last) if tick.last else None,
                        'volume': int(tick.volume) if tick.volume else 0,
                        'timestamp': int(tick.time)
                    }

                    await callback(data)
                    last_tick = tick

                await asyncio.sleep(settings.market_data_update_interval / 1000)

            except Exception as e:
                logger.error(f"Error streaming market data for {symbol}: {e}")
                await asyncio.sleep(1)

    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for trading"""
        try:
            info = mt5.symbol_info(symbol)
            return info is not None and info.select
        except:
            return False