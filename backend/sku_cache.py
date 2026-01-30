"""
SKU Data Cache
==============
Persistent cache for fetched product SKU data.
Data is saved to a JSON file on successful fetch.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional

SKU_CACHE_FILE = os.path.join("output", "settings", "sku_cache.json")

_sku_cache: List[Dict[str, Any]] = []
_last_fetch: Optional[datetime.datetime] = None
_fetch_log: List[str] = []


def _ensure_dir():
    """Ensure output directory exists."""
    os.makedirs(os.path.dirname(SKU_CACHE_FILE), exist_ok=True)


def set_sku_data(data: List[Dict[str, Any]], save_to_file: bool = True) -> bool:
    """
    Store fetched SKU data in cache and optionally save to JSON file.
    
    Returns:
        True if save was successful, False otherwise.
    """
    global _sku_cache, _last_fetch
    _sku_cache = data
    _last_fetch = datetime.datetime.now()
    
    if save_to_file:
        try:
            _ensure_dir()
            cache_data = {
                "last_fetch": _last_fetch.isoformat(),
                "count": len(data),
                "products": data
            }
            with open(SKU_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            add_log(f"Saved {len(data)} SKU records to {SKU_CACHE_FILE}")
            return True
        except Exception as e:
            add_log(f"ERROR saving to file: {e}")
            return False
    
    add_log(f"Cached {len(data)} SKU records (memory only).")
    return True


def get_sku_data() -> List[Dict[str, Any]]:
    """Retrieve cached SKU data. Loads from file if memory cache is empty."""
    global _sku_cache
    if not _sku_cache:
        load_from_file()
    return _sku_cache


def load_from_file() -> bool:
    """Load SKU data from the JSON cache file."""
    global _sku_cache, _last_fetch
    try:
        if os.path.exists(SKU_CACHE_FILE):
            with open(SKU_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            _sku_cache = cache_data.get("products", [])
            last_fetch_str = cache_data.get("last_fetch")
            if last_fetch_str:
                _last_fetch = datetime.datetime.fromisoformat(last_fetch_str)
            add_log(f"Loaded {len(_sku_cache)} SKU records from file.")
            return True
    except Exception as e:
        add_log(f"ERROR loading from file: {e}")
    return False


def get_last_fetch_time() -> Optional[datetime.datetime]:
    """Get the timestamp of the last fetch."""
    return _last_fetch


def clear_cache() -> None:
    """Clear the SKU cache (memory only, does not delete file)."""
    global _sku_cache, _last_fetch
    _sku_cache = []
    _last_fetch = None
    add_log("Cache cleared (memory).")


def add_log(message: str) -> None:
    """Add a timestamped log message."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    _fetch_log.append(f"[{timestamp}] {message}")
    # Keep only last 50 messages
    if len(_fetch_log) > 50:
        _fetch_log.pop(0)


def get_logs() -> List[str]:
    """Get all log messages."""
    return _fetch_log


def get_sku_by_code(code: str) -> Optional[Dict[str, Any]]:
    """Look up full SKU details by product code."""
    data = get_sku_data()
    for p in data:
        if str(p.get("code", "")).strip().upper() == str(code).strip().upper():
            return p
    return None


def get_log_text() -> str:
    """Get logs as a single string for display."""
    return "\n".join(_fetch_log)
