# Telegram Setup Guide

## Getting Your Telegram Credentials

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "My Trading Bot")
   - Choose a username (must end in 'bot', e.g., "my_trading_bot")
4. **Save the bot token** - it looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 2: Get Your Chat ID

#### Option A: Using a Bot

1. Start a chat with your newly created bot
2. Send any message to your bot (e.g., "Hello")
3. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":` in the response
5. Your chat ID is the number after `"id":` (e.g., `123456789`)

#### Option B: Using @userinfobot

1. Search for **@userinfobot** in Telegram
2. Start a chat with it
3. Your user ID will be displayed (this is your chat_id)

### Step 3: Configure the Bot

Edit your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Step 4: Test Telegram Notifications

```bash
# Activate virtual environment
source venv/bin/activate

# Test sync mode (default)
python scripts/test_telegram.py

# Test async mode
python scripts/test_telegram.py --async
```

Expected output:
```
🔔 Testing Telegram Notifications

✅ Telegram notifier initialized
   Bot token: 1234567890...
   Chat ID: 123456789

1. Testing simple message...
   ✅ Message sent successfully

2. Testing trade alert...
   ✅ Trade alert sent

3. Testing system status alert...
   ✅ System status sent

4. Testing risk warning...
   ✅ Risk warning sent

🎉 All Telegram tests passed!
Check your Telegram chat for 4 messages
```

## Notification Types

The bot sends these types of notifications:

### 1. Trade Execution
```
🟢 Trade Executed

Symbol: BTCUSDT
Side: BUY
Quantity: 0.001000
Price: $43,500.00
Strategy: Grid Strategy
Total: $43.50
```

### 2. Order Placement
```
📝 Order Placed

Symbol: BTCUSDT
Side: BUY
Type: LIMIT
Quantity: 0.001000
Price: $43,000.00
```

### 3. Position Updates
```
🎯 Position Opened

Symbol: BTCUSDT
Side: LONG
Quantity: 0.001000
Entry Price: $43,500.00
Strategy: DCA Strategy
Position Value: $43.50
```

### 4. Circuit Breaker Alerts
```
🚨 CIRCUIT BREAKER ACTIVATED

Trading has been halted!

Reason: Daily loss limit exceeded

Please review and manually reset if appropriate.
```

### 5. Daily Summary
```
📊 Daily Summary

Trades: 15
📈 PnL: $125.50
Win Rate: 66.7%
Open Positions: 3
```

### 6. Error Alerts
```
⚠️ Error Alert

Type: API Error
Message: Rate limit exceeded
```

### 7. Risk Warnings
```
⚠️ Risk Warning

Type: High Exposure
Details: Total exposure at 85% of maximum
```

### 8. System Status
```
🚀 System Started

Trading bot initialized
Monitoring 3 pairs with 5 strategies
```

## Troubleshooting

### "Unauthorized" Error
- Check your bot token is correct
- Make sure you copied the entire token
- Verify no extra spaces in .env file

### "Chat not found" Error
- Verify your chat_id is correct
- Make sure you've started a chat with your bot
- Send at least one message to your bot first

### "No messages received"
- Check if bot token and chat_id are set correctly
- Verify Telegram is not blocking the bot
- Check firewall/network settings

### Messages Delayed
- This is normal for Telegram API
- Messages may take 1-2 seconds to arrive
- Check network connectivity

## Privacy & Security

### Best Practices
- **Keep your bot token secret** - don't share or commit to git
- **Use a private bot** - don't add to public groups
- **Limit chat_id access** - only your personal chat ID
- **Monitor bot activity** - review messages regularly

### Bot Permissions
Your bot only needs to:
- ✅ Send messages
- ❌ No need to read messages
- ❌ No need for admin rights
- ❌ No need for group permissions

## Advanced Configuration

### Rate Limiting
Telegram allows:
- 30 messages per second per chat
- 20 messages per minute to different chats

The bot automatically handles rate limiting.

### Message Formatting

#### Markdown (default)
```python
notifier.send_message(
    "*Bold* _Italic_ `Code` [Link](https://example.com)",
    parse_mode="Markdown"
)
```

#### HTML
```python
notifier.send_message(
    "<b>Bold</b> <i>Italic</i> <code>Code</code>",
    parse_mode="HTML"
)
```

### Disable Notifications
Set empty values in `.env`:
```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

The bot will continue running without Telegram notifications.

## Testing Checklist

- [ ] Bot created with @BotFather
- [ ] Bot token saved
- [ ] Chat ID obtained
- [ ] .env file configured
- [ ] Test script passes
- [ ] Messages received in Telegram
- [ ] All notification types tested
- [ ] No errors in logs

## Common Issues

### Issue: "telegram.error.NetworkError"
**Solution**: Check internet connection and firewall

### Issue: "asyncio RuntimeError"
**Solution**: Updated to use proper async handling (v20.7+)

### Issue: "Bot token invalid"
**Solution**: Regenerate token with @BotFather

### Issue: "Timeout error"
**Solution**: Increase timeout in code or check network

## Support

- Telegram Bot API Docs: https://core.telegram.org/bots/api
- python-telegram-bot Docs: https://docs.python-telegram-bot.org/
- Bot Father: @BotFather on Telegram

## Example: Testing from Command Line

```bash
# Quick test
python scripts/test_telegram.py

# Async test (more comprehensive)
python scripts/test_telegram.py --async

# Test from Python REPL
python
>>> from src.monitoring import TelegramNotifier
>>> notifier = TelegramNotifier()
>>> notifier.send_message("Test message!")
```
