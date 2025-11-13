# Deployment Guide

## Production Deployment

### Server Requirements

**Minimum Specifications:**
- 2 CPU cores
- 4GB RAM
- 20GB SSD storage
- Ubuntu 20.04+ or similar Linux distribution
- Docker 20.10+
- Docker Compose 2.0+

**Recommended Specifications:**
- 4 CPU cores
- 8GB RAM
- 50GB SSD storage

### Step 1: Server Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd binance_bot

# Create environment file
cp .env.example .env
nano .env  # Edit with your configuration

# Create directories
mkdir -p logs data

# Pull and start containers
docker-compose pull
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f bot
```

### Step 3: Configure Binance API

1. **Create API Key**:
   - Log into Binance
   - Go to API Management
   - Create new API key
   - Save API Key and Secret securely

2. **Configure API Restrictions**:
   - Enable "Spot & Margin Trading"
   - Disable "Enable Withdrawals"
   - Disable "Enable Futures"
   - Add your server IP to whitelist

3. **Update .env file**:
```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=false  # Set to false for production
```

### Step 4: Configure Telegram Alerts (Optional)

1. **Create Telegram Bot**:
```bash
# Talk to @BotFather on Telegram
/newbot
# Follow instructions to create bot
# Save the bot token
```

2. **Get Chat ID**:
```bash
# Start a chat with your bot
# Send a message
# Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# Find your chat_id in the response
```

3. **Update .env**:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Step 5: Configure Monitoring

```bash
# Start with monitoring stack
docker-compose --profile monitoring up -d

# Access Grafana
# URL: http://your-server-ip:3000
# Default: admin/admin
```

## Security Configuration

### 1. Firewall Setup

```bash
# Install UFW
sudo apt-get install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow monitoring (only from trusted IPs)
sudo ufw allow from YOUR_IP to any port 3000  # Grafana
sudo ufw allow from YOUR_IP to any port 9090  # Prometheus

# Enable firewall
sudo ufw enable
```

### 2. SSL/TLS (Optional for web access)

```bash
# Install Nginx
sudo apt-get install nginx

# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Configure SSL
sudo certbot --nginx -d your-domain.com
```

### 3. Secure Environment Variables

```bash
# Set restrictive permissions
chmod 600 .env

# Never commit .env to version control
echo ".env" >> .gitignore
```

## Monitoring Setup

### Prometheus

Already configured in docker-compose.yml. Metrics available at:
- URL: http://localhost:9090
- Bot metrics: http://localhost:8000

### Grafana Dashboards

1. Access Grafana: http://localhost:3000
2. Add Prometheus data source:
   - URL: http://prometheus:9090
3. Import dashboards (coming soon)

### Telegram Alerts

The bot will send alerts for:
- Trade executions
- Circuit breaker activations
- Errors
- Daily summaries

## Backup Strategy

### 1. Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U bot_user binance_bot > backup_$DATE.sql
gzip backup_$DATE.sql
# Keep only last 7 days
find . -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * cd /path/to/binance_bot && ./backup.sh" | crontab -
```

### 2. Configuration Backup

```bash
# Backup configuration
tar -czf config_backup.tar.gz .env docker-compose.yml

# Copy to remote location
scp config_backup.tar.gz user@backup-server:/backups/
```

## Maintenance

### Update Bot

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f bot

# Last 100 lines
docker-compose logs --tail=100 bot

# Logs for specific service
docker-compose logs postgres
docker-compose logs redis
```

### Database Maintenance

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U bot_user binance_bot

# Common queries
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM trades;
SELECT symbol, SUM(total_pnl) FROM pnl_records GROUP BY symbol;

# Vacuum database (cleanup)
VACUUM ANALYZE;
```

### Redis Maintenance

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Check memory usage
INFO memory

# Clear cache (if needed)
FLUSHDB
```

## Troubleshooting

### Bot Won't Start

```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose logs bot

# Restart services
docker-compose restart

# Full restart
docker-compose down && docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready

# View PostgreSQL logs
docker-compose logs postgres
```

### Memory Issues

```bash
# Check resource usage
docker stats

# Increase memory limits in docker-compose.yml
# Add under bot service:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Clean old data
cd data && find . -name "*.parquet" -mtime +90 -delete
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_orders_symbol_created ON orders(symbol, created_at);
CREATE INDEX idx_trades_symbol_time ON trades(symbol, trade_time);
CREATE INDEX idx_pnl_date ON pnl_records(date);
```

### Redis Optimization

```bash
# Edit redis configuration
# Increase max memory
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Scaling

### Horizontal Scaling

For multiple trading pairs or strategies:

1. Run multiple bot instances
2. Assign different pairs to each instance
3. Use separate databases or schemas
4. Centralized monitoring

### High Availability

1. Use managed PostgreSQL (RDS, etc.)
2. Use managed Redis (ElastiCache, etc.)
3. Deploy bot across multiple regions
4. Implement health checks and auto-restart

## Production Checklist

- [ ] Server secured (firewall, SSH keys)
- [ ] Docker installed and configured
- [ ] Environment variables configured
- [ ] Binance API key created with restrictions
- [ ] Testnet testing completed
- [ ] Telegram alerts configured
- [ ] Monitoring setup (Prometheus + Grafana)
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Resource monitoring enabled
- [ ] Start with small position sizes
- [ ] Monitor for 48 hours before increasing exposure
