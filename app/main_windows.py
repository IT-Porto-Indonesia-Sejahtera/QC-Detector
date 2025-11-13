import sys
from PySide6.QtWidgets import QApplication, QWidget, QStackedWidget, QVBoxLayout
from app.pages.menu_screen import MenuScreen
from app.pages.measure_photo_screen import MeasurePhotoScreen
from app.pages.measure_video_screen import MeasureVideoScreen

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QC Detector System")
        self.setMinimumSize(900, 600)

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

        # Create pages
        self.menu_page = MenuScreen(controller=self)
        self.photo_page = MeasurePhotoScreen(controller=self)
        self.video_page = MeasureVideoScreen(controller=self)

        # Add to stack
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.photo_page)
        self.stack.addWidget(self.video_page)

        self.stack.setCurrentWidget(self.menu_page)

    def go_to_photo(self):
        self.stack.setCurrentWidget(self.photo_page)

    def go_to_video(self):
        self.stack.setCurrentWidget(self.video_page)

    def go_back(self):
        self.stack.setCurrentWidget(self.menu_page)


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())