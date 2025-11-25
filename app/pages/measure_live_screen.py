import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QSizePolicy, QGridLayout, QMenu, QWidgetAction,
    QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QAction, QDoubleValidator
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
        
        # Default calibration value
        self.mm_per_px = 0.215984148

        # Mutable presets (copy from global default)
        # Structure: {"label": "A-38", "model": "Model A", "size": "38"}
        self.presets = []
        for label, model, size in PRESETS:
            self.presets.append({"label": label, "model": model, "size": size})

        # -----------------------------------------------------------------
        # CREATE WIDGETS
        # -----------------------------------------------------------------

        # Big frame (main camera)
        self.big_label = QLabel()
        self.big_label.setStyleSheet("background: #111; border: 1px solid #333;")
        self.big_label.setAlignment(Qt.AlignCenter)
        self.big_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Small frame (preview)
        self.small_label = QLabel()
        self.small_label.setStyleSheet("background: #222; border: 1px solid #444;")
        self.small_label.setFixedSize(240, 180) # Slightly taller
        self.small_label.setAlignment(Qt.AlignCenter)
        self.small_label.setCursor(Qt.PointingHandCursor)
        self.small_label.setToolTip("Click to swap live / captured")
        self.small_label.mousePressEvent = self.swap_frames

        # Camera selector (Hidden, used in settings menu)
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

        # MM per Pixel Input (QLineEdit for better typing experience)
        self.mm_input = QLineEdit()
        self.mm_input.setFixedWidth(200)
        self.mm_input.setText(str(self.mm_per_px))
        self.mm_input.setValidator(QDoubleValidator(0.0001, 10.0, 9))
        self.mm_input.textChanged.connect(self.update_mm_per_px)
        self.mm_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 5px;
                background: #333;
                color: white;
            }
        """)

        # Model selector
        self.model_select = QComboBox()
        self.model_select.setFixedHeight(40)
        self.model_select.addItems(MODEL_DATA.keys())
        self.model_select.currentIndexChanged.connect(self.update_sizes)
        self.model_select.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #555;
                border-radius: 8px;
                background: #333;
                color: white;
                font-size: 14px;
            }
            QComboBox::drop-down { border: 0px; }
        """)

        # Size selector
        self.size_select = QComboBox()
        self.size_select.setFixedHeight(40)
        self.update_sizes()  # fill with initial model sizes
        self.size_select.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #555;
                border-radius: 8px;
                background: #333;
                color: white;
                font-size: 14px;
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

        # Settings Button (Right)
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.setFixedHeight(40)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background: #333;
                color: white;
                font-weight: bold;
                border-radius: 20px;
                padding: 0 15px;
                border: 1px solid #555;
            }
            QPushButton:hover { background: #444; }
            QPushButton::menu-indicator { image: none; }
        """)
        self.settings_button.clicked.connect(self.show_settings_menu)

        top_bar.addWidget(self.back_button, alignment=Qt.AlignLeft)
        top_bar.addStretch()
        top_bar.addWidget(self.settings_button)

        main_layout.addLayout(top_bar)

        # --- SETTINGS MENU (Persistent) ---
        self.settings_menu = QMenu(self)
        self.settings_menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: white;
                border: 1px solid #555;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #444;
            }
        """)

        # Capture Action
        capture_action = QAction("📸 Force Capture", self)
        capture_action.triggered.connect(self.capture_frame)
        self.settings_menu.addAction(capture_action)

        self.settings_menu.addSeparator()

        # Camera Label
        cam_label = QAction("Camera Source:", self)
        cam_label.setEnabled(False)
        self.settings_menu.addAction(cam_label)

        # Camera Selector Widget
        cam_widget_action = QWidgetAction(self)
        cam_widget_action.setDefaultWidget(self.cam_select)
        self.settings_menu.addAction(cam_widget_action)

        self.settings_menu.addSeparator()

        # MM per Pixel Label
        mm_label = QAction("MM per Pixel:", self)
        mm_label.setEnabled(False)
        self.settings_menu.addAction(mm_label)

        # MM per Pixel Widget
        mm_widget_action = QWidgetAction(self)
        mm_widget_action.setDefaultWidget(self.mm_input)
        self.settings_menu.addAction(mm_widget_action)

        # --- BIG CAMERA AREA ---
        main_layout.addWidget(self.big_label)

        # --- BOTTOM AREA ---
        bottom_container = QFrame()
        bottom_container.setFixedHeight(260) # Increased height for bigger presets
        bottom_container.setStyleSheet("background: #1A1A1A; border-radius: 10px;")
        
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(15, 15, 15, 15)
        bottom_layout.setSpacing(20)

        # 1. Small Preview (Left)
        bottom_layout.addWidget(self.small_label, alignment=Qt.AlignVCenter)

        # 2. Controls Area (Right)
        controls_layout = QHBoxLayout()
        
        # 2a. Selectors (SKU & Size) - Vertical Stack
        selectors_layout = QVBoxLayout()
        selectors_layout.setSpacing(15)
        selectors_layout.addStretch() # Top stretch for vertical centering
        
        # SKU
        sku_group = QVBoxLayout()
        sku_group.setSpacing(5)
        sku_lbl = QLabel("SKU / MODEL")
        sku_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        sku_group.addWidget(sku_lbl)
        sku_group.addWidget(self.model_select)
        
        # Size
        size_group = QVBoxLayout()
        size_group.setSpacing(5)
        size_lbl = QLabel("SIZE")
        size_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        size_group.addWidget(size_lbl)
        size_group.addWidget(self.size_select)

        selectors_layout.addLayout(sku_group)
        selectors_layout.addLayout(size_group)
        selectors_layout.addStretch() # Bottom stretch

        # 2b. Presets - Grid Layout
        presets_layout = QVBoxLayout()
        presets_layout.addStretch() # Top stretch for vertical centering
        presets_lbl = QLabel("QUICK PRESETS (Right-click to Save)")
        presets_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        
        self.presets_grid = QGridLayout()
        self.presets_grid.setSpacing(10)
        self.refresh_presets_ui() # Helper to draw presets

        presets_layout.addWidget(presets_lbl)
        presets_layout.addLayout(self.presets_grid)
        presets_layout.addStretch() # Bottom stretch

        # Add to controls layout
        controls_layout.addLayout(selectors_layout, stretch=1)
        controls_layout.addSpacing(20)
        controls_layout.addLayout(presets_layout, stretch=2)

        bottom_layout.addLayout(controls_layout)

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
    # UI Helpers
    # ------------------------------------------------------------------
    def update_mm_per_px(self, val):
        try:
            self.mm_per_px = float(val)
        except ValueError:
            pass # Ignore invalid input while typing

    def refresh_presets_ui(self):
        """Rebuilds the preset grid."""
        # Clear existing items
        while self.presets_grid.count():
            child = self.presets_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        row, col = 0, 0
        for i, p in enumerate(self.presets):
            label = p["label"]
            model = p["model"]
            size = p["size"]
            
            btn = QPushButton(f"{label}\n{size}")
            btn.setFixedSize(100, 100) # Bigger presets
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, idx=i: self.show_preset_menu(pos, idx))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #333;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: #444;
                    border-color: #666;
                }
                QPushButton:pressed {
                    background: #222;
                }
            """)
            btn.setToolTip(f"Set {model} / {size}\nRight-click to save current selection here")
            btn.clicked.connect(lambda _, m=model, s=size: self.set_preset(m, s))
            
            self.presets_grid.addWidget(btn, row, col)
            col += 1
            if col > 3: # 4 columns max
                col = 0
                row += 1

    def show_settings_menu(self):
        # Show menu under the button
        self.settings_menu.exec(self.settings_button.mapToGlobal(self.settings_button.rect().bottomLeft()))

    def show_preset_menu(self, pos, index):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: white;
                border: 1px solid #555;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #444;
            }
        """)

        current_model = self.model_select.currentText()
        current_size = self.size_select.currentText()

        save_action = QAction(f"Save '{current_model} - {current_size}' to this preset", self)
        save_action.triggered.connect(lambda: self.update_preset(index, current_model, current_size))
        menu.addAction(save_action)

        # Find the button that triggered this to map position
        # But pos is passed from signal, which is relative to widget.
        # We need to find the sender widget.
        # Actually, we can just use QCursor.pos() or mapToGlobal if we had the widget reference easily.
        # Since we connected lambda with idx, we don't have the widget ref directly in args unless we iterate.
        # Simpler: use QCursor.pos()
        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def update_preset(self, index, model, size):
        if 0 <= index < len(self.presets):
            # Update data
            self.presets[index]["model"] = model
            self.presets[index]["size"] = size
            # Update label to match model/size or keep custom label? 
            # User asked "customize model and size". 
            # Let's update the label to be the Model name (truncated) + Size for clarity
            # Or just keep the original label (e.g. "A-38")?
            # If I change the content, the label "A-38" might be misleading if it's now "Model B - 42".
            # So I should probably update the label too.
            # Let's make a simple label: "{Model}-{Size}"
            new_label = f"{model[:1]}-{size}" # First letter of model - size
            self.presets[index]["label"] = new_label
            
            self.refresh_presets_ui()

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

            # Setup font
            font = painter.font()
            font.setPointSize(24)  # Bigger font
            font.setBold(True)
            painter.setFont(font)

            # Calculate box size based on text
            fm = painter.fontMetrics()
            max_width = 0
            total_height = 20  # padding
            for line in self.last_results_text:
                max_width = max(max_width, fm.horizontalAdvance(line))
                total_height += fm.height() + 10

            # Draw semi-transparent background
            bg_rect_width = max_width + 40
            painter.fillRect(20, 20, bg_rect_width, total_height, QColor(0, 0, 0, 200))

            # Draw text
            y = 20 + fm.ascent() + 10
            for line in self.last_results_text:
                if "Result" in line:
                    if self.last_pass_fail == "PASS":
                        painter.setPen(QColor(0, 255, 0))  # Bright Green
                    else:
                        painter.setPen(QColor(255, 50, 50))  # Bright Red
                else:
                    painter.setPen(QColor(255, 255, 255))

                painter.drawText(40, y, line)
                y += fm.height() + 10

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
            mm_per_px=self.mm_per_px,
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
            length_mm = r.get("real_length_mm")
            length_px = r.get("px_length")
            width  = r.get("real_width_cm")
            pf     = r.get("pass_fail")

            self.last_results_text = [
                f"Length : {length:.1f} cm" if length else "Length : -",
                f"Length - mm : {length_mm} mm" if length else "Length mm : -",
                f"Length - px : {length_px} px" if length else "Length px : -",
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

