# Telegram Bot Commands Guide

## Overview

The bot includes an **interactive Telegram command interface** that allows you to query information and control the bot via Telegram messages.

## Features

✅ Real-time portfolio status
✅ Position monitoring
✅ Account balances
✅ PnL tracking
✅ Risk metrics dashboard
✅ Recent trade history
✅ Position synchronization
✅ Market data queries

---

## Setup

### 1. Configure Telegram Bot

In your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_personal_chat_id
```

### 2. Start the Bot

When you start the trading bot, the Telegram command handler starts automatically:

```bash
python -m src.main
```

You'll see:
```
Starting Telegram command bot...
Telegram command bot thread started
```

### 3. Send Commands

Open Telegram and send commands to your bot!

---

## Available Commands

### 📊 Portfolio & Positions

#### `/status`
Get a comprehensive portfolio status summary.

**Returns:**
- Total portfolio value
- Total PnL (amount and percentage)
- Today's PnL
- Number of open positions
- Today's trade count

**Example:**
```
/status
```

**Response:**
```
📊 Portfolio Status

💰 Total Value: $10,500.00
📈 Total PnL: $500.00 (+5.00%)
📅 Today's PnL: $125.50
🏦 Open Positions: 3
📝 Today's Trades: 8

Use /positions for detailed breakdown
```

---

#### `/positions`
List all open positions with details.

**Returns:**
- Symbol
- Quantity
- Entry price
- Current price
- PnL (amount and percentage)

**Example:**
```
/positions
```

**Response:**
```
📊 Open Positions:

BTCUSDT
  Qty: 0.05
  Entry: $42,000.00
  Current: $43,500.00
  🟢 PnL: $75.00 (+3.57%)

ETHUSDT
  Qty: 1.5
  Entry: $2,200.00
  Current: $2,350.00
  🟢 PnL: $225.00 (+6.82%)
```

---

#### `/balance`
View all account balances from Binance.

**Returns:**
- Asset name
- Free balance
- Locked balance
- Total balance

**Example:**
```
/balance
```

**Response:**
```
💰 Account Balances:

USDT: 9500.00000000
  Free: 9500.00000000, Locked: 0.00000000

BTC: 0.05000000
  Free: 0.05000000, Locked: 0.00000000
```

---

#### `/pnl`
Profit and loss summary for the last 30 days.

**Returns:**
- Total PnL (30 days)
- Realized PnL
- Unrealized PnL
- Today's PnL

**Example:**
```
/pnl
```

**Response:**
```
📈 Profit & Loss Summary

Last 30 Days:
Total PnL: $1,250.00
Realized: $800.00
Unrealized: $450.00

Today:
PnL: $125.50

Records: 87
```

---

### 🛡️ Risk Management

#### `/risk`
View risk metrics and exposure levels.

**Returns:**
- Current exposure vs max allowed
- Daily loss vs max daily loss
- Circuit breaker status
- Open positions count
- Max position size

**Example:**
```
/risk
```

**Response:**
```
🛡️ Risk Dashboard

Exposure:
🟢 $3,500.00 / $5,000.00 (70.0%)

Daily Loss:
$75.00 / $200.00 (37.5%)

Circuit Breaker: 🟢 INACTIVE
Open Positions: 3

Max Position Size: $1,000.00
```

---

### 📝 Trading Activity

#### `/trades`
View the 10 most recent trades.

**Returns:**
- Symbol
- Side (BUY/SELL)
- Quantity
- Price
- PnL
- Timestamp

**Example:**
```
/trades
```

**Response:**
```
📝 Recent Trades (last 10):

🟢 BTCUSDT - BUY
  Qty: 0.05
  Price: $42,000.00
  PnL: $75.00
  Time: 2024-01-15 14:30

🔴 ETHUSDT - SELL
  Qty: 1.0
  Price: $2,350.00
  PnL: $150.00
  Time: 2024-01-15 13:45
```

---

#### `/sync`
Manually trigger position synchronization from Binance exchange.

**Returns:**
- Number of positions synced
- Positions created
- Positions updated
- Positions closed
- Discrepancies found

**Example:**
```
/sync
```

**Response:**
```
✅ Position Sync Complete

Synced: 3
Created: 0
Updated: 1
Closed: 0
Discrepancies: 1

⚠️ Found discrepancies - check logs
```

**Use Case:** Run this after making manual trades on Binance to update the bot's database.

---

### 💹 Market Data

#### `/price <SYMBOL>`
Get the current price for any trading pair.

**Arguments:**
- `SYMBOL` - Trading pair (e.g., BTCUSDT, ETHUSDT)

**Returns:**
- Current price
- 24-hour change percentage

**Example:**
```
/price BTCUSDT
```

**Response:**
```
💵 BTCUSDT

Price: $43,500.00
📈 24h Change: +2.50%
```

---

#### `/market`
Market overview for all configured trading pairs.

**Returns:**
- Current price
- 24-hour change
- 24-hour volume

**Example:**
```
/market
```

**Response:**
```
🌐 Market Overview:

BTCUSDT
  $43,500.00 📈 +2.50%
  Vol: $25,600.0M

ETHUSDT
  $2,350.00 📉 -1.20%
  Vol: $12,400.0M

BNBUSDT
  $305.00 📈 +0.80%
  Vol: $850.0M
