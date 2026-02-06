"""
Fetch Logger Utility
====================
Simple logging system for database fetch operations.
Relies on project_utilities.logger_config for handlers (including Lark).
"""
import os
import traceback
from datetime import datetime
from typing import List, Optional
from project_utilities.logger_config import get_crash_logger, get_fetch_logger

# Import loggers
_crash_logger = get_crash_logger()
_detection_logger = get_fetch_logger()

def log_error(message: str, include_traceback: bool = True) -> None:
    """Log an error message. Lark notification is handled automatically by the base logger."""
    # We log to crash logger (which has the LarkLoggingHandler)
    _crash_logger.error(message, exc_info=include_traceback)
    # Also log to detection log for context
    _detection_logger.error(message)

def log_success(message: str) -> None:
    """Log a success message"""
    _detection_logger.info(f"[SUCCESS] {message}")

def log_info(message: str) -> None:
    """Log an info message"""
    _detection_logger.info(message)

def log_warning(message: str) -> None:
    """Log a warning message. Lark notification handled by base logger."""
    _detection_logger.warning(message)

# --- Legacy View/Clear Methods (Required for UI) ---

def get_logs() -> str:
    """Read current detection log file"""
    log_path = os.path.join("logs", "detections.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "Error reading log file."
    return ""

def get_log_lines() -> List[str]:
    content = get_logs()
    return content.split('\n') if content else []

def clear_logs() -> bool:
    # Basic clearing of the CURRENT active log file
    log_path = os.path.join("logs", "detections.log")
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("")
        return True
    except:
        return False

def get_log_stats() -> dict:
    lines = get_log_lines()
    success = sum(1 for line in lines if "SUCCESS" in line)
    error = sum(1 for line in lines if "ERROR" in line)
    return {
        "total_entries": len(lines),
        "success_count": success,
        "error_count": error,
        "last_entry": lines[-1] if lines else None
    }
