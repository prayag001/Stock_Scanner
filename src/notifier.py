"""Discord notification module for stock alerts."""
import datetime
import os

import requests


def send_discord(webhook_url: str, message: str):
    """Send a message to Discord via webhook.

    Args:
        webhook_url: Discord webhook URL
        message: Message content to send

    Note:
        Failures are logged but do not raise exceptions to prevent
        disrupting the scanning loop.
    """
    # Optional mention configuration via environment variables:
    # - MENTION_ROLE_ID: a Discord role ID to mention (e.g., 123456789012345678)
    # - MENTION_USER_ID: a Discord user ID to mention
    # - PING_HERE: 'true' to include @here (parsed under 'everyone')
    role_id = os.getenv("MENTION_ROLE_ID")
    user_id = os.getenv("MENTION_USER_ID")
    ping_here = os.getenv("PING_HERE", "false").lower() in ("1", "true", "yes")

    prefixes = []
    if ping_here:
        prefixes.append("@here")
    if role_id:
        prefixes.append(f"<@&{role_id}>")
    if user_id:
        prefixes.append(f"<@{user_id}>")

    content = (" ".join(prefixes) + " " if prefixes else "") + message

    allowed_mentions = {"parse": []}
    if ping_here:
        # 'everyone' enables both @everyone and @here parsing
        allowed_mentions["parse"].append("everyone")
    if role_id:
        allowed_mentions["roles"] = [role_id]
    if user_id:
        allowed_mentions["users"] = [user_id]

    payload = {
        "content": content,
        "allowed_mentions": allowed_mentions,
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        # Optional logging; avoid crashing the job on transient network issues
        print(f"[{datetime.datetime.now()}] Discord send failed: {exc}")


def format_stock_alert(stock: str, _scan_url: str, scan_name: str = None) -> str:
    """Format a stock alert message for Discord.

    Args:
        stock: Stock symbol/name
        _scan_url: URL of the Chartink scan (not used in message)
        scan_name: Name/label for the scan (e.g., "EMA scan", "BB Scalping Scan")

    Returns:
        Formatted alert message string
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_label = f" [{scan_name}]" if scan_name else ""
    return (
        f"📈 New Stock Listed{scan_label}: **{stock}**\n"
        f"⏰ {timestamp}"
    )
