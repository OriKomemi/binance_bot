# Quick Start - Local Testing with Your API Keys

## Step-by-Step Guide

### 1. Get Your Binance Testnet Credentials

Visit **Binance Spot Testnet**: https://testnet.binance.vision/

- Click "Generate HMAC_SHA256 Key"
- Copy your API Key and Secret Key
- These are TEST credentials (no real money involved)

### 2. Configure Environment

```bash
# Navigate to the bot directory
cd binance_bot

# Copy the example environment file
cp .env.example .env

# Edit the .env file with your testnet credentials
nano .env   # or use your preferred editor
```

Update these lines in `.env`:
```bash
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
BINANCE_TESTNET=true
```

### 3. Run Automated Setup

```bash
# Make the setup script executable
chmod +x scripts/quick_start.sh

# Run the automated setup
./scripts/quick_start.sh
```

This will:
- ✅ Check for .env file
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Start Docker containers (PostgreSQL + Redis)
- ✅ Run validation tests

### 4. Run Validation Tests

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run validation
python scripts/validate_setup.py
```

You should see:
```
🎉 All checks passed! You're ready to run the bot.
```

### 5. Test Binance API Connection

```bash
python scripts/test_binance_api.py
```

Expected output:
```
✅ Ping successful
✅ Server time: 2024-01-15 10:30:45
✅ BTC Price: $43,500.00
🎉 All Binance API tests passed!
```

### 6. Run Dry Run Test

```bash
# 5-minute test
python scripts/dry_run.py

# Or 30-minute test
python scripts/dry_run.py --duration 1800
```

This will:
- ✅ Test API connectivity
- ✅ Retrieve market data
- ✅ Generate trading signals
- ✅ Show strategy behavior
- ✅ No real orders placed

### 7. Review Results

The dry run will show:
```
🟢 dca_BTCUSDT: BUY
   Price: $43,500.00
   Quantity: 0.001149
   Confidence: 85%

⚪ grid_BTCUSDT: HOLD
   ...

📊 DRY RUN SUMMARY
Total signals: 15
  🟢 Buy signals: 3
  🔴 Sell signals: 1
  ⚪ Hold signals: 11
```

### 8. Start the Bot (Optional)

Once you're satisfied with the dry run:

```bash
# Start the bot
python -m src.main
```

Monitor the output for:
- ✅ "Bot initialization complete"
- ✅ "All health checks passed"
- ✅ "Subscribed to market data"
- ✅ Strategy signals

Press `Ctrl+C` to stop.

## Alternative: Docker-Only Setup

If you prefer to run everything in Docker:

```bash
# Edit .env with your credentials
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop everything
docker-compose down
```

## Troubleshooting

### "Module not found" error
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install -e .
```

### "Connection refused" error
```bash
# Restart services
docker-compose restart postgres redis

# Or start them if not running
docker-compose up -d postgres redis
```

### "Invalid API key" error
```bash
# Verify your .env file
cat .env | grep BINANCE_API_KEY

# Make sure you're using testnet credentials
# from https://testnet.binance.vision/
```

### "Redis/PostgreSQL not available"
```bash
# Check Docker containers
docker-compose ps

# View container logs
docker-compose logs postgres
docker-compose logs redis

# Restart containers
docker-compose restart
```

## What to Look For

### Good Signs ✅
- API ping successful
- Market data retrieved
- Strategies generating signals
- No connection errors
- Risk checks passing

### Warning Signs ⚠️
- Frequent API errors
- Connection timeouts
- Missing market data
- Errors in strategy calculations
- Risk checks always failing

## Testing Checklist

- [ ] Testnet API credentials configured
- [ ] Validation script passes all checks
- [ ] Binance API test successful
- [ ] Market data retrieval working
- [ ] Strategies generating signals
- [ ] Dry run completes without errors
- [ ] Bot starts successfully
- [ ] No error messages in logs

## Next Steps

After successful local testing:

1. **Run longer test**: `python scripts/dry_run.py --duration 3600` (1 hour)
2. **Monitor behavior**: Watch signals and check they make sense
3. **Review documentation**: Read `TESTING.md` for advanced testing
4. **Deploy**: Follow `DEPLOYMENT.md` for production setup

## Safety Reminders

- 🛡️ These are TEST credentials on TESTNET
- 🛡️ No real money is involved in testnet
- 🛡️ Testnet simulates real trading
- 🛡️ Always test thoroughly before real trading
- 🛡️ Start with small amounts in production

## Need Help?

1. Check `TESTING.md` for detailed testing guide
2. Check `DEPLOYMENT.md` for production deployment
3. Review logs in `logs/bot.log`
4. Check Docker logs: `docker-compose logs`

## Quick Commands Reference

```bash
# Setup
./scripts/quick_start.sh

# Testing
python scripts/validate_setup.py      # Validate setup
python scripts/health_check.py        # Quick health check
python scripts/test_binance_api.py    # Test API
python scripts/dry_run.py             # 5-min dry run
python scripts/dry_run.py --duration 1800  # 30-min dry run

# Running
python -m src.main                    # Start bot

# Docker
docker-compose up -d                  # Start all
docker-compose logs -f bot            # View logs
docker-compose ps                     # Check status
docker-compose down                   # Stop all
```
