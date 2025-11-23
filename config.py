"""
Configuration management for MT5 Server
Loads environment variables and provides typed configuration
"""

import os
from typing import List, Optional
try:
    from pydantic import BaseSettings, validator
except ImportError:
    # Fallback for newer pydantic versions
    from pydantic_settings import BaseSettings
    from pydantic import validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ==========================================
    # SUPABASE AUTHENTICATION
    # ==========================================
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: Optional[str] = None  # Not needed when using Supabase client auth

    # ==========================================
    # MT5 SERVER CONFIGURATION
    # ==========================================
    mt5_path: str = "/config/.wine/drive_c/Program Files/MetaTrader 5"
    mt5_server_port: int = 8001
    mt5_encryption_key: str

    # ==========================================
    # API SECURITY
    # ==========================================
    api_keys: Optional[str] = None
    allowed_ips: Optional[str] = None
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # ==========================================
    # RATE LIMITING
    # ==========================================
    requests_per_minute: int = 60
    burst_limit: int = 10
    websocket_connections_max: int = 100

    # ==========================================
    # WEBSOCKET CONFIGURATION
    # ==========================================
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    ws_ping_interval: int = 30
    ws_ping_timeout: int = 10

    # ==========================================
    # REST API CONFIGURATION
    # ==========================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_debug: bool = False

    # ==========================================
    # DATABASE CONFIGURATION
    # ==========================================
    # Note: MT5 server uses Supabase client (same as backend) - no direct DB connection needed
    database_url: Optional[str] = None  # Not used - we use Supabase client
    db_pool_size: int = 10  # Not used
    db_max_overflow: int = 20  # Not used
    db_pool_recycle: int = 3600  # Not used

    # ==========================================
    # REDIS CONFIGURATION (Optional - for caching)
    # ==========================================
    redis_url: Optional[str] = None
    redis_cache_ttl: int = 300

    # ==========================================
    # LOGGING CONFIGURATION
    # ==========================================
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "/var/log/mt5-server.log"
    log_max_size: str = "100MB"
    log_backup_count: int = 5

    # ==========================================
    # MONITORING & METRICS
    # ==========================================
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30

    # ==========================================
    # MARKET DATA CONFIGURATION
    # ==========================================
    market_data_cache_size: int = 1000
    market_data_update_interval: int = 200
    historical_data_cache_ttl: int = 3600

    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    max_position_size_pct: float = 0.1
    max_daily_loss_pct: float = 0.05
    max_concurrent_trades: int = 10
    default_stop_loss_pips: int = 50
    default_take_profit_pips: int = 100

    # ==========================================
    # NOTIFICATION CONFIGURATION
    # ==========================================
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_email: Optional[str] = None

    # ==========================================
    # BACKUP CONFIGURATION
    # ==========================================
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_path: str = "/var/backups/mt5-server"

    # ==========================================
    # CONTAINER CONFIGURATION
    # ==========================================
    docker_network: str = "mt5-network"
    container_restart_policy: str = "always"
    container_memory_limit: str = "2g"
    container_cpu_limit: str = "1.0"

    # ==========================================
    # SSL/TLS CONFIGURATION (for production)
    # ==========================================
    ssl_enabled: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_cert_path: Optional[str] = None

    # ==========================================
    # DEVELOPMENT/DEBUG SETTINGS
    # ==========================================
    debug_mode: bool = False
    enable_swagger_docs: bool = False
    enable_cors: bool = True
    cors_origins: Optional[str] = None

    # ==========================================
    # MT5 TERMINAL SETTINGS
    # ==========================================
    mt5_auto_login: bool = True
    mt5_connection_timeout: int = 30
    mt5_reconnect_attempts: int = 5
    mt5_reconnect_delay: int = 10

    # ==========================================
    # PERFORMANCE TUNING
    # ==========================================
    max_workers: int = 4
    thread_pool_size: int = 10
    asyncio_max_workers: int = 20
    memory_cache_size_mb: int = 512

    # ==========================================
    # ALERTS & MONITORING
    # ==========================================
    alert_webhook_url: Optional[str] = None
    alert_on_disconnection: bool = True
    alert_on_high_latency: bool = True
    latency_threshold_ms: int = 1000

    # ==========================================
    # FEATURE FLAGS
    # ==========================================
    enable_real_time_trading: bool = True
    enable_paper_trading: bool = True
    enable_strategy_backtesting: bool = True
    enable_market_data_streaming: bool = True
    enable_order_management: bool = True
    enable_position_tracking: bool = True
    enable_risk_management: bool = True
    enable_performance_analytics: bool = True

    # ==========================================
    # EXTERNAL INTEGRATIONS
    # ==========================================
    influxdb_url: Optional[str] = None
    influxdb_token: Optional[str] = None
    influxdb_org: Optional[str] = None
    influxdb_bucket: str = "mt5-metrics"

    grafana_url: Optional[str] = None
    grafana_api_key: Optional[str] = None

    prometheus_pushgateway_url: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator('mt5_encryption_key')
    def validate_encryption_key(cls, v):
        """Validate that encryption key is provided and has minimum length"""
        if not v or len(v) < 32:
            raise ValueError('MT5_ENCRYPTION_KEY must be at least 32 characters long')
        return v

    # Note: supabase_jwt_secret is now optional since we use Supabase client auth
    # (same as the backend does in core/security.py)

    @property
    def api_keys_list(self) -> List[str]:
        """Get API keys as a list"""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(',') if key.strip()]

    @property
    def allowed_ips_list(self) -> List[str]:
        """Get allowed IPs as a list"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(',') if ip.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if not self.cors_origins:
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

# Global settings instance
settings = Settings()