import os
import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGridLayout, QFrame, QSizePolicy
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from datetime import datetime
from model.measurement import measure_sandals
import project_utilities as putils


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QC Sandal Measurement")

        self.selected_image_path = None
        self.image_folder = putils.normalize_path("QC-Detector/input/temp_assets")
        self.output_folder = putils.normalize_path("QC-Detector/output/log_output")

        # === Main Layout ===
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        # === Left Panel: Image Preview ===
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            border: 2px dashed #888;
            border-radius: 10px;
            background: black;  /* black background padding */
        """)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setMaximumSize(1000, 800)
        # ⚠️ Do NOT use setScaledContents(True) → keeps aspect ratio manually

        # Placeholder
        placeholder = QPixmap(256, 256)
        placeholder.fill(Qt.transparent)
        self.image_label.setPixmap(placeholder)
        left_panel.addStretch()
        left_panel.addWidget(self.image_label, alignment=Qt.AlignCenter)
        left_panel.addStretch()

        # === Buttons ===
        button_layout = QHBoxLayout()
        self.measure_button = QPushButton("Measure")
        self.measure_button.clicked.connect(self.measure_image)
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.measure_button)
        button_layout.addWidget(self.quit_button)
        left_panel.addLayout(button_layout)

        # === Right Panel: Scrollable Thumbnails ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(8)
        scroll.setWidget(grid_container)
        right_panel.addWidget(scroll)

        # Combine Layouts
        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 2)
        self.setLayout(main_layout)

        # Load thumbnails
        self.load_thumbnails()

        #maximize
        self.showMaximized()

    def load_thumbnails(self):
        """Load all images in input folder as thumbnails."""
        if not os.path.exists(self.image_folder):
            print("[WARN] Input folder not found:", self.image_folder)
            return

        images = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]

        for i, img_name in enumerate(images):
            img_path = os.path.join(self.image_folder, img_name)
            thumb = QLabel()
            thumb_pix = QPixmap(img_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb.setPixmap(thumb_pix)
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setFrameShape(QFrame.Box)
            thumb.setStyleSheet("border: 1px solid #aaa; border-radius: 4px;")
            thumb.mousePressEvent = lambda event, path=img_path: self.select_image(path)
            row, col = divmod(i, 3)
            self.grid_layout.addWidget(thumb, row, col)

    def select_image(self, path):
        """Handle image selection."""
        self.selected_image_path = path
        pixmap = QPixmap(path)
        self.display_pixmap_scaled(pixmap)
        print(f"[INFO] Selected image: {path}")

    def display_pixmap_scaled(self, pixmap):
        """Scale image to fit label while preserving aspect ratio (with padding)."""
        label_size = self.image_label.size()
        scaled = pixmap.scaled(
            label_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        """When window resizes, rescale current image properly."""
        if self.image_label.pixmap() and not self.image_label.pixmap().isNull():
            self.display_pixmap_scaled(self.image_label.pixmap())
        super().resizeEvent(event)

    def cv2_to_pixmap(self, cv_img):
        """Convert an OpenCV image (BGR) to QPixmap."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(q_image)

    def measure_image(self):
        """Run measurement and show result in GUI."""
        if not self.selected_image_path:
            print("[WARN] No image selected.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"measured_{timestamp}.png"
        output_path = os.path.join(self.output_folder, output_filename)

        print(f"[INFO] Measuring: {self.selected_image_path}")
        try:
            results, processed_img = measure_sandals(
                self.selected_image_path,
                mm_per_px=None,
                draw_output=False,
                save_out=output_path
            )

            print("[RESULT]", results)
            pixmap = self.cv2_to_pixmap(processed_img)
            self.display_pixmap_scaled(pixmap)

        except Exception as e:
            print("[ERROR]", e)


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
