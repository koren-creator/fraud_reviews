"""Helper utilities for data extraction and processing"""
import re
from datetime import datetime
from typing import Dict, Any


def clean_text(text: str) -> str:
    """
    Clean and normalize text

    - Remove extra whitespace
    - Strip leading/trailing spaces
    - Normalize unicode
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\\s+', ' ', text)

    # Strip
    text = text.strip()

    return text


def extract_number_from_text(text: str) -> int:
    """
    Extract first number from text

    Examples:
        "123 reviews" -> 123
        "4.5 stars" -> 4
        "1,234 followers" -> 1234
    """
    if not text:
        return 0

    # Remove commas
    text = text.replace(',', '')

    # Find first number
    match = re.search(r'(\\d+)', text)
    if match:
        return int(match.group(1))

    return 0


def is_hebrew_text(text: str) -> bool:
    """
    Check if text is primarily Hebrew

    Hebrew Unicode range: U+0590 to U+05FF
    """
    if not text:
        return False

    hebrew_chars = sum(1 for c in text if '\\u0590' <= c <= '\\u05FF')
    total_chars = len(text)

    if total_chars == 0:
        return False

    return (hebrew_chars / total_chars) > 0.3


def normalize_business_name(name: str) -> str:
    """
    Normalize business name for comparison/caching

    - Lowercase
    - Remove special characters
    - Strip extra spaces
    """
    if not name:
        return ""

    name = name.lower()
    name = re.sub(r'[^a-z0-9\\s]', '', name)
    name = re.sub(r'\\s+', ' ', name)
    name = name.strip()

    return name


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display"""
    if not dt:
        return ""

    return dt.strftime('%Y-%m-%d %H:%M:%S')


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
