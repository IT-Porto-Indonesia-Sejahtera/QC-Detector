import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.get_product_sku import get_product_sku
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

# Configure logging
from app.utils.fetch_logger import log_info, log_error, log_warning, log_success

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'settings', 'skus.json')

def fetch_and_save():
    """
    Fetches product SKUs and saves them to the output JSON file.
    """
    log_info("Starting product SKU fetch...")
    
    # Check env vars
    db_host = os.getenv("DB_HOST")
    log_info(f"DB_HOST from env: {db_host}")
    
    # Check connection explicitly
    from backend.DB import is_connected, init_db
    if not is_connected():
        log_info("Database not connected. Attempting to initialize...")
        try:
            init_db()
        except Exception as e:
            log_error(f"Failed to initialize database: {e}")
            return False

    if is_connected():
        log_info("Database connection established.")
    else:
        log_error("Database connection failed even after initialization.")
        return False

    try:
        # Fetch data
        products = get_product_sku()
        
        if not products:
            log_warning("No products fetched. Aborting save to prevent data loss.")
            return False

        count = len(products)
        log_success(f"Fetched {count} products.")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

        # Save to JSON
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=4, ensure_ascii=False)
            
        log_success(f"Successfully saved to {OUTPUT_FILE}")
        return True

    except Exception as e:
        import traceback
        log_error(f"Error during fetch/save: {e}")
        log_error(traceback.format_exc())
        return False

def run_daemon(interval_hours=24):
    """
    Runs the fetch task in a loop.
    """
    log_info(f"Starting daemon mode. Fetching every {interval_hours} hours.")
    
    while True:
        success = fetch_and_save()
        if not success:
            log_error("Failed to fetch and save. Retrying in 5 minutes...")
            time.sleep(300)  # Wait 5 minutes before retrying
            continue
        
        # Calculate next run
        next_run = datetime.now() + timedelta(hours=interval_hours)
        log_info(f"Sleeping until {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        # Sleep
        time.sleep(interval_hours * 3600)

def main():
    parser = argparse.ArgumentParser(description="Fetch Product SKUs from Database")
    parser.add_argument('--now', action='store_true', help="Run immediately and exit (default behavior)")
    parser.add_argument('--daemon', action='store_true', help="Run in a loop (daemon mode)")
    parser.add_argument('--interval', type=int, default=24, help="Interval in hours for daemon mode (default: 24)")
    
    args = parser.parse_args()
    
    # Default to running immediately if no specific mode or if --now is passed
    if args.daemon:
        run_daemon(args.interval)
    else:
        # One-shot execution
        fetch_and_save()

if __name__ == "__main__":
    main()
