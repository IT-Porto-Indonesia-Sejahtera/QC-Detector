import sys
import os
import json
import traceback
from PySide6.QtWidgets import QApplication, QWidget, QStackedWidget, QVBoxLayout
from app.pages.menu_screen import MenuScreen
from app.pages.measure_photo_screen import MeasurePhotoScreen
from app.pages.measure_video_screen import MeasureVideoScreen
from app.pages.measure_live_screen import LiveCameraScreen
from app.pages.capture_dataset_screen import CaptureDatasetScreen
from app.pages.general_settings_page import GeneralSettingsPage
from app.pages.profiles_page import ProfilesPage
from app.utils.fetch_logger import log_info, log_error, log_warning
from project_utilities.json_utility import JsonUtility

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QC Detector System")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: white;")
        self.from_live = False # Track if we came from live screen

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

        # Create pages
        self.menu_page = MenuScreen(controller=self)
        self.photo_page = MeasurePhotoScreen(controller=self)
        self.video_page = MeasureVideoScreen(controller=self)
        self.live_page = LiveCameraScreen(parent=self)
        self.dataset_page = CaptureDatasetScreen(parent=self)
        self.settings_page = GeneralSettingsPage(controller=self)
        self.profiles_page = ProfilesPage(controller=self)

        # Add to stack
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.photo_page)
        self.stack.addWidget(self.video_page)
        self.stack.addWidget(self.live_page)
        self.stack.addWidget(self.dataset_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.profiles_page)

        self.stack.setCurrentWidget(self.menu_page)

        # --- AI Model Warmup ---
        try:
            from model.inference_utils import ModelWarmupWorker
            self.warmup_worker = ModelWarmupWorker(self)
            self.warmup_worker.start()
            print("[Startup] Background AI model warmup started.")
        except Exception as e:
            print(f"[Startup] Error starting warmup: {e}")


        # --- Internal Scheduler Setup ---
        from PySide6.QtCore import QTimer, QTime
        from backend.get_product_sku import ProductSKUWorker

        self.ProductSKUWorker = ProductSKUWorker
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.timeout.connect(self.check_scheduler)
        self.scheduler_timer.start(60000) # Check every 60 seconds

        # Load scheduler settings
        self.refresh_scheduler_settings()
        
        log_info(f"[Scheduler] Internal scheduler started. Mode: {self.scheduler_mode}")
    
    def refresh_scheduler_settings(self):
        """Load scheduler configuration from app_settings.json"""
        settings_file = os.path.join("output", "settings", "app_settings.json")
        settings = JsonUtility.load_from_json(settings_file) or {}
        
        # Scheduling Modes: "daily" (legacy), "interval" (minutes), "schedule" (specific times)
        self.scheduler_mode = settings.get("scheduler_mode", "daily")
        self.scheduler_interval_min = settings.get("scheduler_interval_min", 60)
        self.scheduler_schedule_times = settings.get("scheduler_schedule_times", ["09:00"])
        
        # Legacy single-time support
        self.scheduled_hour = settings.get("scheduler_hour", 9) 
        self.scheduled_minute = settings.get("scheduler_minute", 0)
        
        # State tracking
        self.last_run_time = None 
        self.last_run_date = None

    def check_scheduler(self):
        from PySide6.QtCore import QTime, QDate, QDateTime
        now = QDateTime.currentDateTime()
        
        should_run = False
        
        if self.scheduler_mode == "interval":
            # Interval mode: check if enough minutes passed since last run
            if self.last_run_time is None:
                should_run = True # Run on startup if in interval mode
            else:
                mins_passed = self.last_run_time.secsTo(now) / 60
                if mins_passed >= self.scheduler_interval_min:
                    should_run = True
                    
        elif self.scheduler_mode == "schedule":
            # Multi-time schedule mode
            current_time_str = now.time().toString("HH:mm")
            if current_time_str in self.scheduler_schedule_times:
                # Ensure we only run once per day for THIS specific minute slot
                # Using a combo of date + time string for tracking
                run_id = f"{now.date().toString(Qt.ISODate)}_{current_time_str}"
                if self.last_run_date != run_id:
                    should_run = True
                    self.last_run_date = run_id
                    
        else: # "daily" legacy mode
            now_time = now.time()
            if (now_time.hour() == self.scheduled_hour and 
                now_time.minute() == self.scheduled_minute):
                if self.last_run_date != now.date():
                    should_run = True
                    self.last_run_date = now.date()

        if should_run:
            log_info(f"[Scheduler] Condition met ({self.scheduler_mode}). Starting fetch...")
            self.run_scheduled_fetch()
            self.last_run_time = now

    def run_scheduled_fetch(self):
        worker = self.ProductSKUWorker(limit=None, parent=self)
        worker.finished.connect(self.on_scheduled_fetch_success)
        worker.error.connect(self.on_scheduled_fetch_error)
        worker.start()
        # Keep reference to avoid GC? QThread parenting usually handles it, but good practice
        self._scheduler_worker = worker 
        
    def on_scheduled_fetch_success(self, products):
        import os
        import json
        
        try:
            log_info(f"[Scheduler] Fetch success! Got {len(products)} items.")
            if not products:
                print("[Scheduler] Empty result, skipping save.")
                return

            output_path = os.path.join("output", "settings", "skus.json")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
                
            log_info(f"[Scheduler] Saved results to {output_path}")
            
            # Optional: Refresh currently open pages if they display this data
            # self.profiles_page.refresh_data() # usage depends on if it's safe to call off-main-thread or if this is main thread.
            # worker finished signal is on main thread, so it's safe.
            if self.stack.currentWidget() == self.profiles_page:
                self.profiles_page.refresh_data()
                
        except Exception as e:
            log_error(f"[Scheduler] Error saving data: {e}")
            log_error(traceback.format_exc())

    def on_scheduled_fetch_error(self, err_msg):
        log_error(f"[Scheduler] Fetch failed: {err_msg}")

    def go_to_photo(self):
        self.stack.setCurrentWidget(self.photo_page)

    def go_to_video(self):
        self.stack.setCurrentWidget(self.video_page)

    def go_to_live(self):
        self.from_live = False
        self.live_page.refresh_data()
        self.stack.setCurrentWidget(self.live_page)

    def go_to_dataset(self):
        self.stack.setCurrentWidget(self.dataset_page)
        
    def go_to_settings(self, from_live=False):
        self.from_live = from_live
        self.settings_page.refresh_data()
        self.stack.setCurrentWidget(self.settings_page)
        
    def go_to_profiles(self, from_live=False):
        self.from_live = from_live
        self.profiles_page.refresh_data()
        self.stack.setCurrentWidget(self.profiles_page)

    def go_back(self):
        # Admin back button: return to live if we came from there, otherwise return to menu
        if self.from_live:
            self.from_live = False
            self.live_page.refresh_data()
            self.stack.setCurrentWidget(self.live_page)
        else:
            self.stack.setCurrentWidget(self.menu_page)
            
    def go_to_home(self):
        self.from_live = False
        self.stack.setCurrentWidget(self.menu_page)


