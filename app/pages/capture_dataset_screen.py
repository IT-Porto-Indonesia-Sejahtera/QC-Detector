import cv2
import os
import time
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QMetaObject, Q_ARG, Qt as QtCore_Qt
from PySide6.QtGui import QPixmap, QImage

# Import PLC Modbus trigger
try:
    from input.plc_modbus_trigger import PLCModbusTrigger, ModbusConfig, check_pymodbus_available
    PLC_AVAILABLE = check_pymodbus_available()
except ImportError:
    PLC_AVAILABLE = False

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
        
        # -----------------------------------------------------------------
        # PLC Modbus Trigger
        # -----------------------------------------------------------------
        self.plc_trigger = None
        self.plc_status_label = QLabel("PLC: Not connected")
        self.plc_status_label.setStyleSheet("color: #888; font-size: 12px;")
        top_bar.addWidget(self.plc_status_label)
        
        self._init_plc_trigger()
    
    def _init_plc_trigger(self):
        """Initialize PLC Modbus trigger"""
        if not PLC_AVAILABLE:
            print("[PLC] pymodbus not available. Install with: pip install pymodbus")
            self.plc_status_label.setText("PLC: pymodbus not installed")
            return
        
        try:
            config = ModbusConfig(
                connection_type="rtu",
                serial_port="COM7",
                baudrate=9600,
                parity="E",
                stopbits=1,
                bytesize=8,
                slave_id=1,
                register_address=12,
                register_type="holding",
                poll_interval_ms=100
            )
            
            self.plc_trigger = PLCModbusTrigger(config)
            self.plc_trigger.on_trigger = self._on_plc_trigger
            self.plc_trigger.on_value_update = self._on_plc_value_update
            self.plc_trigger.on_connection_change = self._on_plc_connection_change
            
            print("[PLC] Modbus trigger initialized")
            
        except Exception as e:
            print(f"[PLC] Failed to initialize: {e}")
            self.plc_status_label.setText(f"PLC: Init error")
    
    def _on_plc_trigger(self):
        """Called when PLC trigger fires (value changed 0 -> 1)"""
        print("[PLC] TRIGGER FIRED! Capturing image...")
        # Use QTimer to call capture_image on the main thread
        QTimer.singleShot(0, self.capture_image)
    
    def _on_plc_value_update(self, value):
        """Called when PLC register value is read"""
        print(f"[PLC] Register value: {value}")
    
    def _on_plc_connection_change(self, connected, message):
        """Called when PLC connection status changes"""
        print(f"[PLC] Connection: {message}")
        if connected:
            self.plc_status_label.setText(f"PLC: Connected")
            self.plc_status_label.setStyleSheet("color: #0f0; font-size: 12px;")
        else:
            self.plc_status_label.setText(f"PLC: {message}")
            self.plc_status_label.setStyleSheet("color: #f00; font-size: 12px;")

    def detect_cameras(self, max_test=3):
        """Detect available cameras with timeout to prevent freezing"""
        cams = []
        for i in range(max_test):
            try:
                # Use DirectShow on Windows for faster detection
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 1000)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        cams.append(str(i))
                else:
                    cap.release()
            except Exception:
                continue
        return cams if cams else ["No cameras found"]

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
        
        # Start PLC trigger
        if self.plc_trigger:
            print("[PLC] Starting Modbus polling...")
            self.plc_trigger.start()
        
        super().showEvent(event)

    def hideEvent(self, event):
        """Ensure camera and PLC are released when widget is hidden."""
        # Stop PLC trigger
        if self.plc_trigger:
            print("[PLC] Stopping Modbus polling...")
            self.plc_trigger.stop()
        
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
        # Stop and disconnect PLC trigger
        if self.plc_trigger:
            self.plc_trigger.disconnect()
        
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
        # Stop PLC trigger
        if self.plc_trigger:
            self.plc_trigger.stop()
        
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
