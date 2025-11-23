"""
Health Monitor
Monitors system health, MT5 connection status, and performance metrics
"""

import asyncio
import psutil
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Optional MT5 import for testing without MT5
try:
    # Try mt5linux first (Linux-compatible)
    import mt5linux as mt5
    logger.info("✅ mt5linux library loaded in health monitor")
except ImportError:
    try:
        # Fallback to MetaTrader5 (Windows)
        import MetaTrader5 as mt5
        logger.info("✅ MetaTrader5 library loaded in health monitor")
    except ImportError:
        mt5 = None
        logger.warning("⚠️  No MT5 library available in health monitor - running in simulation mode")
import logging
from datetime import datetime
import time

from config import settings

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitors system and MT5 health"""

    def __init__(self):
        self.mt5_status = False
        self.last_mt5_check = None
        self.error_count = 0
        self.start_time = datetime.now()

    async def initialize(self):
        """Initialize the health monitor"""
        logger.info("Initializing Health Monitor")
        self.start_time = datetime.now()
        logger.info("Health Monitor initialized successfully")

    async def cleanup(self):
        """Cleanup health monitor resources"""
        logger.info("Cleaning up Health Monitor")

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "services": {},
                "system": {},
                "errors": []
            }

            # Check MT5 connection
            mt5_health = await self.check_mt5_health()
            health_data["services"]["mt5"] = mt5_health

            if not mt5_health["healthy"]:
                health_data["status"] = "degraded"
                health_data["errors"].append("MT5 connection issues")

            # Check system resources
            system_health = self.check_system_health()
            health_data["system"] = system_health

            if not system_health["healthy"]:
                health_data["status"] = "unhealthy"
                health_data["errors"].extend(system_health["issues"])

            # Overall status determination
            if health_data["errors"]:
                if len(health_data["errors"]) > 2:
                    health_data["status"] = "unhealthy"
                else:
                    health_data["status"] = "degraded"

            return health_data

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    async def check_mt5_health(self) -> Dict[str, Any]:
        """Check MT5 connection and terminal health"""
        try:
            mt5_health = {
                "healthy": False,
                "connected": False,
                "terminal_info": None,
                "account_info": None,
                "last_check": datetime.now().isoformat(),
                "issues": []
            }

            # Check MT5 initialization (only if initialize method exists)
            if hasattr(mt5, 'initialize') and not mt5.initialize():
                mt5_health["issues"].append("MT5 initialization failed")
                self.error_count += 1
                return mt5_health
            elif not hasattr(mt5, 'initialize'):
                # mt5linux doesn't need initialization, just check if library is available
                mt5_health["healthy"] = True
                mt5_health["connected"] = True
                logger.info("MT5 library available (no initialization needed)")

            # Get terminal info (only if function exists - mt5linux doesn't have this)
            if hasattr(mt5, 'terminal_info'):
                terminal_info = mt5.terminal_info()
                if terminal_info:
                    mt5_health["terminal_info"] = {
                        "name": terminal_info.name,
                        "connected": terminal_info.connected,
                        "trade_allowed": terminal_info.trade_allowed,
                        "community_account": terminal_info.community_account,
                        "community_connection": terminal_info.community_connection
                    }

                    if terminal_info.connected:
                        mt5_health["connected"] = True
                    else:
                        mt5_health["issues"].append("MT5 terminal not connected")
            else:
                # mt5linux doesn't have terminal_info, assume connected if library is available
                mt5_health["terminal_info"] = {"library_type": "mt5linux", "connected": True}
                logger.info("mt5linux library detected - terminal_info not available")

            # Get account info
            account_info = mt5.account_info()
            if account_info:
                mt5_health["account_info"] = {
                    "login": account_info.login,
                    "server": account_info.server,
                    "balance": float(account_info.balance),
                    "equity": float(account_info.equity),
                    "margin": float(account_info.margin),
                    "margin_free": float(account_info.margin_free),
                    "profit": float(account_info.profit)
                }
                # If we have account info, we're definitely connected
                mt5_health["connected"] = True
            else:
                mt5_health["issues"].append("No account information available")

            # Determine overall health - for mt5linux, focus on account info availability
            if hasattr(mt5, 'terminal_info'):
                # Standard MT5 library - require terminal info
                mt5_health["healthy"] = (
                    mt5_health["connected"] and
                    mt5_health["terminal_info"] is not None and
                    mt5_health["account_info"] is not None and
                    len(mt5_health["issues"]) == 0
                )
            else:
                # mt5linux - just require account info and no issues
                mt5_health["healthy"] = (
                    mt5_health["account_info"] is not None and
                    len(mt5_health["issues"]) == 0
                )

            self.mt5_status = mt5_health["healthy"]
            self.last_mt5_check = datetime.now()

            return mt5_health

        except Exception as e:
            logger.error(f"MT5 health check error: {e}")
            self.error_count += 1
            return {
                "healthy": False,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    def check_system_health(self) -> Dict[str, Any]:
        """Check system resource health"""
        try:
            system_health = {
                "healthy": True,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections()),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "issues": []
            }

            # Check CPU usage
            if system_health["cpu_percent"] > 90:
                system_health["issues"].append(f"High CPU usage: {system_health['cpu_percent']}%")
                system_health["healthy"] = False

            # Check memory usage
            if system_health["memory_percent"] > 90:
                system_health["issues"].append(f"High memory usage: {system_health['memory_percent']}%")
                system_health["healthy"] = False

            # Check disk usage
            if system_health["disk_percent"] > 95:
                system_health["issues"].append(f"High disk usage: {system_health['disk_percent']}%")
                system_health["healthy"] = False

            return system_health

        except Exception as e:
            logger.error(f"System health check error: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "issues": ["System health check failed"]
            }

    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory": psutil.virtual_memory()._asdict(),
                    "disk": psutil.disk_usage('/')._asdict(),
                    "network": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else None,
                    "boot_time": psutil.boot_time()
                },
                "mt5": {
                    "status": self.mt5_status,
                    "last_check": self.last_mt5_check.isoformat() if self.last_mt5_check else None,
                    "error_count": self.error_count
                },
                "process": {
                    "pid": psutil.Process().pid,
                    "cpu_percent": psutil.Process().cpu_percent(),
                    "memory_info": psutil.Process().memory_info()._asdict(),
                    "num_threads": psutil.Process().num_threads(),
                    "num_fds": psutil.Process().num_fds() if hasattr(psutil.Process(), 'num_fds') else None
                }
            }

            # Add MT5 specific metrics if available
            try:
                if hasattr(mt5, 'initialize'):
                    if mt5.initialize():
                        terminal_info = mt5.terminal_info() if hasattr(mt5, 'terminal_info') else None
                        account_info = mt5.account_info()
                else:
                    # mt5linux doesn't need initialization
                    terminal_info = mt5.terminal_info() if hasattr(mt5, 'terminal_info') else None
                    account_info = mt5.account_info()

                    if terminal_info:
                        metrics["mt5"]["terminal"] = {
                            "connected": terminal_info.connected,
                            "trade_allowed": terminal_info.trade_allowed,
                            "ping_last": terminal_info.ping_last if hasattr(terminal_info, 'ping_last') else None
                        }
                    elif not hasattr(mt5, 'terminal_info'):
                        # mt5linux doesn't have terminal_info
                        metrics["mt5"]["terminal"] = {"library_type": "mt5linux"}

                    if account_info:
                        metrics["mt5"]["account"] = {
                            "login": account_info.login,
                            "server": account_info.server,
                            "leverage": account_info.leverage,
                            "balance": float(account_info.balance),
                            "equity": float(account_info.equity),
                            "margin": float(account_info.margin),
                            "margin_free": float(account_info.margin_free),
                            "profit": float(account_info.profit)
                        }

            except Exception as e:
                logger.warning(f"Could not get detailed MT5 metrics: {e}")

            return metrics

        except Exception as e:
            logger.error(f"Detailed metrics error: {e}")
            return {"error": str(e)}

    async def monitor_loop(self):
        """Continuous monitoring loop"""
        logger.info("Starting health monitoring loop")

        while True:
            try:
                # Perform health check
                health = await self.check_health()

                # Log issues
                if health["status"] != "healthy":
                    logger.warning(f"Health check issues: {health}")

                # Send alerts if configured
                if settings.alert_webhook_url and health["status"] == "unhealthy":
                    await self.send_alert(health)

                await asyncio.sleep(settings.health_check_interval)

            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def send_alert(self, health_data: Dict[str, Any]):
        """Send health alert to configured webhook"""
        try:
            import aiohttp

            alert_data = {
                "alert_type": "health_check_failed",
                "severity": "high" if health_data["status"] == "unhealthy" else "medium",
                "timestamp": health_data["timestamp"],
                "status": health_data["status"],
                "errors": health_data["errors"],
                "system_info": health_data["system"]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(settings.alert_webhook_url, json=alert_data) as response:
                    if response.status == 200:
                        logger.info("Health alert sent successfully")
                    else:
                        logger.error(f"Failed to send health alert: {response.status}")

        except Exception as e:
            logger.error(f"Error sending health alert: {e}")

    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()

    def reset_error_count(self):
        """Reset error counter"""
        self.error_count = 0