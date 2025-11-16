"""Telegram bot command handler for user queries."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..config import get_settings

logger = logging.getLogger(__name__)


class TelegramCommandBot:
    """Telegram bot with command handlers for interactive queries."""

    def __init__(self, database=None, executor=None, risk_manager=None, data_client=None):
        """Initialize Telegram command bot.

        Args:
            database: Database instance for querying positions/trades
            executor: OrderExecutor instance for syncing/executing
            risk_manager: RiskManager instance for risk metrics
            data_client: BinanceDataClient for market data
        """
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = settings.telegram_enabled

        # Store component references
        self.db = database
        self.executor = executor
        self.risk_manager = risk_manager
        self.data_client = data_client

        # Application instance
        self.application = None
        self.is_running = False

        if not self.enabled:
            logger.warning("Telegram commands disabled (missing credentials)")
        else:
            logger.info("Telegram command bot initialized")

    async def start(self):
        """Start the Telegram bot."""
        if not self.enabled:
            logger.warning("Cannot start Telegram bot - not enabled")
            return

        # Build application
        self.application = Application.builder().token(self.bot_token).build()

        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("pnl", self.cmd_pnl))
        self.application.add_handler(CommandHandler("risk", self.cmd_risk))
        self.application.add_handler(CommandHandler("trades", self.cmd_trades))
        self.application.add_handler(CommandHandler("sync", self.cmd_sync))
        self.application.add_handler(CommandHandler("price", self.cmd_price))
        self.application.add_handler(CommandHandler("market", self.cmd_market))

        # Start polling
        logger.info("Starting Telegram bot polling...")
        self.is_running = True
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Stop the Telegram bot."""
        if self.application and self.is_running:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.is_running = False
            logger.info("Telegram bot stopped")

    # Command Handlers

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_msg = (
            "🤖 *Binance Trading Bot*\n\n"
            "Welcome! I can help you monitor your trading activity.\n\n"
            "Use /help to see available commands."
        )
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_msg = (
            "📚 *Available Commands:*\n\n"
            "*Portfolio & Positions:*\n"
            "/status - Portfolio status and summary\n"
            "/positions - List all open positions\n"
            "/balance - Account balances\n"
            "/pnl - Profit and loss summary\n\n"
            "*Risk Management:*\n"
            "/risk - Risk metrics and exposure\n\n"
            "*Trading Activity:*\n"
            "/trades - Recent trades\n"
            "/sync - Sync positions from exchange\n\n"
            "*Market Data:*\n"
            "/price <SYMBOL> - Get current price (e.g. /price BTCUSDT)\n"
            "/market - Market overview\n\n"
            "*Other:*\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_msg, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - portfolio status."""
        try:
            if not self.db:
                await update.message.reply_text("❌ Database not available")
                return

            # Get all open positions
            positions = self.db.get_all_positions(is_open=True)

            if not positions:
                await update.message.reply_text("📊 No open positions")
                return

            # Calculate portfolio metrics
            total_value = Decimal('0')
            total_pnl = Decimal('0')
            total_invested = Decimal('0')

            for pos in positions:
                if pos.quantity and pos.current_price and pos.entry_price:
                    position_value = pos.quantity * pos.current_price
                    invested = pos.quantity * pos.entry_price
                    pnl = position_value - invested

                    total_value += position_value
                    total_pnl += pnl
                    total_invested += invested

            pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else Decimal('0')

            # Get today's trades for daily stats
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_trades = self.db.get_trades(start_date=today_start, limit=1000)

            daily_pnl = sum(
                (trade.pnl or Decimal('0')) for trade in today_trades
            )

            # Format status message
            status_msg = (
                f"📊 *Portfolio Status*\n\n"
                f"💰 *Total Value:* ${total_value:,.2f}\n"
                f"📈 *Total PnL:* ${total_pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                f"📅 *Today's PnL:* ${daily_pnl:,.2f}\n"
                f"🏦 *Open Positions:* {len(positions)}\n"
                f"📝 *Today's Trades:* {len(today_trades)}\n\n"
                f"_Use /positions for detailed breakdown_"
            )

            await update.message.reply_text(status_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /status command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command - list all positions."""
        try:
            if not self.db:
                await update.message.reply_text("❌ Database not available")
                return

            positions = self.db.get_all_positions(is_open=True)

            if not positions:
                await update.message.reply_text("📊 No open positions")
                return

            # Build positions message
            msg_lines = ["📊 *Open Positions:*\n"]

            for pos in positions:
                if pos.quantity and pos.current_price and pos.entry_price:
                    pnl = (pos.current_price - pos.entry_price) * pos.quantity
                    pnl_pct = (pos.current_price - pos.entry_price) / pos.entry_price * 100
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"

                    msg_lines.append(
                        f"\n*{pos.symbol}*\n"
                        f"  Qty: {pos.quantity}\n"
                        f"  Entry: ${pos.entry_price:,.2f}\n"
                        f"  Current: ${pos.current_price:,.2f}\n"
                        f"  {pnl_emoji} PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)"
                    )

            positions_msg = "\n".join(msg_lines)
            await update.message.reply_text(positions_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /positions command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command - show account balances."""
        try:
            if not self.executor:
                await update.message.reply_text("❌ Executor not available")
                return

            # Get account info from Binance
            account_info = self.executor.client.get_account()

            # Filter balances > 0
            balances = [
                b for b in account_info['balances']
                if float(b['free']) > 0 or float(b['locked']) > 0
            ]

            if not balances:
                await update.message.reply_text("💰 No balances found")
                return

            # Build balance message
            msg_lines = ["💰 *Account Balances:*\n"]

            for balance in balances[:20]:  # Limit to top 20
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked

                if total > 0.00000001:  # Filter dust
                    msg_lines.append(
                        f"*{asset}:* {total:.8f}\n"
                        f"  Free: {free:.8f}, Locked: {locked:.8f}"
                    )

            if len(balances) > 20:
                msg_lines.append(f"\n_... and {len(balances) - 20} more_")

            balance_msg = "\n\n".join(msg_lines)
            await update.message.reply_text(balance_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /balance command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command - profit and loss summary."""
        try:
            if not self.db:
                await update.message.reply_text("❌ Database not available")
                return

            # Get PnL records for last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)

            pnl_records = self.db.get_pnl_records(
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )

            if not pnl_records:
                await update.message.reply_text("📈 No PnL records found")
                return

            # Calculate metrics
            total_pnl = sum(r.total_pnl or Decimal('0') for r in pnl_records)
            realized_pnl = sum(r.realized_pnl or Decimal('0') for r in pnl_records)
            unrealized_pnl = sum(r.unrealized_pnl or Decimal('0') for r in pnl_records)

            # Get today's PnL
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_pnl = sum(
                (r.total_pnl or Decimal('0'))
                for r in pnl_records
                if r.date and r.date >= today_start
            )

            # Format PnL message
            pnl_msg = (
                f"📈 *Profit & Loss Summary*\n\n"
                f"*Last 30 Days:*\n"
                f"Total PnL: ${total_pnl:,.2f}\n"
                f"Realized: ${realized_pnl:,.2f}\n"
                f"Unrealized: ${unrealized_pnl:,.2f}\n\n"
                f"*Today:*\n"
                f"PnL: ${today_pnl:,.2f}\n\n"
                f"_Records: {len(pnl_records)}_"
            )

            await update.message.reply_text(pnl_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /pnl command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command - risk metrics."""
        try:
            if not self.risk_manager:
                await update.message.reply_text("❌ Risk manager not available")
                return

            # Get risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics()

            # Calculate percentages
            exposure_pct = (
                risk_metrics.total_exposure_usd / risk_metrics.max_total_exposure_usd * 100
                if risk_metrics.max_total_exposure_usd > 0 else 0
            )

            daily_loss_pct = (
                risk_metrics.daily_loss_usd / risk_metrics.max_daily_loss_usd * 100
                if risk_metrics.max_daily_loss_usd > 0 else 0
            )

            # Status indicators
            cb_status = "🔴 ACTIVE" if risk_metrics.circuit_breaker_active else "🟢 INACTIVE"

            if exposure_pct < 50:
                exposure_status = "🟢"
            elif exposure_pct < 80:
                exposure_status = "🟡"
            else:
                exposure_status = "🔴"

            # Format risk message
            risk_msg = (
                f"🛡️ *Risk Dashboard*\n\n"
                f"*Exposure:*\n"
                f"{exposure_status} ${risk_metrics.total_exposure_usd:,.2f} / "
                f"${risk_metrics.max_total_exposure_usd:,.2f} ({exposure_pct:.1f}%)\n\n"
                f"*Daily Loss:*\n"
                f"${risk_metrics.daily_loss_usd:,.2f} / "
                f"${risk_metrics.max_daily_loss_usd:,.2f} ({daily_loss_pct:.1f}%)\n\n"
                f"*Circuit Breaker:* {cb_status}\n"
                f"*Open Positions:* {risk_metrics.positions_count}\n\n"
                f"_Max Position Size: ${risk_metrics.max_position_size_usd:,.2f}_"
            )

            if risk_metrics.circuit_breaker_active:
                risk_msg += f"\n\n⚠️ *Reason:* {risk_metrics.circuit_breaker_reason}"

            await update.message.reply_text(risk_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /risk command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command - recent trades."""
        try:
            if not self.db:
                await update.message.reply_text("❌ Database not available")
                return

            # Get recent trades
            trades = self.db.get_trades(limit=10)

            if not trades:
                await update.message.reply_text("📝 No trades found")
                return

            # Build trades message
            msg_lines = [f"📝 *Recent Trades* (last {len(trades)}):\n"]

            for trade in trades:
                side_emoji = "🟢" if trade.side.value == "BUY" else "🔴"
                pnl_str = f"${trade.pnl:,.2f}" if trade.pnl else "N/A"

                msg_lines.append(
                    f"\n{side_emoji} *{trade.symbol}* - {trade.side.value}\n"
                    f"  Qty: {trade.quantity}\n"
                    f"  Price: ${trade.price:,.2f}\n"
                    f"  PnL: {pnl_str}\n"
                    f"  Time: {trade.trade_time.strftime('%Y-%m-%d %H:%M')}"
                )

            trades_msg = "\n".join(msg_lines)
            await update.message.reply_text(trades_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /trades command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_sync(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sync command - sync positions from exchange."""
        try:
            if not self.executor:
                await update.message.reply_text("❌ Executor not available")
                return

            await update.message.reply_text("🔄 Syncing positions from exchange...")

            # Get trading pairs from settings
            settings = get_settings()
            sync_results = self.executor.sync_positions_from_exchange(
                trading_pairs=settings.trading_pairs_list
            )

            if 'error' in sync_results:
                await update.message.reply_text(f"❌ Sync failed: {sync_results['error']}")
                return

            # Format sync results
            sync_msg = (
                f"✅ *Position Sync Complete*\n\n"
                f"Synced: {sync_results['synced_count']}\n"
                f"Created: {sync_results['created_count']}\n"
                f"Updated: {sync_results['updated_count']}\n"
                f"Closed: {sync_results['closed_count']}\n"
                f"Discrepancies: {len(sync_results['discrepancies'])}"
            )

            if sync_results['discrepancies']:
                sync_msg += "\n\n⚠️ _Found discrepancies - check logs_"

            await update.message.reply_text(sync_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /sync command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command - get current price for a symbol."""
        try:
            if not self.executor:
                await update.message.reply_text("❌ Executor not available")
                return

            # Get symbol from command args
            if not context.args or len(context.args) == 0:
                await update.message.reply_text(
                    "Usage: /price <SYMBOL>\nExample: /price BTCUSDT"
                )
                return

            symbol = context.args[0].upper()

            # Get price
            ticker = self.executor.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])

            # Get 24h change
            ticker_24h = self.executor.client.get_ticker(symbol=symbol)
            change_24h = float(ticker_24h['priceChangePercent'])
            change_emoji = "🚀" if change_24h > 5 else "📈" if change_24h > 0 else "📉" if change_24h > -5 else "💥"

            price_msg = (
                f"💵 *{symbol}*\n\n"
                f"Price: ${price:,.2f}\n"
                f"{change_emoji} 24h Change: {change_24h:+.2f}%"
            )

            await update.message.reply_text(price_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /price command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /market command - market overview."""
        try:
            if not self.executor:
                await update.message.reply_text("❌ Executor not available")
                return

            settings = get_settings()
            msg_lines = ["🌐 *Market Overview:*\n"]

            for symbol in settings.trading_pairs_list:
                try:
                    ticker = self.executor.client.get_ticker(symbol=symbol)
                    price = float(ticker['lastPrice'])
                    change_24h = float(ticker['priceChangePercent'])
                    volume = float(ticker['quoteVolume'])

                    change_emoji = "🚀" if change_24h > 5 else "📈" if change_24h > 0 else "📉" if change_24h > -5 else "💥"

                    msg_lines.append(
                        f"\n*{symbol}*\n"
                        f"  ${price:,.2f} {change_emoji} {change_24h:+.2f}%\n"
                        f"  Vol: ${volume/1e6:.1f}M"
                    )
                except Exception as e:
                    logger.warning(f"Failed to get ticker for {symbol}: {e}")
                    continue

            market_msg = "\n".join(msg_lines)
            await update.message.reply_text(market_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /market command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