def run_app():
    # Enable High DPI scaling and set rounding policy for fractional scaling
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    
    # Global Stylesheet for consistent UI
    # Focus on QComboBox, ScrollBars, and general app feel
    app.setStyleSheet("""
        /* Global Font/Base */
        QWidget {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
        }

        /* --- Global QComboBox Styling --- */
        QComboBox {
            background-color: white;
            border: 1px solid #D1D1D6;
            border-radius: 8px;
            padding: 5px 10px;
            color: #1C1C1E;
            font-size: 14px;
        }

        QComboBox:hover {
            border: 1px solid #007AFF;
            background-color: #F8F9FA;
        }

        QComboBox:on { /* shift the text when the popup opens */
            padding-top: 3px;
            padding-left: 4px;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left-width: 0px;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: transparent; 
        }

        QComboBox::down-arrow {
            /* Using none allows Qt to draw default arrow if image is none. 
               Ideally use an SVG icon here for full customization. */
            width: 12px;
            height: 12px;
            image: none;
            border-image: none;
        }
        
        /* THE POPUP LIST - FIX WHITE ON WHITE */
        QComboBox QAbstractItemView {
            border: 1px solid #D1D1D6;
            background-color: white;   /* Light background */
            color: #1C1C1E;            /* Dark text */
            selection-background-color: #007AFF;
            selection-color: white;
            outline: none;
            border-radius: 8px;
            padding: 4px;
        }
        
        /* CALENDAR / DATE EDIT SCROLLING FIX */
        QCalendarWidget QWidget#qt_calendar_navigationbar { 
            background-color: white; 
        }
        QCalendarWidget QToolButton {
            color: black;
            font-weight: bold;
            icon-size: 24px;
        }
        QCalendarWidget QAbstractItemView {
            background-color: white;
            color: black;  /* Fix for invisible weekdays */
            selection-background-color: #007AFF;
            selection-color: white;
        }

        /* --- Global Scrollbar Styling (Minimalist) --- */
        QScrollBar:vertical {
            border: none;
            background: #F2F2F7;
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar:handle:vertical {
            background: #D1D1D6;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar:handle:vertical:hover {
            background: #A1A1A6;
        }
        QScrollBar:add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: #F2F2F7;
            height: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal {
            background: #D1D1D6;
            min-width: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #A1A1A6;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }
    """)

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())