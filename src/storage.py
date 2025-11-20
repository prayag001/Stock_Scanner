"""Persistent storage module for tracking seen stocks."""
import json
from pathlib import Path

DEFAULT_PATH = Path("seen_stocks.json")


def load_seen(path: Path = DEFAULT_PATH) -> set:
    """Load previously seen stock symbols from JSON file.

    Args:
        path: Path to the JSON file containing seen stocks

    Returns:
        Set of stock symbols that have been seen before
    """
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return set(data)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to load seen stocks: {exc}")
        return set()


def save_seen(stocks: set, path: Path = DEFAULT_PATH):
    """Save seen stock symbols to JSON file.

    Args:
        stocks: Set of stock symbols to save
        path: Path to the JSON file to save to
    """
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(sorted(list(stocks)), file, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"Failed to save seen stocks: {exc}")
