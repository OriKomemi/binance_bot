"""Telegram bot for notifications and alerts."""

import logging
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
import asyncio

from ..config import get_settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification manager."""

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
            logger.info("Telegram notifier initialized")

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send a message via Telegram.

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
            # Run async send in sync context
            asyncio.run(self._send_async(message, parse_mode))
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def _send_async(self, message: str, parse_mode: str):
        """Send message asynchronously.

        Args:
            message: Message text
            parse_mode: Parse mode
        """
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode=parse_mode
        )

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
