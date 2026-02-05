import sys
from PySide6.QtWidgets import QApplication, QWidget, QStackedWidget, QVBoxLayout
from app.pages.menu_screen import MenuScreen
from app.pages.measure_photo_screen import MeasurePhotoScreen
from app.pages.measure_video_screen import MeasureVideoScreen
from app.pages.measure_live_screen import LiveCameraScreen
from app.pages.capture_dataset_screen import CaptureDatasetScreen
from app.pages.general_settings_page import GeneralSettingsPage
from app.pages.profiles_page import ProfilesPage

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
        import json
        import os

        # Helper to get worker class (lazy import style kept simple here)
        self.ProductSKUWorker = ProductSKUWorker

        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.timeout.connect(self.check_scheduler)
        self.scheduler_timer.start(60000) # Check every 60 seconds

        # State to prevent multiple runs in the same minute/window
        self.last_run_date = None
        
        # Default schedule time (could be loaded from settings)
        self.scheduled_hour = 9 
        self.scheduled_minute = 0
        
        print(f"[Scheduler] Internal scheduler started. Checking every min. Target: {self.scheduled_hour:02d}:{self.scheduled_minute:02d}")

    def check_scheduler(self):
        from PySide6.QtCore import QTime, QDate
        now = QTime.currentTime()
        today = QDate.currentDate()
        
        # Check time match (simple equality check on hour/minute)
        # We use a flag 'last_run_date' to ensure we only run ONCE per day
        if (now.hour() == self.scheduled_hour and 
            now.minute() == self.scheduled_minute):
            
            if self.last_run_date != today:
                print(f"[Scheduler] Time match! Starting scheduled fetch task...")
                self.run_scheduled_fetch()
                self.last_run_date = today
            else:
                # Already ran today
                pass

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
            print(f"[Scheduler] Fetch success! Got {len(products)} items.")
            if not products:
                print("[Scheduler] Empty result, skipping save.")
                return

            output_path = os.path.join("output", "settings", "skus.json")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
                
            print(f"[Scheduler] Saved to {output_path}")
            
            # Optional: Refresh currently open pages if they display this data
            # self.profiles_page.refresh_data() # usage depends on if it's safe to call off-main-thread or if this is main thread.
            # worker finished signal is on main thread, so it's safe.
            if self.stack.currentWidget() == self.profiles_page:
                self.profiles_page.refresh_data()
                
        except Exception as e:
            print(f"[Scheduler] Error saving data: {e}")

    def on_scheduled_fetch_error(self, err_msg):
        print(f"[Scheduler] Fetch failed: {err_msg}")

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
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())