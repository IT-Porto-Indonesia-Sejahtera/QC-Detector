import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter
import numpy as np
from model.measure_live_sandals import measure_live_sandals


# ---------------------------------------------------------------------
# Dummy Data
# ---------------------------------------------------------------------
MODEL_DATA = {
    "E6005M": ["33", "33", "34", "35", "36", "37", "38", "39", "40"],
    "1094M": ["39", "40", "41", "42"],
    "3097K-4": ["35", "36", "37"],
}

PRESETS = [
    ("A-38", "Model A", "38"),
    ("A-40", "Model A", "40"),
    ("B-41", "Model B", "41"),
    ("C-36", "Model C", "36"),
]

class LiveCameraScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowTitle("Live Camera QC")
        self.last_results_text = None   # store text lines to draw
        self.last_pass_fail = None      # PASS / FAIL color

        # -----------------------------------------------------------------
        # CREATE MISSING WIDGETS (Fix for AttributeError)
        # -----------------------------------------------------------------

        # Big frame (main camera)
        self.big_label = QLabel()
        self.big_label.setStyleSheet("background: #111; border: 1px solid #333;")
        # self.big_label.setMinimumSize(800, 480)
        self.big_label.setAlignment(Qt.AlignCenter)
        self.big_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Small frame (preview)
        self.small_label = QLabel()
        self.small_label.setStyleSheet("background: #222; border: 1px solid #444;")
        self.small_label.setFixedSize(240, 160)
        self.small_label.setAlignment(Qt.AlignCenter)
        self.small_label.setCursor(Qt.PointingHandCursor)
        self.small_label.setToolTip("Click to swap live / captured")
        self.small_label.mousePressEvent = self.swap_frames

        # Camera selector
        self.cam_select = QComboBox()
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.currentIndexChanged.connect(self.change_camera)

        # Model selector
        self.model_select = QComboBox()
        self.model_select.addItems(MODEL_DATA.keys())
        self.model_select.currentIndexChanged.connect(self.update_sizes)

        # Size selector
        self.size_select = QComboBox()
        self.update_sizes()  # fill with initial model sizes

        # -----------------------------------------------------------------
        # UI LAYOUT
        # -----------------------------------------------------------------
        main_layout = QVBoxLayout()

        # Top floating buttons
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.back_button = QPushButton("←")
        self.back_button.setFixedSize(40, 40)
        self.back_button.setStyleSheet("""
            QPushButton {
                background: #444;
                color: white;
                font-weight: bold;
                border-radius: 20px;
            }
            QPushButton:hover { background: #666; }
        """)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setToolTip("Back to previous screen")

        self.capture_button = QPushButton("📸")
        self.capture_button.setFixedSize(48, 48)
        self.capture_button.setStyleSheet("""
            QPushButton {
                background: #00AEEF;
                color: white;
                font-size: 20px;
                border-radius: 24px;
            }
            QPushButton:hover { background: #0090C8; }
        """)
        self.capture_button.clicked.connect(self.capture_frame)
        self.capture_button.setToolTip("Capture & measure (shortcut available)")

        top_bar.addWidget(self.back_button, alignment=Qt.AlignLeft)
        top_bar.addStretch()
        top_bar.addWidget(self.capture_button, alignment=Qt.AlignRight)

        main_layout.addLayout(top_bar)
        main_layout.addSpacing(5)

        # Big camera area
        main_layout.addWidget(self.big_label)

        # Bottom area: left preview + right controls
        bottom = QHBoxLayout()
        bottom.addWidget(self.small_label)

        bottom_container = QFrame()
        bottom_container.setLayout(bottom)
        bottom_container.setFixedHeight(200)

        # Right panel
        right_panel = QVBoxLayout()

        # Camera selector row
        cam_row = QHBoxLayout()
        cam_lbl = QLabel("Kamera:")
        cam_lbl.setFixedWidth(60)
        cam_row.addWidget(cam_lbl)
        cam_row.addWidget(self.cam_select)
        right_panel.addLayout(cam_row)

        # Model row
        model_row = QHBoxLayout()
        model_lbl = QLabel("SKU:")
        model_lbl.setFixedWidth(60)
        model_row.addWidget(model_lbl)
        model_row.addWidget(self.model_select)
        right_panel.addLayout(model_row)

        # Size row
        size_row = QHBoxLayout()
        size_lbl = QLabel("Ukuran:")
        size_lbl.setFixedWidth(60)
        size_row.addWidget(size_lbl)
        size_row.addWidget(self.size_select)
        right_panel.addLayout(size_row)

        # Presets
        preset_lbl = QLabel("Presets:")
        preset_lbl.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_panel.addWidget(preset_lbl)

        preset_btn_row = QHBoxLayout()
        for label, model, size in PRESETS:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton {
                    background: #333;
                    color: white;
                    border-radius: 6px;
                    padding: 3px 8px;
                }
                QPushButton:hover { background: #555; }
            """)
            btn.setToolTip(f"Set {model} / {size}")
            btn.clicked.connect(lambda _, m=model, s=size: self.set_preset(m, s))
            preset_btn_row.addWidget(btn)

        right_panel.addLayout(preset_btn_row)
        right_panel.addStretch()

        bottom.addLayout(right_panel)
        main_layout.addWidget(bottom_container)
        self.setLayout(main_layout)

        # -----------------------------------------------------------------
        # Camera system
        # -----------------------------------------------------------------
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.big_frame_is_live = True

        self.live_frame = None
        self.captured_frame = None

    # ------------------------------------------------------------------
    # Lifecycle fix — FIXES the "camera freeze after back"
    # ------------------------------------------------------------------
    def showEvent(self, event):
        """Reinitialize camera whenever this screen becomes visible."""
        # guard: ensure we have at least one camera string
        cam_text = self.cam_select.currentText() if self.cam_select.count() > 0 else "0"
        try:
            cam_index = int(cam_text)
        except Exception:
            cam_index = 0
        # release previous if any
        if self.cap is not None and self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = cv2.VideoCapture(cam_index)
        self.timer.start(30)
        super().showEvent(event)

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

    # ------------------------------------------------------------------
    # Camera utility
    # ------------------------------------------------------------------
    def detect_cameras(self, max_test=3):
        cams = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cams.append(str(i))
                cap.release()
        return cams or ["0"]

    def change_camera(self, index=None):
        """Called when camera selection changes. Accepts optional index arg from signal."""
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
    # Model + Size
    # ------------------------------------------------------------------
    def update_sizes(self):
        model = self.model_select.currentText() or list(MODEL_DATA.keys())[0]
        sizes = MODEL_DATA.get(model, [])
        self.size_select.clear()
        if sizes:
            self.size_select.addItems(sizes)

    def set_preset(self, model, size):
        # setCurrentText may not trigger index change if already selected, so call update_sizes
        self.model_select.setCurrentText(model)
        self.update_sizes()
        self.size_select.setCurrentText(size)

    # ------------------------------------------------------------------
    # Frame conversion (stable memory)
    # ------------------------------------------------------------------
    def cv2_to_pixmap(self, img, target_width, target_height):
        # Ensure we have a valid image
        if img is None:
            return QPixmap()

        # Convert BGR -> RGB and resize with padding while preserving aspect ratio
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

        # Create QImage and make a deep copy to avoid lifetime issues with numpy buffer
        qimg = QImage(canvas.data, target_width, target_height, 3 * target_width, QImage.Format_RGB888)
        qimg_copy = qimg.copy()  # force a deep copy so underlying memory is owned by Qt
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

        # Convert frame to pixmap
        pix = None
        if self.big_frame_is_live:
            pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
        else:
            pix = self.cv2_to_pixmap(self.live_frame, self.small_label.width(), self.small_label.height())

        # Draw measurement overlay ON THE BIG FRAME
        if self.big_frame_is_live and self.last_results_text:
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)

            # draw semi-transparent background
            bg_rect_height = 90
            painter.fillRect(10, 10, 250, bg_rect_height, QColor(0, 0, 0, 180))

            # text settings
            painter.setPen(QColor(255, 255, 255))
            y = 35
            for line in self.last_results_text:
                if "Result" in line:
                    if self.last_pass_fail == "PASS":
                        painter.setPen(QColor(0, 255, 0))
                    else:
                        painter.setPen(QColor(255, 0, 0))
                else:
                    painter.setPen(QColor(255, 255, 255))

                painter.drawText(20, y, line)
                y += 25

            painter.end()

        # Show pixmap
        if self.big_frame_is_live:
            self.big_label.setPixmap(pix)
        else:
            self.small_label.setPixmap(pix)


    def capture_frame(self):
        if self.live_frame is None:
            return

        results, processed = measure_live_sandals(
            self.live_frame,
            mm_per_px=0.3,
            draw_output=True,
            save_out=None
        )

        self.captured_frame = processed

        # Update small preview
        pix = self.cv2_to_pixmap(processed, self.small_label.width(), self.small_label.height())
        self.small_label.setPixmap(pix)

        # Extract the first result (only one sandal)
        if results:
            r = results[0]

            length = r.get("real_length_cm")
            width  = r.get("real_width_cm")
            pf     = r.get("pass_fail")

            self.last_results_text = [
                f"Length : {length:.1f} cm" if length else "Length : -",
                f"Width  : {width:.1f} cm" if width else "Width  : -",
                f"Result : {pf}"
            ]

            self.last_pass_fail = pf

        print(f"[INFO] Capture processed | Model: {self.model_select.currentText()} | "
            f"Size: {self.size_select.currentText()} | Results: {results}")


    def swap_frames(self, event):
        # clicking small preview toggles big/small between live and captured
        if self.captured_frame is None:
            return

        if self.big_frame_is_live:
            big_pix = self.cv2_to_pixmap(self.captured_frame, self.big_label.width(), self.big_label.height())
            small_pix = self.cv2_to_pixmap(self.live_frame, self.small_label.width(), self.small_label.height())
        else:
            big_pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
            small_pix = self.cv2_to_pixmap(self.captured_frame, self.small_label.width(), self.small_label.height())

        self.big_label.setPixmap(big_pix)
        self.small_label.setPixmap(small_pix)
        self.big_frame_is_live = not self.big_frame_is_live

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

