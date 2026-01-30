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