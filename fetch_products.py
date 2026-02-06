import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

def get_seconds_until_next_schedule(schedule_times):
    """
    Calculate seconds until the nearest time in the schedule.
    schedule_times: list of strings like "06:00", "18:00"
    """
    now = datetime.now()
    possible_runs = []
    
    for t_str in schedule_times:
        try:
            h, m = map(int, t_str.split(':'))
            # Try today
            run_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if run_time <= now:
                # If already passed today, try tomorrow
                run_time += timedelta(days=1)
            possible_runs.append(run_time)
        except Exception as e:
            log_error(f"Invalid schedule time format '{t_str}': {e}")
    
    if not possible_runs:
        return None
        
    next_run = min(possible_runs)
    wait_seconds = (next_run - now).total_seconds()
    return wait_seconds, next_run

def run_daemon(interval_hours=None, interval_mins=None, schedule=None):
    """
    Runs the fetch task in a loop with flexible scheduling.
    """
    if schedule:
        log_info(f"Starting daemon mode. Scheduled times: {', '.join(schedule)}")
    elif interval_mins:
        log_info(f"Starting daemon mode. Fetching every {interval_mins} minutes.")
    else:
        log_info(f"Starting daemon mode. Fetching every {interval_hours} hours.")
    
    while True:
        # Run the task
        success = fetch_and_save()
        
        if not success:
            log_error("Failed to fetch and save. Retrying in 5 minutes...")
            time.sleep(300)
            continue
        
        # Determine wait time
        wait_seconds = 0
        next_run_desc = ""
        
        if schedule:
            res = get_seconds_until_next_schedule(schedule)
            if res:
                wait_seconds, next_run_dt = res
                next_run_desc = next_run_dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                log_error("No valid schedules found. Falling back to 24h interval.")
                wait_seconds = 24 * 3600
                next_run_desc = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        elif interval_mins:
            wait_seconds = interval_mins * 60
            next_run_desc = (datetime.now() + timedelta(minutes=interval_mins)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            wait_seconds = interval_hours * 3600
            next_run_desc = (datetime.now() + timedelta(hours=interval_hours)).strftime('%Y-%m-%d %H:%M:%S')
            
        log_info(f"Task complete. Sleeping until {next_run_desc} ({int(wait_seconds)} seconds)")
        time.sleep(wait_seconds)

def main():
    parser = argparse.ArgumentParser(description="Fetch Product SKUs from Database")
    parser.add_argument('--now', action='store_true', help="Run immediately and exit (default behavior)")
    parser.add_argument('--daemon', action='store_true', help="Run in a loop (daemon mode)")
    parser.add_argument('--interval', type=int, default=24, help="Interval in hours for daemon mode (default: 24)")
    parser.add_argument('--interval-min', type=int, help="Interval in minutes for daemon mode (overrides --interval)")
    parser.add_argument('--schedule', type=str, help="Comma-separated times (HH:MM) to run, e.g., '06:00,18:00'")
    
    args = parser.parse_args()
    
    if args.daemon:
        schedule_list = None
        if args.schedule:
            schedule_list = [t.strip() for t in args.schedule.split(',')]
            
        run_daemon(
            interval_hours=args.interval, 
            interval_mins=args.interval_min, 
            schedule=schedule_list
        )
    else:
        # One-shot execution
        fetch_and_save()

if __name__ == "__main__":
    main()
