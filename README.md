# MT5 Trading Server - Production Ready

A production-ready MT5 trading server with REST API, WebSocket streaming, and Supabase authentication integration. Designed to work with Linux MT5 installations and provide institutional-grade trading capabilities.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Linux VPS with MT5 installed
- Supabase project with authentication configured

### 1. Clone and Setup
```bash
git clone https://github.com/Nuelchi/MetaTrader5-Docker.git
cd MetaTrader5-Docker
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Build and Run
```bash
# Build the container
sudo docker-compose build

# Run the server
sudo docker-compose up -d

# Check logs
sudo docker-compose logs -f mt5-server
```

### 4. Verify Installation
```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status": "healthy", ...}
```

## 📋 Environment Configuration

Create a `.env` file with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# MT5 Server Configuration
MT5_ENCRYPTION_KEY=your-32-character-encryption-key

# JWT Configuration
JWT_SECRET=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
WS_HOST=0.0.0.0
WS_PORT=8765

# Optional: External Integrations
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
GRAFANA_URL=http://localhost:3000
```

## 🔧 Key Fixes Applied

### 1. MT5 Library Compatibility
**Problem**: `mt5linux` library doesn't have `initialize()` method
**Solution**: Check for method existence before calling

```python
# In mt5_account_manager.py and health_monitor.py
if hasattr(mt5, 'initialize'):
    if not mt5.initialize():
        raise Exception("MT5 initialization failed")
else:
    # mt5linux doesn't need initialization
    logger.info("MT5 library available (no initialization needed)")
```

### 2. Settings Field Access
**Problem**: Pydantic BaseSettings converts env vars to lowercase fields
**Solution**: Use lowercase field names consistently

```python
# ❌ Wrong
settings.SUPABASE_URL
settings.LOG_LEVEL

# ✅ Correct
settings.supabase_url
settings.log_level
```

### 3. Supabase Authentication
**Problem**: SupabaseJWTVerifier constructor expected parameters
**Solution**: Use global Supabase client like Trainflow backend

```python
# Initialize global client
supabase_client = supabase.create_client(settings.supabase_url, settings.supabase_anon_key)

# Use in verifier without parameters
class SupabaseAuthVerifier:
    def __init__(self):
        pass  # Uses global client
```

### 4. CORS Configuration
**Problem**: CORS settings access used uppercase
**Solution**: Use property method for list conversion

