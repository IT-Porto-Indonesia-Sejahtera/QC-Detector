"""
Logger Config
=============
Centralized logging configuration for the QC-Detector application.
Provides configured loggers for:
1. Crashes: Rotated daily, kept for 30 days.
2. Detections: Rotated by size (100MB), max 1GB total.
"""

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Base log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Logger names
CRASH_LOGGER_NAME = 'qc_crash_logger'
DETECTION_LOGGER_NAME = 'qc_detection_logger'

def setup_crash_logger():
    """
    Setup logger for application crashes/errors.
    Policy: Daily rotation, keep 30 days.
    """
    logger = logging.getLogger(CRASH_LOGGER_NAME)
    logger.setLevel(logging.ERROR)
    
    if not logger.handlers:
        log_file = os.path.join(LOG_DIR, 'crashes.log')
        
        # TimedRotatingFileHandler
        # when='D' (Daily), interval=1, backupCount=30 (Keep 30 days)
        handler = TimedRotatingFileHandler(
            log_file,
            when='D',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

def setup_detection_logger():
    """
    Setup logger for detections and operational info.
    Policy: Max 100MB per file, keep 10 backup files (~1GB total).
    """
    logger = logging.getLogger(DETECTION_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        log_file = os.path.join(LOG_DIR, 'detections.log')
        
        # RotatingFileHandler
        # maxBytes=100*1024*1024 (100MB), backupCount=10
        handler = RotatingFileHandler(
            log_file,
            maxBytes=100*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        print(f"DEBUG: Added handler {handler} to logger {logger.name}. Log file: {log_file}")
        
        # Also add a stream handler to see logs in console during development
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
    return logger

def setup_fetch_logger():
    """
    Setup logger for Database Sync operations.
    Policy: Max 100MB per file, keep 10 lines (~1GB total).
    """
    logger = logging.getLogger('qc_fetch_logger')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        log_file = os.path.join(LOG_DIR, 'fetch.log')
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=100*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
    return logger

def get_crash_logger():
    """Get the crash logger instance"""
    return setup_crash_logger()

def get_detection_logger():
    """Get the detection logger instance"""
    return setup_detection_logger()

def get_fetch_logger():
    """Get the fetch logger instance"""
    return setup_fetch_logger()