```

---

### ℹ️ Help & Information

#### `/start`
Welcome message and introduction to the bot.

**Example:**
```
/start
```

**Response:**
```
🤖 Binance Trading Bot

Welcome! I can help you monitor your trading activity.

Use /help to see available commands.
```

---

#### `/help`
Show all available commands with descriptions.

**Example:**
```
/help
```

**Response:**
```
📚 Available Commands:

Portfolio & Positions:
/status - Portfolio status and summary
/positions - List all open positions
/balance - Account balances
/pnl - Profit and loss summary

Risk Management:
/risk - Risk metrics and exposure

Trading Activity:
/trades - Recent trades
/sync - Sync positions from exchange

Market Data:
/price <SYMBOL> - Get current price
/market - Market overview

Other:
/help - Show this help message
```

---

## Usage Tips

### Quick Status Check
```
/status
```
Get a quick overview of your portfolio performance.

### After Manual Trades
```
/sync
```
Always sync after making manual trades on Binance to keep the bot's database updated.

### Check Risk Before Trading
```
/risk
```
Review your exposure and risk metrics before placing large orders.

### Monitor Market Conditions
```
/market
```
Check overall market trends across your trading pairs.

### Track Performance
```
/pnl
```
Review your profit and loss to evaluate strategy performance.

---

## Error Handling

If a command fails, you'll receive an error message:

```
❌ Error: [error description]
```

Common errors:
- **Database not available** - Database connection issue
- **Executor not available** - Executor not initialized
- **Failed to get ticker** - Network or API issue
- **Invalid symbol** - Symbol not found on Binance

---

## Security Notes

🔒 **Important Security Considerations:**

1. **Keep your chat ID private** - Anyone with your chat ID can see bot responses
2. **Use a personal bot** - Don't share your bot token
3. **Monitor access** - Only you should be able to send commands
4. **Sensitive data** - Commands show balance and PnL information

### How to Verify Your Bot

1. Send `/start` - Only you should receive a response
2. Check bot username matches your bot
3. Verify chat ID in `.env` is correct

---

## Troubleshooting

### Bot doesn't respond

**Check:**
1. Bot token is correct in `.env`
2. Chat ID is your personal chat ID (not bot ID)
3. Bot is running: `python -m src.main`
4. Check logs for errors

**Get your chat ID:**
```
# Option 1: Use @userinfobot on Telegram
# Option 2: Send /start to your bot and check logs
```

### Commands return errors

**Check:**
1. Database is running (PostgreSQL)
2. Redis is running
3. Binance API credentials are valid
4. Network connection is stable

### Delayed responses

This is normal:
- Complex queries (like `/sync`) may take a few seconds
- Network latency to Binance API
- Database query time

---

## Advanced Usage

### Combining Commands

Monitor a position:
```
1. /price BTCUSDT    # Check current price
2. /positions        # See your position
3. /risk             # Check exposure
```

Daily routine:
```
1. /status           # Morning portfolio check
2. /market           # Market overview
3. /trades           # Review yesterday's trades
4. /pnl              # Check performance
```

Position management:
```
1. /balance          # Check available funds
2. /risk             # Verify risk limits
3. /positions        # Review current positions
4. /sync             # Sync after manual changes
```

---

## Integration with Trading Bot

The command bot runs **alongside** the trading bot:

- **Separate thread** - Commands don't interrupt trading
- **Real-time data** - Queries use live data
- **Shared database** - Same data as trading bot
- **Independent** - Trading bot works even if command bot fails

---

## Examples

### Daily Monitoring Workflow

**Morning:**
```
/status
/market
/risk
```

**After Trading:**
```
/trades
/positions
/pnl
```

**Before Manual Trade:**
```
/balance
/risk
/price BTCUSDT
```

**After Manual Trade:**
```
/sync
/positions
```

---

## Command Reference Quick Sheet

| Command | Purpose | Response Time |
|---------|---------|---------------|
| `/status` | Portfolio summary | Fast |
| `/positions` | List positions | Fast |
| `/balance` | Account balances | Medium |
| `/pnl` | PnL summary | Fast |
| `/risk` | Risk metrics | Fast |
| `/trades` | Recent trades | Fast |
| `/sync` | Sync positions | Slow (API calls) |
| `/price` | Get price | Medium |
| `/market` | Market overview | Medium |
| `/help` | Show commands | Instant |

---

## FAQ

**Q: Can I use commands while bot is trading?**
A: Yes! Commands don't interfere with trading operations.

**Q: Are commands secure?**
A: Yes, as long as you keep your bot token and chat ID private.

**Q: Can multiple people use the bot?**
A: Currently, the bot responds to the configured chat ID only.

**Q: What if I send an invalid command?**
A: The bot will ignore it. Use `/help` for valid commands.

**Q: How often can I send commands?**
A: No rate limit, but avoid spamming to prevent Telegram API limits.

**Q: Do commands work when bot is stopped?**
A: No, the bot must be running for commands to work.

---

## Related Documentation

- [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) - Initial bot setup
- [README_DETAILED.md](README_DETAILED.md) - Full bot documentation
- [TESTING.md](TESTING.md) - Testing guide

---

## Support

If you encounter issues:

1. Check logs: `tail -f logs/bot.log`
2. Verify configuration: `.env` file
3. Test connection: `/start` command
4. Review this guide for proper usage

Happy trading! 🚀
