# Binance Spot Trading Bot - Comprehensive Guide

A low-risk, automated cryptocurrency trading bot for Binance spot markets. Built with capital preservation and steady gains in mind.

## Features

### Core Architecture
- **Data Ingestion**: WebSocket streams for real-time data + REST API fallback
- **Market State Store**: Redis cache for hot data + Parquet/PostgreSQL for historical storage
- **Strategy Engine**: Modular, backtestable strategy framework
- **Risk Manager**: Position sizing, exposure limits, and automated circuit breakers
- **Execution Layer**: Rate-limited order execution with retry logic
- **Persistence**: Full trade, fill, and PnL tracking in PostgreSQL
- **Monitoring**: Prometheus metrics + Grafana dashboards + Telegram alerts
- **Orchestration**: Docker Compose for easy deployment

### Trading Strategies
1. **Grid Trading**: Places orders at predetermined price levels for ranging markets
2. **DCA (Dollar Cost Averaging)**: Regular purchases at intervals with opportunistic buys on dips
3. **Trend Following**: Conservative momentum-based strategy using EMA, RSI, and MACD

### Risk Management
- Maximum position size limits
- Total exposure caps
- Daily loss limits
- Automated circuit breakers
- Conservative position sizing

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Binance API credentials (or use testnet)
- PostgreSQL and Redis (provided via Docker)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd binance_bot
```

2. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Configure settings**:
Edit `.env` with your:
- Binance API credentials
- Trading pairs
- Risk parameters
- Telegram credentials (optional)

4. **Start the bot**:
```bash
# Start with monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d

# Or start without monitoring
docker-compose up -d
```

5. **View logs**:
```bash
docker-compose logs -f bot
```

## Configuration

### Environment Variables

#### Binance API
```bash
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true  # Use testnet for testing
```

#### Trading Configuration
```bash
TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT
```

#### Risk Parameters
```bash
MAX_POSITION_SIZE_USD=1000          # Max single position size
MAX_TOTAL_EXPOSURE_USD=5000         # Max total exposure
MAX_DAILY_LOSS_USD=200              # Daily loss limit
CIRCUIT_BREAKER_LOSS_PERCENT=5.0    # Circuit breaker threshold
```

#### Database
```bash
POSTGRES_PASSWORD=your_secure_password
```

#### Telegram Alerts (Optional)
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Binance Trading Bot                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   WebSocket  │───▶│  Redis Cache │───▶│  Strategies  │  │
│  │   Manager    │    │              │    │   Engine     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                         │          │
│         ▼                                         ▼          │
│  ┌──────────────┐                      ┌──────────────┐    │
│  │  Historical  │                      │     Risk     │    │
│  │    Store     │                      │   Manager    │    │
│  │  (Parquet)   │                      └──────────────┘    │
│  └──────────────┘                               │          │
│                                                  ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  PostgreSQL  │◀───│  Execution   │◀───│   Circuit    │  │
│  │   Database   │    │    Layer     │    │   Breaker    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                                │
│                             ▼                                │
│              ┌──────────────────────────┐                   │
│              │  Binance Spot Exchange   │                   │
│              └──────────────────────────┘                   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Monitoring: Prometheus, Grafana, Telegram           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Strategy Configuration

### Grid Strategy
Ideal for ranging markets. Places buy and sell orders at predetermined price levels.

```python
GridStrategy(
    symbol="BTCUSDT",
    grid_levels=10,              # Number of grid levels
    price_range_percent=3.0,     # ±3% from center price
    position_size_usd=100.0      # Size per grid level
)
```

### DCA Strategy
Conservative accumulation strategy with regular purchases.

```python
DCAStrategy(
    symbol="ETHUSDT",
    purchase_amount_usd=50.0,         # Amount per purchase
    interval_hours=24,                 # Purchase interval
    price_drop_threshold_percent=2.0   # Extra buy on 2% dip
)
```

### Trend Following Strategy
Momentum-based strategy using technical indicators.

```python
TrendFollowingStrategy(
    symbol="BTCUSDT",
    fast_ma_period=9,       # Fast EMA period
    slow_ma_period=21,      # Slow EMA period
    rsi_period=14,          # RSI period
    position_size_usd=500.0
)
```

## Monitoring

### Prometheus Metrics
Access metrics at: `http://localhost:8000`

Key metrics:
- `binance_bot_orders_total` - Total orders placed
- `binance_bot_trades_total` - Total trades executed
- `binance_bot_pnl_total` - Profit/Loss tracking
- `binance_bot_circuit_breaker_active` - Circuit breaker status
- `binance_bot_total_exposure_usd` - Current exposure

### Grafana Dashboards
Access Grafana at: `http://localhost:3000` (default: admin/admin)

Pre-configured dashboards for:
- Trading activity
- PnL tracking
- Risk metrics
- System health

### Telegram Alerts
Receive real-time notifications for:
- Trade executions
- Order placements
- Position changes
- Circuit breaker activations
- Daily summaries
- Error alerts

## Development

### Local Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

### Project Structure
```
binance_bot/
├── src/
│   ├── config/          # Configuration management
│   ├── data/            # Data ingestion (WebSocket, REST)
│   ├── storage/         # Redis cache + Parquet store
│   ├── strategies/      # Trading strategies
│   ├── risk/            # Risk management
│   ├── execution/       # Order execution
│   ├── persistence/     # Database models
│   ├── monitoring/      # Alerts and metrics
│   ├── utils/           # Utilities
│   └── main.py          # Main bot application
├── tests/               # Test suite
├── docker/              # Docker configurations
├── logs/                # Log files
├── data/                # Historical data storage
└── config/              # Configuration files
```

## Safety & Best Practices

### Testing
1. **Always start with testnet**: Set `BINANCE_TESTNET=true`
2. **Paper trade first**: Test strategies with small amounts
3. **Monitor closely**: Watch for 24-48 hours before scaling up

### Risk Management
1. **Start small**: Use conservative position sizes
2. **Set strict limits**: Configure MAX_POSITION_SIZE_USD appropriately
3. **Monitor daily**: Review PnL and positions regularly
4. **Use stop losses**: Strategies include automatic stop losses
5. **Circuit breakers**: Will halt trading on excessive losses

### Security
1. **Protect API keys**: Never commit credentials to version control
2. **Use API restrictions**: Limit API key to spot trading only
3. **Enable 2FA**: On your Binance account
4. **Secure server**: Use firewall and secure SSH access
5. **Regular backups**: Backup database and configuration

## Troubleshooting

### Bot not starting
```bash
# Check logs
docker-compose logs bot

# Check services health
docker-compose ps

# Restart services
docker-compose restart
```

### Database connection issues
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U bot_user -d binance_bot

# Reset database
docker-compose down -v
docker-compose up -d
```

### WebSocket disconnections
The bot automatically reconnects. Check logs for connection issues.

### Circuit breaker activated
1. Review risk metrics: Check why it triggered
2. Analyze trades: Review recent trades in database
3. Adjust parameters: Update risk limits if needed
4. Manual reset: Via Redis or restart bot

## License

MIT License - See LICENSE file for details

## Disclaimer

**USE AT YOUR OWN RISK**

This software is for educational purposes. Cryptocurrency trading carries significant risk of financial loss. The authors are not responsible for any financial losses incurred while using this software.

- Always test thoroughly in testnet first
- Start with small amounts you can afford to lose
- Monitor your bot actively
- Understand the strategies before deploying
- Comply with all applicable laws and regulations
