import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from datetime import datetime
from model.measure_live_sandals import measure_live_sandals
import numpy as np

class LiveCameraScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Camera QC")
        self.parent_widget = parent

        # --- Camera selection ---
        cam_layout = QHBoxLayout()
        self.cam_select = QComboBox()
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.currentIndexChanged.connect(self.change_camera)
        cam_layout.addWidget(QLabel("Select Camera:"))
        cam_layout.addWidget(self.cam_select)

        # --- Main display ---
        self.big_label = QLabel()
        self.big_label.setAlignment(Qt.AlignCenter)
        self.big_label.setStyleSheet("background-color: black; border: 1px solid #444;")
        self.big_label.setMinimumSize(640, 480)

        # --- Small frame ---
        self.small_label = QLabel()
        self.small_label.setAlignment(Qt.AlignCenter)
        self.small_label.setStyleSheet("background-color: black; border: 1px solid #444;")
        self.small_label.setFixedSize(200, 150)
        self.small_label.mousePressEvent = self.swap_frames

        # --- Buttons ---
        button_layout = QHBoxLayout()
        self.capture_button = QPushButton("Capture & Measure")
        self.capture_button.clicked.connect(self.capture_frame)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.capture_button)
        button_layout.addWidget(self.back_button)

        # --- Layout ---
        main_layout = QVBoxLayout()
        main_layout.addLayout(cam_layout)
        main_layout.addWidget(self.big_label)
        main_layout.addWidget(self.small_label, alignment=Qt.AlignLeft)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # --- Camera setup ---
        self.cam_index = int(self.cam_select.currentText())
        self.cap = cv2.VideoCapture(self.cam_index)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~30 FPS

        # Frame buffers
        self.live_frame = None
        self.captured_frame = None
        self.big_frame_is_live = True

    # ---------------- Utility ----------------
    def detect_cameras(self, max_test=3):
        cams = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cams.append(str(i))
                cap.release()
        return cams or ["0"]

    def change_camera(self, index):
        self.cap.release()
        self.cam_index = int(self.cam_select.currentText())
        self.cap = cv2.VideoCapture(self.cam_index)

    def cv2_to_pixmap(self, img, target_width, target_height):
        """Convert BGR image to QPixmap with aspect ratio preserved and black padding."""
        # Convert BGR -> RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, _ = img_rgb.shape
        scale = min(target_width / w, target_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        # Create black canvas
        canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        x_offset = (target_width - new_w) // 2
        y_offset = (target_height - new_h) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        # Convert to QPixmap
        qimg = QImage(canvas.data, target_width, target_height, 3*target_width, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    # ---------------- Core ----------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        self.live_frame = frame.copy()
        if self.big_frame_is_live:
            pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
            self.big_label.setPixmap(pix)
        elif self.captured_frame is not None:
            pix = self.cv2_to_pixmap(self.live_frame, self.small_label.width(), self.small_label.height())
            self.small_label.setPixmap(pix)

    def capture_frame(self):
        if self.live_frame is None:
            return
        results, processed = measure_live_sandals(self.live_frame, mm_per_px=None, draw_output=False, save_out=None)
        self.captured_frame = processed
        pix = self.cv2_to_pixmap(self.captured_frame, self.small_label.width(), self.small_label.height())
        self.small_label.setPixmap(pix)
        print("[INFO] Capture processed frame, results:", results)

    def swap_frames(self, event):
        if self.captured_frame is None:
            return
        if self.big_frame_is_live:
            # Show captured in big, live in small
            big_pix = self.cv2_to_pixmap(self.captured_frame, self.big_label.width(), self.big_label.height())
            small_pix = self.cv2_to_pixmap(self.live_frame, self.small_label.width(), self.small_label.height())
        else:
            # Show live in big, captured in small
            big_pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
            small_pix = self.cv2_to_pixmap(self.captured_frame, self.small_label.width(), self.small_label.height())
        self.big_label.setPixmap(big_pix)
        self.small_label.setPixmap(small_pix)
        self.big_frame_is_live = not self.big_frame_is_live

    def go_back(self):
        self.timer.stop()
        self.cap.release()
        if self.parent_widget:
            self.parent_widget.go_back()