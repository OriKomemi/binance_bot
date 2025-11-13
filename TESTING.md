# Testing Guide - Local Dry Run

## Overview

This guide will help you test the bot locally using Binance Testnet API credentials without risking real funds.

## Step 1: Get Binance Testnet Credentials

### Option A: Binance Spot Testnet (Recommended)

1. Visit: https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Save your API Key and Secret Key

### Option B: Binance Main API with Testnet Mode

The bot supports testnet mode which simulates trades without execution.

## Step 2: Local Environment Setup

### Create Local .env File

```bash
# Copy example and edit
cp .env.example .env
```

Edit `.env` with your testnet credentials:

```bash
# Binance Testnet Credentials
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
BINANCE_TESTNET=true

# Trading Configuration
TRADING_PAIRS=BTCUSDT,ETHUSDT

# Risk Parameters (Conservative for testing)
MAX_POSITION_SIZE_USD=100
MAX_TOTAL_EXPOSURE_USD=500
MAX_DAILY_LOSS_USD=50
CIRCUIT_BREAKER_LOSS_PERCENT=5.0

# Database (Local testing)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=binance_bot_test
POSTGRES_USER=bot_user
POSTGRES_PASSWORD=test_password

# Redis (Local testing)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Telegram (Optional for testing)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Logging
LOG_LEVEL=DEBUG
ENVIRONMENT=testing
```

## Step 3: Local Infrastructure Setup

### Option A: Use Docker for Dependencies Only

```bash
# Start only PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 10

# Verify services are running
docker-compose ps
```

### Option B: Install Locally (No Docker)

**PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Start PostgreSQL
sudo service postgresql start  # Linux
brew services start postgresql  # macOS

# Create database
sudo -u postgres createuser bot_user
sudo -u postgres createdb binance_bot_test
sudo -u postgres psql -c "ALTER USER bot_user WITH PASSWORD 'test_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE binance_bot_test TO bot_user;"
```

**Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo service redis-server start

# macOS
brew install redis
brew services start redis
```

## Step 4: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install bot in development mode
pip install -e .
```

## Step 5: Validate Setup

Run the validation script:

```bash
python scripts/validate_setup.py
```

This will check:
- Environment variables
- Database connection
- Redis connection
- Binance API connectivity
- Testnet access

## Step 6: Run Dry Run Tests

### Test 1: Quick Health Check

```bash
python scripts/health_check.py
```

### Test 2: Data Connection Test

```bash
python scripts/test_data_ingestion.py
```

### Test 3: Strategy Test

```bash
python scripts/test_strategies.py
```

### Test 4: Full Dry Run

```bash
# Run bot in dry-run mode (no actual orders)
python scripts/dry_run.py --duration 300  # Run for 5 minutes
```

## Step 7: Run Bot Locally

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python -m src.main

# Or use the entry point
binance-bot
```

### Monitor Output

Watch for:
- ✅ "Bot initialization complete"
- ✅ "All health checks passed"
- ✅ "WebSocket manager started"
- ✅ "Subscribed to market data"
- ✅ "Strategy signals generated"

## Troubleshooting

### "Database connection failed"

```bash
# Check PostgreSQL is running
pg_isready

# If using Docker
docker-compose logs postgres
```

### "Redis connection failed"

```bash
# Check Redis is running
redis-cli ping

# If using Docker
docker-compose logs redis
```

### "Binance API error"

```bash
# Test API connectivity
python scripts/test_binance_api.py
```

### "Import errors"

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Testing Checklist

- [ ] Environment variables configured
- [ ] PostgreSQL running and accessible
- [ ] Redis running and accessible
- [ ] Binance testnet API credentials valid
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] Health checks passing
- [ ] Data ingestion working
- [ ] Strategies generating signals
- [ ] Risk manager approving/rejecting trades
- [ ] Orders placed successfully (testnet)
- [ ] Database recording trades
- [ ] Logs showing expected behavior

## Next Steps

Once local testing is successful:

1. **Run for 24 hours**: Monitor behavior and stability
2. **Review logs**: Check for errors or unexpected behavior
3. **Validate data**: Check database for correct data recording
4. **Test circuit breaker**: Simulate loss scenarios
5. **Review PnL**: Analyze simulated trading performance

## Production Deployment

After successful testing:

1. Switch to production API keys
2. Set `BINANCE_TESTNET=false`
3. Use production-grade infrastructure
4. Start with small position sizes
5. Enable monitoring and alerts

## Safety Reminders

- ⚠️ Always test on testnet first
- ⚠️ Start with small position sizes
- ⚠️ Monitor actively for first 48 hours
- ⚠️ Keep API keys secure
- ⚠️ Enable all risk management features
