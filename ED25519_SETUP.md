# Ed25519 Authentication Setup Guide

## Overview

Ed25519 is a more secure alternative to HMAC_SHA256 for authenticating Binance API requests. This guide shows you how to set it up.

## Benefits of Ed25519

✅ **More Secure**: Uses public-key cryptography
✅ **Better Protection**: Private key never transmitted
✅ **Industry Standard**: Used by SSH, Signal, and more
✅ **Recommended**: Binance recommends Ed25519 for production

## Step 1: Generate Ed25519 Key Pair

### Option A: Using Binance Testnet Dashboard

1. Visit: https://testnet.binance.vision/
2. Login with GitHub
3. Click **"Generate Ed25519 Key"** (instead of HMAC_SHA256)
4. Download the private key file (`.pem` format)
5. Save your API Key (shown on screen)

### Option B: Generate Locally (Advanced)

```bash
# Generate private key
openssl genpkey -algorithm ed25519 -out test-prv-key.pem

# Extract public key
openssl pkey -in test-prv-key.pem -pubout -out test-pub-key.pem

# View public key (you'll need to upload this to Binance)
cat test-pub-key.pem
```

Then upload the public key to Binance API settings.

## Step 2: Save Your Private Key

```bash
# Create a secure directory
mkdir -p ~/.binance_bot/keys
chmod 700 ~/.binance_bot/keys

# Move your private key there
mv ~/Downloads/test-prv-key.pem ~/.binance_bot/keys/
chmod 600 ~/.binance_bot/keys/test-prv-key.pem
```

## Step 3: Configure .env File

Edit your `.env` file:

```bash
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_TESTNET=true

# Ed25519 Authentication (recommended)
USE_ED25519=true
ED25519_PRIVATE_KEY_PATH=/home/user/.binance_bot/keys/test-prv-key.pem
ED25519_KEY_PASSWORD=  # Leave empty if key is not encrypted

# HMAC Secret (not needed when using Ed25519)
BINANCE_API_SECRET=
```

### If Your Key is Encrypted

If you encrypted your private key with a password:

```bash
ED25519_KEY_PASSWORD=your_key_password_here
```

## Step 4: Test Ed25519 Authentication

```bash
# Install cryptography library
pip install cryptography

# Test Ed25519 authentication
python scripts/test_ed25519.py
```

Expected output:
```
🔐 Testing Ed25519 Authentication

Initializing Ed25519 client...
✅ Client initialized

1. Testing ping...
   ✅ Ping successful

2. Getting server time...
   ✅ Server time: 2024-01-15 10:30:45

3. Getting BTC price...
   ✅ BTC Price: $43,500.00

4. Getting account info (signed request)...
   ✅ Account retrieved
   Balances: 150
   USDT Balance: 10000.00

5. Getting open orders...
   ✅ Open orders: 0

🎉 All Ed25519 authentication tests passed!
```

## Step 5: Update Bot to Use Ed25519

The bot will automatically use Ed25519 when `USE_ED25519=true` is set.

### For Testing:

```bash
# Run validation
python scripts/validate_setup.py

# Run dry run with Ed25519
python scripts/dry_run.py
```

### For Production:

```bash
# Start the bot
python -m src.main
```

## Security Best Practices

### 🔒 Protect Your Private Key

```bash
# Set strict permissions
chmod 600 ~/.binance_bot/keys/test-prv-key.pem

# Only you can read it
ls -la ~/.binance_bot/keys/test-prv-key.pem
# Should show: -rw------- (600)
```

### 🔒 Encrypt Your Private Key (Recommended)

```bash
# Encrypt with password
openssl pkey -in test-prv-key.pem -out encrypted-key.pem -aes256

# Then use encrypted key
ED25519_PRIVATE_KEY_PATH=/path/to/encrypted-key.pem
ED25519_KEY_PASSWORD=your_strong_password
```

### 🔒 Never Commit Private Keys

```bash
# Already in .gitignore
*.pem
*.key
keys/
```

### 🔒 Use Different Keys for Test/Production

```bash
# Testnet key
ED25519_PRIVATE_KEY_PATH=/keys/testnet-key.pem

# Production key (different file)
ED25519_PRIVATE_KEY_PATH=/keys/production-key.pem
```

## Troubleshooting

### "Private key file not found"

```bash
# Check file exists
ls -la ~/.binance_bot/keys/test-prv-key.pem

# Check path in .env is absolute
ED25519_PRIVATE_KEY_PATH=/home/user/.binance_bot/keys/test-prv-key.pem
# NOT: ./keys/test-prv-key.pem
```

### "Invalid key file"

```bash
# Verify it's a valid Ed25519 key
openssl pkey -in test-prv-key.pem -text -noout

# Should show:
# ED25519 Private-Key:
```

### "Permission denied"

```bash
# Fix permissions
chmod 600 /path/to/test-prv-key.pem
```

### "Signature verification failed"

- Check API key matches the public key uploaded to Binance
- Verify timestamp is within 5 seconds of server time
- Ensure key file hasn't been corrupted

## Example: Creating a Test Order with Ed25519

```python
from src.data.binance_ed25519_client import BinanceEd25519Client

# Initialize client
client = BinanceEd25519Client(
    api_key="your_api_key",
    private_key_path="/path/to/key.pem",
    testnet=True
)

# Create order (automatically signed with Ed25519)
order = client.create_order(
    symbol="BTCUSDT",
    side="BUY",
    order_type="LIMIT",
    quantity=0.001,
    price=40000.00,
    time_in_force="GTC"
)

print(f"Order placed: {order['orderId']}")
```

## Switching Back to HMAC (If Needed)

If you need to switch back to HMAC authentication:

```bash
# In .env
USE_ED25519=false
BINANCE_API_SECRET=your_hmac_secret_here
```

## FAQ

**Q: Can I use Ed25519 in production?**
A: Yes! It's recommended for production use.

**Q: Is Ed25519 required?**
A: No, HMAC still works. Ed25519 is optional but more secure.

**Q: Can I have both HMAC and Ed25519?**
A: Yes, but the bot will use Ed25519 when `USE_ED25519=true`.

**Q: What if I lose my private key?**
A: Generate a new key pair and update your Binance API settings.

**Q: Does testnet support Ed25519?**
A: Yes! Test there first before using in production.

## Resources

- Binance API Docs: https://binance-docs.github.io/apidocs/spot/en/#ed25519
- Ed25519 Info: https://ed25519.cr.yp.to/
- OpenSSL Ed25519: https://www.openssl.org/docs/man1.1.1/man1/genpkey.html

## Verification Checklist

- [ ] Ed25519 key pair generated
- [ ] Private key saved securely with correct permissions
- [ ] API key obtained from Binance
- [ ] .env configured with Ed25519 settings
- [ ] test_ed25519.py passes all tests
- [ ] Can retrieve account info
- [ ] Can place test orders
- [ ] Private key is backed up securely
- [ ] Production uses different key than testnet
