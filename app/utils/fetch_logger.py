"""
Fetch Logger Utility
====================
Simple logging system for database fetch operations.
Wrapper around project_utilities.logger_config.
"""
import os
from datetime import datetime
from typing import List, Optional
from project_utilities.logger_config import get_crash_logger, get_fetch_logger

# Import loggers
# We explicitly separate them: "Detection" logger for info/success, "Crash" logger for errors.
_crash_logger = get_crash_logger()
_detection_logger = get_fetch_logger()  # Renaming variable to minimize change, effectively pointing to fetch log

# Legacy constant for backward compatibility logic if needed
LOG_FILE = os.path.join("logs", "detections.log") 

def log(message: str, level: str = "INFO") -> None:
    """
    Log message to appropriate logger based on level.
    """
    if level == "ERROR":
        _crash_logger.error(message)
        # Also log to detection log for context? 
        # User asked for 2 separate ones. Usually you want errors in both.
        # But specifically asked for crashes separate. Let's keep strict separation or double log.
        # Let's double log to detection so the operational stream is complete.
        _detection_logger.error(message)
    elif level == "WARNING":
        _detection_logger.warning(message)
    else:
        _detection_logger.info(message)


def log_success(message: str) -> None:
    """Log a success message"""
    _detection_logger.info(f"[SUCCESS] {message}")


def log_error(message: str) -> None:
    """Log an error message"""
    _crash_logger.error(message)
    _detection_logger.error(message)


def log_info(message: str) -> None:
    """Log an info message"""
    _detection_logger.info(message)


def log_warning(message: str) -> None:
    """Log a warning message"""
    _detection_logger.warning(message)

# --- Legacy View/Clear Methods (Adapted for new file) ---
# Note: These are less reliable with rotating files but provided for simple UI compatibility

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
