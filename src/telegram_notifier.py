"""Telegram notification module for stock alerts."""
import datetime
import os
from typing import Optional
import requests


def send_telegram(bot_token: str, chat_id: str, message: str, parse_mode: str = "Markdown"):
    """Send a message to Telegram via bot using synchronous requests.

    Args:
        bot_token: Telegram bot token from BotFather
        chat_id: Telegram chat ID (user, group, or channel)
        message: Message content to send
        parse_mode: Message formatting (Markdown, HTML, or None)

    Note:
        Failures are logged but do not raise exceptions to prevent
        disrupting the scanning loop.
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"[{datetime.datetime.now()}] Telegram send failed: {exc}")
    except Exception as exc:
        print(f"[{datetime.datetime.now()}] Telegram error: {exc}")


def format_telegram_alert(stock: str, scan_url: str, scan_name: Optional[str] = None) -> str:
    """Format a stock alert message for Telegram.

    Args:
        stock: Stock symbol/name
        scan_url: URL to the Chartink scan (not included in message)
        scan_name: Name/label for the scan (e.g., "EMA scan")

    Returns:
        Formatted alert message string with Markdown formatting
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_label = f" *[{scan_name}]*" if scan_name else ""
    
    # Telegram Markdown formatting (without scan URL)
    return (
        f"📈 *New Stock Listed*{scan_label}\n"
        f"💰 Stock: *{stock}*\n"
        f"⏰ Time: `{timestamp}`"
    )
