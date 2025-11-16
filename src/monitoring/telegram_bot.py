"""Telegram bot for notifications and alerts."""

import logging
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot
from telegram.error import TelegramError

from ..config import get_settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification manager with async support."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (uses settings if None)
            chat_id: Telegram chat ID (uses settings if None)
        """
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.enabled = settings.telegram_enabled

        if not self.enabled:
            logger.warning("Telegram notifications disabled (missing credentials)")
            self.bot = None
        else:
            self.bot = Bot(token=self.bot_token)
            self._loop = None
            self._executor = ThreadPoolExecutor(max_workers=1)
            logger.info("Telegram notifier initialized")

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop for async operations.

        Returns:
            Event loop
        """
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to submit to it differently
                return loop
            return loop
        except RuntimeError:
            # No event loop in current thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send a message via Telegram (sync interface).

        Args:
            message: Message text
            parse_mode: Parse mode (Markdown or HTML)

        Returns:
            True if successful
        """
        if not self.enabled or not self.bot:
            logger.debug(f"Telegram disabled, would send: {message}")
            return False

        try:
            # Check if we're in an async context (running loop in current thread)
            try:
                asyncio.get_running_loop()
                # We're in a running loop - can't use run_until_complete
                # Use asyncio.run in a thread instead
                import threading
                result = [False]
                exception = [None]

                def run_in_thread():
                    try:
                        # Create a new event loop for this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(
                                self.send_message_async(message, parse_mode)
                            )
                            result[0] = True
                        finally:
                            new_loop.close()
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=10)

                if exception[0]:
                    raise exception[0]

                return result[0]

            except RuntimeError:
                # No running loop in current thread - we can use run_until_complete
                # Create a fresh loop to avoid conflicts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.send_message_async(message, parse_mode)
                    )
                    return True
                finally:
                    loop.close()

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def send_message_async(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send a message via Telegram (async interface).

        Args:
            message: Message text
            parse_mode: Parse mode (Markdown or HTML)

        Returns:
            True if successful
        """
        if not self.enabled or not self.bot:
            logger.debug(f"Telegram disabled, would send: {message}")
            return False

        try:
            async with self.bot:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    read_timeout=10,
                    write_timeout=10,
                    connect_timeout=10
                )
            return True
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def alert_trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy: str = "Unknown"
    ):
        """Send trade execution alert.

        Args:
            symbol: Trading pair
            side: Order side (BUY/SELL)
            quantity: Quantity traded
            price: Execution price
            strategy: Strategy name
        """
        icon = "🟢" if side == "BUY" else "🔴"
        message = (
            f"{icon} *Trade Executed*\n\n"
            f"*Symbol:* {symbol}\n"
            f"*Side:* {side}\n"
            f"*Quantity:* {quantity:.6f}\n"
            f"*Price:* ${price:.2f}\n"
            f"*Strategy:* {strategy}\n"
            f"*Total:* ${quantity * price:.2f}"
        )
        self.send_message(message)

    def alert_order_placed(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None
    ):
        """Send order placement alert.

        Args:
            symbol: Trading pair
            side: Order side
            order_type: Order type
            quantity: Quantity
            price: Order price (if limit)
        """
        message = (
            f"📝 *Order Placed*\n\n"
            f"*Symbol:* {symbol}\n"
            f"*Side:* {side}\n"
            f"*Type:* {order_type}\n"
            f"*Quantity:* {quantity:.6f}\n"
        )

        if price:
            message += f"*Price:* ${price:.2f}\n"

        self.send_message(message)

    def alert_circuit_breaker(self, reason: str):
        """Send circuit breaker alert.

        Args:
            reason: Reason for activation
        """
        message = (
            f"🚨 *CIRCUIT BREAKER ACTIVATED*\n\n"
            f"Trading has been halted!\n\n"
            f"*Reason:* {reason}\n\n"
            f"Please review and manually reset if appropriate."
        )
        self.send_message(message)

    def alert_daily_summary(
        self,
        total_trades: int,
        pnl: float,
        win_rate: float,
        positions_count: int
    ):
        """Send daily summary.

        Args:
            total_trades: Number of trades
            pnl: Total PnL
            win_rate: Win rate percentage
            positions_count: Number of open positions
        """
        pnl_icon = "📈" if pnl >= 0 else "📉"
        message = (
            f"📊 *Daily Summary*\n\n"
            f"*Trades:* {total_trades}\n"
            f"{pnl_icon} *PnL:* ${pnl:.2f}\n"
            f"*Win Rate:* {win_rate:.1f}%\n"
            f"*Open Positions:* {positions_count}"
        )
        self.send_message(message)

    def alert_error(self, error_type: str, error_message: str):
        """Send error alert.

        Args:
            error_type: Type of error
            error_message: Error message
        """
        message = (
            f"⚠️ *Error Alert*\n\n"
            f"*Type:* {error_type}\n"
            f"*Message:* {error_message}"
        )
        self.send_message(message)

    def alert_position_opened(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        strategy: str = "Unknown"
    ):
        """Send position opened alert.

        Args:
            symbol: Trading pair
            side: Position side
            quantity: Position size
            entry_price: Entry price
            strategy: Strategy name
        """
        message = (
            f"🎯 *Position Opened*\n\n"
            f"*Symbol:* {symbol}\n"
            f"*Side:* {side}\n"
            f"*Quantity:* {quantity:.6f}\n"
            f"*Entry Price:* ${entry_price:.2f}\n"
            f"*Strategy:* {strategy}\n"
            f"*Position Value:* ${quantity * entry_price:.2f}"
        )
        self.send_message(message)

    def alert_position_closed(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percent: float
    ):
        """Send position closed alert.

        Args:
            symbol: Trading pair
            quantity: Position size
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/Loss
            pnl_percent: PnL percentage
        """
        pnl_icon = "✅" if pnl >= 0 else "❌"
        message = (
            f"{pnl_icon} *Position Closed*\n\n"
            f"*Symbol:* {symbol}\n"
            f"*Quantity:* {quantity:.6f}\n"
            f"*Entry:* ${entry_price:.2f}\n"
            f"*Exit:* ${exit_price:.2f}\n"
            f"*PnL:* ${pnl:.2f} ({pnl_percent:+.2f}%)"
        )
        self.send_message(message)

    def alert_risk_warning(self, warning_type: str, details: str):
        """Send risk warning alert.

        Args:
            warning_type: Type of warning
            details: Warning details
        """
        message = (
            f"⚠️ *Risk Warning*\n\n"
            f"*Type:* {warning_type}\n"
            f"*Details:* {details}"
        )
        self.send_message(message)

    def alert_system_status(self, status: str, message_text: str = ""):
        """Send system status alert.

        Args:
            status: Status (started, stopped, error)
            message_text: Additional message
        """
        icons = {
            "started": "🚀",
            "stopped": "🛑",
            "error": "💥",
            "healthy": "✅"
        }

        icon = icons.get(status.lower(), "ℹ️")
        message = f"{icon} *System {status.title()}*\n"

        if message_text:
            message += f"\n{message_text}"

        self.send_message(message)

    # Enhanced Visualizations

    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Create a visual progress bar.

        Args:
            percentage: Percentage value (0-100)
            length: Length of the bar

        Returns:
            Progress bar string
        """
        filled = int((percentage / 100) * length)
        empty = length - filled
        return "█" * filled + "░" * empty

    def _create_sparkline(self, values: list, height: int = 8) -> str:
        """Create a sparkline chart from values.

        Args:
            values: List of numeric values
            height: Height of sparkline (max 8)

        Returns:
            Sparkline string
        """
        if not values:
            return ""

        # Normalize values to 0-7 range
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        bars = "▁▂▃▄▅▆▇█"
        sparkline = ""

        for value in values:
            normalized = int(((value - min_val) / range_val) * 7)
            sparkline += bars[normalized]

        return sparkline

    def send_portfolio_status(self, portfolio_data: dict):
        """Send detailed portfolio status with visualization.

        Args:
            portfolio_data: Dictionary with portfolio information
                {
                    'total_value': float,
                    'total_pnl': float,
                    'pnl_percent': float,
                    'positions': list of position dicts,
                    'daily_pnl': float,
                    'daily_trades': int,
                    'win_rate': float
                }
        """
        total_value = portfolio_data.get('total_value', 0)
        total_pnl = portfolio_data.get('total_pnl', 0)
        pnl_percent = portfolio_data.get('pnl_percent', 0)
        daily_pnl = portfolio_data.get('daily_pnl', 0)
        daily_trades = portfolio_data.get('daily_trades', 0)
        win_rate = portfolio_data.get('win_rate', 0)

        # Header
        pnl_icon = "📈" if total_pnl >= 0 else "📉"
        message = f"{pnl_icon} *Portfolio Status*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        # Total value and PnL
        message += f"💰 *Total Value:* ${total_value:,.2f}\n"

        pnl_sign = "+" if total_pnl >= 0 else ""
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        message += f"{pnl_emoji} *Total PnL:* {pnl_sign}${total_pnl:,.2f} ({pnl_percent:+.2f}%)\n"

        # PnL progress bar
        pnl_bar = self._create_progress_bar(abs(pnl_percent) if abs(pnl_percent) <= 100 else 100)
        message += f"`{pnl_bar}` {abs(pnl_percent):.1f}%\n\n"

        # Daily stats
        message += "📊 *Today's Performance*\n"
        daily_pnl_emoji = "🟢" if daily_pnl >= 0 else "🔴"
        message += f"{daily_pnl_emoji} PnL: ${daily_pnl:+,.2f}\n"
        message += f"📝 Trades: {daily_trades}\n"
        message += f"🎯 Win Rate: {win_rate:.1f}%\n\n"

        # Positions
        positions = portfolio_data.get('positions', [])
        if positions:
            message += "💼 *Open Positions*\n"
            message += "━━━━━━━━━━━━━━━━━━━\n"

            for pos in positions[:5]:  # Show top 5 positions
                symbol = pos.get('symbol', 'Unknown')
                qty = pos.get('quantity', 0)
                entry = pos.get('entry_price', 0)
                current = pos.get('current_price', 0)
                pos_pnl = pos.get('pnl', 0)
                pos_pnl_pct = pos.get('pnl_percent', 0)

                pos_emoji = "🟢" if pos_pnl >= 0 else "🔴"
                message += f"\n{pos_emoji} *{symbol}*\n"
                message += f"  Qty: {qty:.6f} @ ${entry:.2f}\n"
                message += f"  Now: ${current:.2f} ({pos_pnl_pct:+.2f}%)\n"

            if len(positions) > 5:
                message += f"\n_...and {len(positions) - 5} more positions_\n"

        self.send_message(message)

    def send_trade_summary(self, trade_data: dict):
        """Send visually enhanced trade summary.

        Args:
            trade_data: Dictionary with trade information
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'exit_price': float,
                    'quantity': float,
                    'pnl': float,
                    'pnl_percent': float,
                    'duration': str,
                    'strategy': str
                }
        """
        symbol = trade_data.get('symbol', 'Unknown')
        side = trade_data.get('side', 'BUY')
        entry = trade_data.get('entry_price', 0)
        exit_price = trade_data.get('exit_price', 0)
        qty = trade_data.get('quantity', 0)
        pnl = trade_data.get('pnl', 0)
        pnl_pct = trade_data.get('pnl_percent', 0)
        duration = trade_data.get('duration', 'Unknown')
        strategy = trade_data.get('strategy', 'Unknown')

        # Determine icons and colors
        if pnl > 0:
            icon = "✅"
            trend = "🚀"
            result = "PROFIT"
        elif pnl < 0:
            icon = "❌"
            trend = "📉"
            result = "LOSS"
        else:
            icon = "⚪"
            trend = "➡️"
            result = "BREAK-EVEN"

        message = f"{icon} *Trade Completed - {result}*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        # Trade info
        message += f"📊 *Symbol:* {symbol}\n"
        message += f"📍 *Side:* {side}\n"
        message += f"🎯 *Strategy:* {strategy}\n\n"

        # Price movement
        message += "💹 *Price Action*\n"
        message += f"  Entry:  ${entry:,.2f}\n"
        message += f"  Exit:   ${exit_price:,.2f}\n"

        price_change = ((exit_price - entry) / entry) * 100
        message += f"  {trend} {price_change:+.2f}%\n\n"

        # Results
        message += "💰 *Results*\n"
        message += f"  Quantity: {qty:.6f}\n"
        message += f"  PnL: ${pnl:+,.2f}\n"
        message += f"  Return: {pnl_pct:+.2f}%\n\n"

        # Performance bar
        bar_length = min(int(abs(pnl_pct)), 20)
        bar = "█" * bar_length
        message += f"`{bar}` {abs(pnl_pct):.2f}%\n\n"

        # Duration
        message += f"⏱ *Duration:* {duration}\n"

        self.send_message(message)

    def send_performance_chart(self, performance_data: dict):
        """Send performance chart with sparklines.

        Args:
            performance_data: Dictionary with performance metrics
                {
                    'pnl_history': list of daily PnL values,
                    'win_streak': int,
                    'loss_streak': int,
                    'best_trade': float,
                    'worst_trade': float,
                    'avg_win': float,
                    'avg_loss': float,
                    'total_trades': int,
                    'winning_trades': int,
                    'losing_trades': int
                }
        """
        pnl_history = performance_data.get('pnl_history', [])
        win_streak = performance_data.get('win_streak', 0)
        loss_streak = performance_data.get('loss_streak', 0)
        best_trade = performance_data.get('best_trade', 0)
        worst_trade = performance_data.get('worst_trade', 0)
        avg_win = performance_data.get('avg_win', 0)
        avg_loss = performance_data.get('avg_loss', 0)
        total_trades = performance_data.get('total_trades', 0)
        winning_trades = performance_data.get('winning_trades', 0)
        losing_trades = performance_data.get('losing_trades', 0)

        message = "📈 *Performance Analytics*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        # PnL trend
        if pnl_history:
            sparkline = self._create_sparkline(pnl_history)
            total_pnl = sum(pnl_history)
            avg_pnl = total_pnl / len(pnl_history) if pnl_history else 0

            message += "💹 *PnL Trend (7 days)*\n"
            message += f"`{sparkline}`\n"
            message += f"Avg: ${avg_pnl:+.2f} | Total: ${total_pnl:+.2f}\n\n"

        # Win rate visualization
        if total_trades > 0:
            win_rate = (winning_trades / total_trades) * 100
            win_bar = self._create_progress_bar(win_rate)

            message += "🎯 *Win Rate*\n"
            message += f"`{win_bar}` {win_rate:.1f}%\n"
            message += f"Wins: {winning_trades} | Losses: {losing_trades}\n\n"

        # Streaks
        message += "🔥 *Streaks*\n"
        if win_streak > 0:
            message += f"  ✅ Win Streak: {win_streak}\n"
        if loss_streak > 0:
            message += f"  ❌ Loss Streak: {loss_streak}\n"
        message += "\n"

        # Best/Worst
        message += "📊 *Trade Statistics*\n"
        message += f"  🏆 Best: ${best_trade:+.2f}\n"
        message += f"  💔 Worst: ${worst_trade:+.2f}\n"
        message += f"  ✅ Avg Win: ${avg_win:.2f}\n"
        message += f"  ❌ Avg Loss: ${avg_loss:.2f}\n"

        # Risk/Reward ratio
        if avg_loss != 0:
            rr_ratio = abs(avg_win / avg_loss)
            message += f"  ⚖️ R:R Ratio: {rr_ratio:.2f}:1\n"

        self.send_message(message)

    def send_market_overview(self, market_data: dict):
        """Send market overview with price trends.

        Args:
            market_data: Dictionary with market information
                {
                    'symbols': list of symbol dicts with price, change, volume
                }
        """
        message = "🌐 *Market Overview*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        symbols = market_data.get('symbols', [])

        for sym_data in symbols:
            symbol = sym_data.get('symbol', 'Unknown')
            price = sym_data.get('price', 0)
            change = sym_data.get('change_24h', 0)
            volume = sym_data.get('volume_24h', 0)

            # Trend indicator
            if change > 2:
                trend = "🚀"
            elif change > 0:
                trend = "📈"
            elif change < -2:
                trend = "💥"
            elif change < 0:
                trend = "📉"
            else:
                trend = "➡️"

            message += f"{trend} *{symbol}*\n"
            message += f"  ${price:,.2f} ({change:+.2f}%)\n"
            message += f"  Vol: ${volume/1000000:.1f}M\n\n"

        self.send_message(message)

    def send_risk_dashboard(self, risk_data: dict):
        """Send risk management dashboard.

        Args:
            risk_data: Dictionary with risk metrics
                {
                    'total_exposure': float,
                    'max_exposure': float,
                    'daily_loss': float,
                    'max_daily_loss': float,
                    'positions_count': int,
                    'circuit_breaker_active': bool
                }
        """
        total_exp = risk_data.get('total_exposure', 0)
        max_exp = risk_data.get('max_exposure', 5000)
        daily_loss = risk_data.get('daily_loss', 0)
        max_daily = risk_data.get('max_daily_loss', 200)
        positions = risk_data.get('positions_count', 0)
        cb_active = risk_data.get('circuit_breaker_active', False)

        # Calculate percentages
        exp_pct = (total_exp / max_exp) * 100 if max_exp > 0 else 0
        loss_pct = (daily_loss / max_daily) * 100 if max_daily > 0 else 0

        message = "🛡️ *Risk Dashboard*\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        # Exposure
        exp_bar = self._create_progress_bar(exp_pct)
        exp_status = "🟢" if exp_pct < 70 else "🟡" if exp_pct < 90 else "🔴"
        message += f"{exp_status} *Total Exposure*\n"
        message += f"`{exp_bar}` {exp_pct:.1f}%\n"
        message += f"${total_exp:,.2f} / ${max_exp:,.2f}\n\n"

        # Daily Loss
        loss_bar = self._create_progress_bar(loss_pct)
        loss_status = "🟢" if loss_pct < 50 else "🟡" if loss_pct < 80 else "🔴"
        message += f"{loss_status} *Daily Loss*\n"
        message += f"`{loss_bar}` {loss_pct:.1f}%\n"
        message += f"${daily_loss:,.2f} / ${max_daily:,.2f}\n\n"

        # Positions
        message += f"📊 *Open Positions:* {positions}\n\n"

        # Circuit breaker
        cb_icon = "🚨" if cb_active else "✅"
        cb_text = "ACTIVE" if cb_active else "Standby"
        message += f"{cb_icon} *Circuit Breaker:* {cb_text}\n"

        # Risk level
        overall_risk = max(exp_pct, loss_pct)
        if overall_risk < 50:
            risk_level = "🟢 LOW"
        elif overall_risk < 75:
            risk_level = "🟡 MEDIUM"
        else:
            risk_level = "🔴 HIGH"

        message += f"\n⚠️ *Risk Level:* {risk_level}"

        self.send_message(message)