```python
# In mt5_server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Property handles conversion
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🏗️ Architecture

```
MT5 Trading Server
├── REST API (FastAPI)
│   ├── Account Management (/api/v1/accounts/*)
│   ├── Order Management (/api/v1/trades)
│   ├── Market Data (/api/v1/market-data/*)
│   └── Position Tracking (/api/v1/positions)
├── WebSocket Server (8765)
│   ├── Real-time price feeds
│   ├── Order status updates
│   └── Account notifications
├── Services
│   ├── MT5AccountManager - Account connections
│   ├── OrderManager - Trade execution
│   ├── MarketDataService - Price feeds
│   ├── HealthMonitor - System monitoring
│   └── SupabaseAuthVerifier - JWT validation
└── Security
    ├── Supabase JWT authentication
    ├── API key fallback
    └── Rate limiting
```

## 📡 API Endpoints

### Authentication Required
All endpoints require Bearer token authentication:
```
Authorization: Bearer <supabase-jwt-token>
```

### Core Endpoints

#### Health Check
```bash
GET /health
# Returns system and MT5 health status
```

#### Account Management
```bash
POST /api/v1/accounts/connect
# Connect MT5 account with credentials

POST /api/v1/accounts/disconnect
# Disconnect MT5 account

GET /api/v1/accounts/status
# Get connection status

GET /api/v1/account/info
# Get detailed account information
```

#### Trading
```bash
POST /api/v1/trades
# Execute market/limit orders

GET /api/v1/positions
# Get open positions

GET /api/v1/orders
# Get order history

DELETE /api/v1/orders/{order_id}
# Cancel pending order
```

#### Market Data
```bash
GET /api/v1/market-data/{symbol}?timeframe=H1&bars=100
# Get historical market data

GET /api/v1/symbols
# Get available trading symbols
```

### WebSocket Streaming
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8765/ws');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your-jwt-token'
}));

// Subscribe to market data
ws.send(JSON.stringify({
  type: 'subscribe',
  symbols: ['EURUSD', 'GBPUSD']
}));
```

## 🔒 Security Features

- **Supabase JWT Authentication**: Matches Trainflow backend auth
- **API Key Fallback**: For system integrations
- **Rate Limiting**: Configurable per endpoint
- **Credential Encryption**: AES-256 encryption for stored credentials
- **Input Validation**: Comprehensive request validation
- **CORS Protection**: Configurable origin restrictions

## 📊 Monitoring & Health

### Health Checks
- **System Resources**: CPU, memory, disk, network
- **MT5 Connection**: Terminal and account status
- **Service Status**: All internal services
- **Error Tracking**: Automatic error reporting

### Metrics Available
```bash
GET /health  # Comprehensive health report
GET /metrics # Detailed performance metrics
```

## 🚀 Deployment

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  mt5-server:
    build: .
    ports:
      - "8000:8000"  # REST API
      - "8765:8765"  # WebSocket
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/var/log/mt5-server
```

### Manual Docker Run
```bash
sudo docker run -d \
  --name mt5-server \
  -p 8000:8000 \
  -p 8765:8765 \
  --env-file .env \
  --restart unless-stopped \
  metatrader5-docker_mt5-server:latest
```

### Production Considerations
- Use reverse proxy (nginx/caddy) for SSL
- Configure proper logging rotation
- Set up monitoring (Prometheus/Grafana)
- Enable backup procedures
- Configure firewall rules

## 🐛 Troubleshooting

### Common Issues

#### Health Check Shows "degraded"
- **Cause**: MT5 library compatibility issues
- **Fix**: Ensure all fixes from this README are applied
- **Check**: `curl http://localhost:8000/health`

#### Authentication Errors
- **Cause**: Invalid Supabase configuration
- **Fix**: Verify SUPABASE_URL and SUPABASE_ANON_KEY in .env
- **Check**: Test with valid JWT token

#### MT5 Connection Failed
- **Cause**: MT5 not installed or credentials invalid
- **Fix**: Install MT5 on host system, verify credentials
- **Check**: Check MT5 terminal logs

#### Port Already in Use
- **Cause**: Another service using ports 8000/8765
- **Fix**: Change ports in docker-compose.yml or stop conflicting service

### Logs and Debugging
```bash
# View container logs
sudo docker-compose logs -f mt5-server

# Check container status
sudo docker ps

# Enter container for debugging
sudo docker exec -it mt5-server bash
```

## 🔄 Integration with Trainflow

### Backend Integration
The MT5 server is designed to integrate seamlessly with your Trainflow backend:

1. **Shared Authentication**: Uses same Supabase project
2. **Compatible APIs**: REST endpoints match expected patterns
3. **WebSocket Streaming**: Real-time data for frontend

### Frontend Connection
Update your Trainflow frontend to connect to MT5 server:

```javascript
// In backend-api.ts
const MT5_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://your-vps-domain.com'
  : 'http://localhost:8000';

// Use MT5 endpoints for live trading
await backendAPI.startLiveStrategy({
  strategy_id: strategyId,
  symbol: symbol,
  mt5_server_url: MT5_BASE_URL
});
```

## 📝 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run without Docker
python mt5_server.py
```

### Testing
```bash
# Run health tests
python test_requirements.py

# Test authentication
python test_jwt_token.py

# Test Supabase connection
python simple_supabase_test.py
```

### Code Structure
```
MetaTrader5-Docker/
├── mt5_server.py          # Main FastAPI application
├── config.py              # Settings and configuration
├── auth.py                # Authentication handlers
├── mt5_account_manager.py # MT5 account management
├── order_manager.py       # Order execution
├── market_data_service.py # Market data handling
├── health_monitor.py      # System monitoring
├── websocket_server.py   # WebSocket streaming
├── Dockerfile.server      # Docker configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (gitignored)
└── README.md             # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the Trainflow trading platform. See main project license for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs: `sudo docker-compose logs mt5-server`
3. Verify your .env configuration
4. Test with the provided test scripts

---

**Status**: ✅ Production Ready
**MT5 Compatibility**: ✅ Linux (mt5linux)
**Authentication**: ✅ Supabase JWT
**Health Monitoring**: ✅ System & MT5
**WebSocket Streaming**: ✅ Real-time data
**Docker Deployment**: ✅ Automated
