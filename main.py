import os
import sys
import atexit
import signal
from datetime import datetime
from model.measurement import measure_sandals
import project_utilities as putils
import app.main_windows as app  # import the PyQt app
from backend.DB import init_db, close_pool

def cleanup():
    """Cleanup function to close database connections."""
    print("\n🔄 Closing database connections...")
    close_pool()
    print("✓ Cleanup complete")

def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    signal_name = signal.Signals(signum).name
    print(f"\n⚠ Received {signal_name}, shutting down...")
    cleanup()
    sys.exit(0)

def init_database():
    """Initialize the database connection pool."""
    try:
        init_db()
        print("✓ Database connection pool initialized")
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")
        print("  App will continue without database functionality")

def run_cli_mode():
    """Run measurement in command-line mode."""
    img_path = "QC-Detector\\input\\temp_assets\\WhatsApp Image 2025-11-11 at 14.54.35 (1).jpeg"
    mm_per_px = None 

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"measured_{timestamp}.png"
    output_path = os.path.join("QC-Detector", "output", "log_output", output_filename)

    print("Measuring:", img_path)
    normalized_path = putils.normalize_path(img_path)
    print("Normalized path:", normalized_path)

    res = measure_sandals(
        normalized_path, 
        mm_per_px=mm_per_px,
        draw_output=True,
        save_out=output_path
    )
    print("Results:", res)

def run_ui_mode():
    """Run the GUI version of the app."""
    app.run_app()

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    
    # Register cleanup function for normal exit
    atexit.register(cleanup)
    
    # Initialize database connection pool
    init_database()
    
    MODE = "ui"
    if MODE == "ui":
        run_ui_mode()
    else:
        run_cli_mode()