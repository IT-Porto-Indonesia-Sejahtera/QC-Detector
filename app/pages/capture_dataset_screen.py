import cv2
import os
import time
import numpy as np
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
from app.utils.camera_utils import open_video_capture
from app.utils.capture_thread import VideoCaptureThread
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling

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
        
        # Load settings
        self.settings = JsonUtility.load_from_json(os.path.join("output", "settings", "app_settings.json")) or {}
        
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
        self.cam_select.setFixedWidth(UIScaling.scale(200))
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.currentIndexChanged.connect(self.change_camera)
        
        cam_select_padding = UIScaling.scale(5)
        self.cam_select.setStyleSheet(f"""
            QComboBox {{
                padding: {cam_select_padding}px;
                border: 1px solid #555;
                border-radius: 5px;
                background: #333;
                color: white;
            }}
            QComboBox::drop-down {{ border: 0px; }}
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
        back_btn_size = UIScaling.scale(40)
        back_btn_font_size = UIScaling.scale_font(18)
        self.back_button.setFixedSize(back_btn_size, back_btn_size)
        self.back_button.setStyleSheet(f"""
            QPushButton {{
                background: #444;
                color: white;
                font-weight: bold;
                border-radius: {back_btn_size // 2}px;
                font-size: {back_btn_font_size}px;
            }}
            QPushButton:hover {{ background: #666; }}
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
        bottom_container.setMinimumHeight(UIScaling.scale(100))
        bottom_container.setStyleSheet("background: #1A1A1A; border-radius: 10px;")
        
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(15, 15, 15, 15)
        bottom_layout.setSpacing(UIScaling.scale(20))

        # Capture Button
        self.capture_btn = QPushButton("📸 Capture Image")
        self.capture_btn.setMinimumHeight(UIScaling.scale(60))
        capture_btn_font_size = UIScaling.scale_font(20)
        self.capture_btn.setStyleSheet(f"""
            QPushButton {{
                background: #007AFF;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                font-size: {capture_btn_font_size}px;
            }}
            QPushButton:hover {{ background: #0056b3; }}
            QPushButton:pressed {{ background: #004080; }}
        """)
        self.capture_btn.clicked.connect(self.capture_image)
        
        bottom_layout.addWidget(self.capture_btn)

        main_layout.addWidget(bottom_container)
        self.setLayout(main_layout)

        # Camera system
        self.cap_thread = None
        self.live_frame = None
        
        # -----------------------------------------------------------------
        # PLC Modbus Trigger
        # -----------------------------------------------------------------
        self.plc_trigger = None
        self.plc_status_label = QLabel("PLC: Not connected")
        plc_status_font_size = UIScaling.scale_font(12)
        self.plc_status_label.setStyleSheet(f"color: #888; font-size: {plc_status_font_size}px;")
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
                serial_port=self.settings.get("plc_port", ""),
                baudrate=9600,
                parity="E",
                stopbits=1,
                bytesize=8,
                slave_id=1,
                register_address=int(self.settings.get("plc_trigger_reg", 12)),
                register_type="holding",
                poll_interval_ms=100
            )
            
            self.plc_trigger = PLCModbusTrigger(config)
            self.plc_trigger.on_trigger = self._on_plc_trigger
            self.plc_trigger.on_value_update = self._on_plc_value_update
            self.plc_trigger.on_connection_change = self._on_plc_connection_change
            
            print("[PLC] Modbus trigger initialized (connection deferred)")
        except Exception as e:
            print(f"[PLC] Failed to initialize: {e}")
            self.plc_status_label.setText(f"PLC: Init error")
    
    def _on_plc_trigger(self):
        """Called when PLC trigger fires"""
        print("[PLC] TRIGGER FIRED! Capturing image...")
        QTimer.singleShot(0, self.capture_image)
    
    def _on_plc_value_update(self, value):
        pass
    
    def _on_plc_connection_change(self, connected, message):
        if connected:
            self.plc_status_label.setText(f"PLC: Connected")
            self.plc_status_label.setStyleSheet("color: #0f0; font-size: 12px;")
        else:
            self.plc_status_label.setText(f"PLC: {message}")
            self.plc_status_label.setStyleSheet("color: #f00; font-size: 12px;")

    def detect_cameras(self, max_test=3):
        """Detect available cameras"""
        cams = []
        for i in range(max_test):
            try:
                cap = open_video_capture(i, timeout_ms=500)
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret: cams.append(str(i))
                elif cap:
                    cap.release()
            except Exception:
                continue
        
        if self.settings.get("ip_camera_presets"):
            cams.append("IP Camera")
            
        return cams if cams else ["No cameras found"]

    def change_camera(self, index=None):
        self.stop_camera()
        self.start_camera()

    def start_camera(self):
        if self.cap_thread is not None:
            return

        cam_text = self.cam_select.currentText() if self.cam_select.count() > 0 else "0"
        try:
            if cam_text == "IP Camera":
                presets = self.settings.get("ip_camera_presets", [])
                active_id = self.settings.get("active_ip_preset_id")
                cam_source = next((p for p in presets if p["id"] == active_id), presets[0] if presets else 0)
            else:
                cam_source = int(cam_text)
        except Exception:
            cam_source = 0

        is_ip = (cam_text == "IP Camera")
        self.cap_thread = VideoCaptureThread(cam_source, is_ip)
        self.cap_thread.frame_ready.connect(self.on_frame_received)
        self.cap_thread.start()
        
        # Start PLC trigger in background
        if self.plc_trigger:
            threading.Thread(target=self.plc_trigger.start, daemon=True).start()

    def on_frame_received(self, frame):
        self.live_frame = frame.copy()
        pix = self.cv2_to_pixmap(self.live_frame, self.big_label.width(), self.big_label.height())
        self.big_label.setPixmap(pix)

    def showEvent(self, event):
        """Refresh camera list and start."""
        # Reload settings to get latest camera_index
        self.settings = JsonUtility.load_from_json(os.path.join("output", "settings", "app_settings.json")) or {}
        
        current_cam = self.cam_select.currentText()
        self.cam_select.blockSignals(True)
        self.cam_select.clear()
        self.cam_select.addItems(self.detect_cameras())
        self.cam_select.blockSignals(False)
        
        # Check if camera_index is set to "ip" to auto-select IP Camera
        camera_index = self.settings.get("camera_index", 0)
        if camera_index == "ip" or camera_index == "IP Camera":
            index = self.cam_select.findText("IP Camera")
        else:
            index = self.cam_select.findText(current_cam)
            
        if index >= 0:
            self.cam_select.setCurrentIndex(index)
        
        self.start_camera()
        super().showEvent(event)

    def stop_camera(self):
        if self.cap_thread:
            self.cap_thread.stop()
            self.cap_thread = None
        
        if self.plc_trigger:
            self.plc_trigger.stop()

    def hideEvent(self, event):
        self.stop_camera()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

    def go_back(self):
        self.stop_camera()
        if self.parent_widget:
            self.parent_widget.go_back()

    def cv2_to_pixmap(self, img, target_width, target_height):
        if img is None: return QPixmap()
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, _ = img_rgb.shape
            scale = min(max(1e-6, target_width / w), max(1e-6, target_height / h))
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w == 0 or new_h == 0: return QPixmap()
            resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            qimg = QImage(resized.data, new_w, new_h, 3 * new_w, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception:
            return QPixmap()

    def capture_image(self):
        if self.live_frame is None: return
        timestamp = int(time.time() * 1000)
        filename = f"dataset_{timestamp}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        cv2.imwrite(filepath, self.live_frame)
        self.capture_btn.setText("Saved!")
        QTimer.singleShot(1000, lambda: self.capture_btn.setText("📸 Capture Image"))
