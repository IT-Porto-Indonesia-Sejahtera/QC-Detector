"""
Fetch Logger Utility
====================
Simple logging system for database fetch operations.
Logs are stored in output/settings/fetch_log.txt
"""
import os
from datetime import datetime
from typing import List, Optional

# Log file path
LOG_FILE = os.path.join("output", "settings", "fetch_log.txt")

# Maximum log entries to keep (to prevent file from growing too large)
MAX_LOG_ENTRIES = 100


def _ensure_log_file():
    """Ensure the log file directory exists"""
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)


def log(message: str, level: str = "INFO") -> None:
    """
    Add a log entry with timestamp.
    
    Args:
        message: The log message
        level: Log level (INFO, SUCCESS, ERROR, WARNING)
    """
    _ensure_log_file()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}\n"
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        
        # Trim log if too large
        _trim_log_if_needed()
    except Exception as e:
        print(f"[FetchLogger] Failed to write log: {e}")


def log_success(message: str) -> None:
    """Log a success message"""
    log(message, "SUCCESS")


def log_error(message: str) -> None:
    """Log an error message"""
    log(message, "ERROR")


def log_info(message: str) -> None:
    """Log an info message"""
    log(message, "INFO")


def log_warning(message: str) -> None:
    """Log a warning message"""
    log(message, "WARNING")


def get_logs() -> str:
    """
    Read all log entries from the log file.
    
    Returns:
        String containing all log entries, or empty string if no logs
    """
    _ensure_log_file()
    
    if not os.path.exists(LOG_FILE):
        return ""
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading logs: {e}"


def get_log_lines() -> List[str]:
    """
    Read log entries as a list of lines.
    
    Returns:
        List of log entry lines
    """
    content = get_logs()
    if not content:
        return []
    return content.strip().split("\n")


def clear_logs() -> bool:
    """
    Clear all log entries.
    
    Returns:
        True if successful, False otherwise
    """
    _ensure_log_file()
    
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return True
    except Exception as e:
        print(f"[FetchLogger] Failed to clear logs: {e}")
        return False


def _trim_log_if_needed() -> None:
    """Trim log file to keep only the last MAX_LOG_ENTRIES entries"""
    try:
        lines = get_log_lines()
        if len(lines) > MAX_LOG_ENTRIES:
            # Keep only the last MAX_LOG_ENTRIES lines
            trimmed = lines[-MAX_LOG_ENTRIES:]
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(trimmed) + "\n")
    except Exception:
        pass  # Silently fail trimming


def get_log_stats() -> dict:
    """
    Get statistics about the log file.
    
    Returns:
        Dict with 'total_entries', 'success_count', 'error_count', 'last_entry'
    """
    lines = get_log_lines()
    
    success_count = sum(1 for line in lines if "[SUCCESS]" in line)
    error_count = sum(1 for line in lines if "[ERROR]" in line)
    
    return {
        "total_entries": len(lines),
        "success_count": success_count,
        "error_count": error_count,
        "last_entry": lines[-1] if lines else None
    }
