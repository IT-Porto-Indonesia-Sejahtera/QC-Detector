import cv2
import os
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage

class CaptureDatasetScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowTitle("Capture Dataset")
        
        # Ensure output directory exists
        self.output_dir = os.path.join("output", "dataset")
        os.makedirs(self.output_dir, exist_ok=True)

        # -----------------------------------------------------------------
        # CREATE WIDGETS
        # -----------------------------------------------------------------

        # Big frame (main camera)
        self.big_label = QLabel()
        self.big_label.setStyleSheet("background: #111; border: 1px solid #333;")
        self.big_label.setAlignment(Qt.AlignCenter)
        self.big_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Camera Selector
        self.cam_select = QComboBox()
        self.cam_select.setFixedWidth(200)
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.currentIndexChanged.connect(self.change_camera)
        self.cam_select.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 5px;
                background: #333;
                color: white;
            }
            QComboBox::drop-down { border: 0px; }
        """)

        # -----------------------------------------------------------------
        # UI LAYOUT
        # -----------------------------------------------------------------
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- TOP BAR ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        # Back Button
        self.back_button = QPushButton("←")
        self.back_button.setFixedSize(40, 40)
        self.back_button.setStyleSheet("""
            QPushButton {
                background: #444;
                color: white;
                font-weight: bold;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover { background: #666; }
        """)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setToolTip("Back to previous screen")

        top_bar.addWidget(self.back_button, alignment=Qt.AlignLeft)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Camera: "))
        top_bar.addWidget(self.cam_select)
        
        main_layout.addLayout(top_bar)

        # --- BIG CAMERA AREA ---
        main_layout.addWidget(self.big_label)

        # --- BOTTOM AREA ---
        bottom_container = QFrame()
        bottom_container.setFixedHeight(100)
        bottom_container.setStyleSheet("background: #1A1A1A; border-radius: 10px;")
        
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(15, 15, 15, 15)
        bottom_layout.setSpacing(20)

        # Capture Button
        self.capture_btn = QPushButton("📸 Capture Image")
        self.capture_btn.setFixedHeight(60)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover { background: #0056b3; }
            QPushButton:pressed { background: #004080; }
        """)
        self.capture_btn.clicked.connect(self.capture_image)
        
        bottom_layout.addWidget(self.capture_btn)

        main_layout.addWidget(bottom_container)
        self.setLayout(main_layout)

        # -----------------------------------------------------------------
        # Camera system
        # -----------------------------------------------------------------
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.live_frame = None

    def detect_cameras(self, max_test=3):
        cams = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cams.append(str(i))
                cap.release()
        return cams or ["0"]

    def change_camera(self, index=None):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        try:
            cam_text = self.cam_select.currentText() or "0"
            cam_idx = int(cam_text)
        except Exception:
            cam_idx = 0
        self.cap = cv2.VideoCapture(cam_idx)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def showEvent(self, event):
        """Reinitialize camera whenever this screen becomes visible."""
        # Refresh camera list
        current_cam = self.cam_select.currentText()
        self.cam_select.blockSignals(True)
        self.cam_select.clear()
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.blockSignals(False)
        
        # Restore selection if possible, else default
        index = self.cam_select.findText(current_cam)
        if index >= 0:
            self.cam_select.setCurrentIndex(index)
        
        # guard: ensure we have at least one camera string
        cam_text = self.cam_select.currentText() if self.cam_select.count() > 0 else "0"
        try:
            cam_index = int(cam_text)
        except Exception:
            cam_index = 0

        if self.cap is not None and self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = cv2.VideoCapture(cam_index)
        self.timer.start(30)
        super().showEvent(event)

    def hideEvent(self, event):
        """Ensure camera is released when widget is hidden."""
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        super().hideEvent(event)

    def closeEvent(self, event):
        """Proper cleanup."""
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        super().closeEvent(event)

    def go_back(self):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        if self.parent_widget:
            self.parent_widget.go_back()

    # ------------------------------------------------------------------
    # Frame conversion
    # ------------------------------------------------------------------
    def cv2_to_pixmap(self, img, target_width, target_height):
        if img is None:
            return QPixmap()

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, _ = img_rgb.shape
        scale = min(max(1e-6, target_width / w), max(1e-6, target_height / h))
        new_w, new_h = int(w * scale), int(h * scale)
        if new_w == 0 or new_h == 0:
            return QPixmap()

        resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        x_offset = (target_width - new_w) // 2
        y_offset = (target_height - new_h) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        qimg = QImage(canvas.data, target_width, target_height, 3 * target_width, QImage.Format_RGB888)
        qimg_copy = qimg.copy()
        return QPixmap.fromImage(qimg_copy)

    # ------------------------------------------------------------------
    # Main functions
    # ------------------------------------------------------------------
    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self.live_frame = frame.copy()
        pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
        self.big_label.setPixmap(pix)

    def capture_image(self):
        if self.live_frame is None:
            return

        timestamp = int(time.time() * 1000)
        filename = f"dataset_{timestamp}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        cv2.imwrite(filepath, self.live_frame)
        print(f"[INFO] Saved image to {filepath}")
        
        # Optional: Flash effect or feedback
        self.capture_btn.setText("Saved!")
        QTimer.singleShot(1000, lambda: self.capture_btn.setText("📸 Capture Image"))
