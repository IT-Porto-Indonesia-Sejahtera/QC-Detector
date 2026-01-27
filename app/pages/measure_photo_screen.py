import os
import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGridLayout, QFrame, QSizePolicy,
    QComboBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from datetime import datetime
from model.measurement import measure_sandals
import project_utilities as putils
from app.utils.ui_scaling import UIScaling

class MeasurePhotoScreen(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle("QC Sandal Measurement")
        self.controller = controller
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
        borderRadius = UIScaling.scale(10)
        self.image_label.setStyleSheet(f"""
            border: 2px dashed #CCCCCC;
            border-radius: {borderRadius}px;
            background: #F8F8F8;
        """)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(UIScaling.scale(400), UIScaling.scale(400))

        # Placeholder
        placeholder_size = UIScaling.scale(256)
        placeholder = QPixmap(placeholder_size, placeholder_size)
        placeholder.fill(Qt.transparent)
        self.image_label.setPixmap(placeholder)
        left_panel.addStretch()
        left_panel.addWidget(self.image_label, alignment=Qt.AlignCenter)
        left_panel.addStretch()

        # === Detection Method Selector ===
        method_layout = QHBoxLayout()
        method_label = QLabel("Detection Method:")
        method_label.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px; font-weight: bold; color: #333;")
        
        self.method_combo = QComboBox()
        self.method_combo.addItem("Standard (Contour)", "standard")
        self.method_combo.addItem("SAM (AI)", "sam")
        self.method_combo.setMinimumWidth(UIScaling.scale(180))
        self.method_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: {UIScaling.scale_font(14)}px;
                padding: {UIScaling.scale(8)}px;
                border: 1px solid #CCCCCC;
                border-radius: {UIScaling.scale(6)}px;
                background: white;
            }}
            QComboBox:hover {{
                border: 1px solid #2196F3;
            }}
        """)
        
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()
        left_panel.addLayout(method_layout)
        left_panel.addSpacing(UIScaling.scale(10))

        # === Buttons ===
        button_layout = QHBoxLayout()
        btn_padding = UIScaling.scale(8)
        btn_font_size = UIScaling.scale_font(14)
        btn_radius = UIScaling.scale(8)
        
        self.measure_button = QPushButton("Measure")
        self.measure_button.setStyleSheet(f"background-color: #2196F3; color: white; border-radius: {btn_radius}px; font-weight: bold; padding: {btn_padding}px; font-size: {btn_font_size}px;")
        self.measure_button.clicked.connect(self.measure_image)
        self.quit_button = QPushButton("Quit")
        self.quit_button.setStyleSheet(f"background-color: #F5F5F5; color: #333333; border-radius: {btn_radius}px; font-weight: bold; padding: {btn_padding}px; font-size: {btn_font_size}px;")
        self.quit_button.clicked.connect(self.close)
        self.back_button = QPushButton("Back to Menu")
        self.back_button.setStyleSheet(f"background-color: #F5F5F5; color: #333333; border-radius: {btn_radius}px; font-weight: bold; padding: {btn_padding}px; font-size: {btn_font_size}px;")
        self.back_button.clicked.connect(self.controller.go_back)
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.measure_button)
        button_layout.addWidget(self.quit_button)
        left_panel.addLayout(button_layout)

        # === Right Panel: Scrollable Thumbnails ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(UIScaling.scale(8))
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

        thumb_size = UIScaling.scale(100)
        for i, img_name in enumerate(images):
            img_path = os.path.join(self.image_folder, img_name)
            thumb = QLabel()
            thumb_pix = QPixmap(img_path).scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb.setPixmap(thumb_pix)
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setFrameShape(QFrame.Box)
            thumb.setStyleSheet(f"border: 1px solid #aaa; border-radius: {UIScaling.scale(4)}px;")
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

        # Get selected detection method
        method = self.method_combo.currentData()
        use_sam = (method == "sam")
        
        method_name = "SAM (AI)" if use_sam else "Standard"
        print(f"[INFO] Measuring with {method_name}: {self.selected_image_path}")
        
        try:
            results, processed_img = measure_sandals(
                self.selected_image_path,
                mm_per_px=None,
                draw_output=False,
                save_out=output_path,
                use_sam=use_sam
            )

            # Show inference time if using SAM
            if use_sam and results and 'inference_time_ms' in results[0]:
                print(f"[SAM] Inference time: {results[0]['inference_time_ms']:.1f}ms")
            
            print("[RESULT]", results)
            pixmap = self.cv2_to_pixmap(processed_img)
            self.display_pixmap_scaled(pixmap)

        except Exception as e:
            print("[ERROR]", e)
