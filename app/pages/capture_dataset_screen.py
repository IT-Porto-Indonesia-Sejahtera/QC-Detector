import cv2
import os
import time
import numpy as np
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QComboBox, QLineEdit, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
from app.utils.camera_utils import open_video_capture
from app.utils.capture_thread import VideoCaptureThread
from app.utils.consistency_test_thread import ConsistencyTestThread
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from model.measure_live_sandals import measure_live_sandals

# Import PLC Modbus trigger
try:
    from input.plc_modbus_trigger import PLCModbusTrigger, ModbusConfig, check_pymodbus_available
    PLC_AVAILABLE = check_pymodbus_available()
except ImportError:
    PLC_AVAILABLE = False

class CaptureDatasetScreen(QWidget):
    plc_capture_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowTitle("Capture Dataset")
        
        # Load settings
        self.settings = JsonUtility.load_from_json(os.path.join("output", "settings", "app_settings.json")) or {}
        
        # Ensure default output directory exists
        self.output_dir = self.settings.get("last_dataset_path") or os.path.join("output", "dataset")
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

        # Model Selector
        self.model_select = QComboBox()
        self.model_select.setFixedWidth(UIScaling.scale(150))
        self.model_select.addItems(["Standard (CV)", "YOLO v8", "FastSAM"])
        
        # Set default to YOLO as requested if available, else Standard
        # Simple string match logic
        self.model_select.setCurrentIndex(1) # YOLO
        
        self.model_select.setStyleSheet(f"""
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
        top_bar.addWidget(QLabel("Model: "))
        top_bar.addWidget(self.model_select)
        top_bar.addSpacing(15)
        top_bar.addWidget(QLabel("Camera: "))
        top_bar.addWidget(self.cam_select)
        
        main_layout.addLayout(top_bar)

        # --- BIG CAMERA AREA ---
        main_layout.addWidget(self.big_label)

        # --- BOTTOM AREA ---
        bottom_container = QFrame()
        bottom_container.setMinimumHeight(UIScaling.scale(140))
        bottom_container.setStyleSheet("background: #1A1A1A; border-radius: 10px;")
        
        bottom_v_layout = QVBoxLayout(bottom_container)
        bottom_v_layout.setContentsMargins(15, 15, 15, 15)
        bottom_v_layout.setSpacing(UIScaling.scale(10))

        # Folder Selection Row
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit(self.output_dir)
        self.folder_input.setStyleSheet("background: #333; color: white; border: 1px solid #555; padding: 8px; border-radius: 5px;")
        self.folder_input.textChanged.connect(self.update_output_dir)
        
        self.btn_browse = QPushButton("📁 Browse")
        self.btn_browse.setStyleSheet("background: #444; color: white; padding: 8px 15px; border-radius: 5px;")
        self.btn_browse.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(QLabel("Save Folder:"))
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(self.btn_browse)
        bottom_v_layout.addLayout(folder_layout)

        # Save Options Row
        options_layout = QHBoxLayout()
        self.chk_measure = QCheckBox("Save Measurement Result (Overlay)")
        self.chk_measure.setStyleSheet("color: white; font-weight: bold;")
        self.chk_measure.setChecked(self.settings.get("dataset_save_measurements", False))
        self.chk_measure.toggled.connect(self.update_save_options)
        options_layout.addWidget(self.chk_measure)
        
        # New: Capture images during consistency test
        self.chk_capture_images_test = QCheckBox("Capture Images during Consistency Test")
        self.chk_capture_images_test.setStyleSheet("color: #FFA000; font-weight: bold;")
        self.chk_capture_images_test.setChecked(False)
        options_layout.addWidget(self.chk_capture_images_test)
        
        bottom_v_layout.addLayout(options_layout)

        # Capture Control Row
        control_layout = QHBoxLayout()
        control_layout.setSpacing(UIScaling.scale(20))

        # PLC Toggle Button
        self.btn_plc_toggle = QPushButton("PLC Trigger: OFF")
        self.btn_plc_toggle.setMinimumHeight(UIScaling.scale(50))
        self.btn_plc_toggle.setStyleSheet("background: #444; color: #888; font-weight: bold; border-radius: 8px;")
        self.btn_plc_toggle.clicked.connect(self.toggle_plc)
        
        # Test Consistency Button
        self.test_btn = QPushButton("Test Consistency")
        self.test_btn.setMinimumHeight(UIScaling.scale(50))
        self.test_btn.setStyleSheet("background: #E65100; color: white; font-weight: bold; border-radius: 8px;")
        self.test_btn.clicked.connect(self.start_consistency_test)

        # Capture Button
        self.capture_btn = QPushButton("📸 Capture Image (Manual)")
        self.capture_btn.setMinimumHeight(UIScaling.scale(50))
        capture_btn_font_size = UIScaling.scale_font(18)
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
        
        control_layout.addWidget(self.btn_plc_toggle, 1)
        control_layout.addWidget(self.test_btn, 1)
        control_layout.addWidget(self.capture_btn, 2)
        bottom_v_layout.addLayout(control_layout)

        main_layout.addWidget(bottom_container)
        self.setLayout(main_layout)

        # Camera system
        self.cap_thread = None
        self.live_frame = None
        self.test_thread = None
        
        # -----------------------------------------------------------------
        # PLC Modbus Trigger
        # -----------------------------------------------------------------
        self.plc_trigger = None
        self.plc_running = False
        self.plc_status_label = QLabel("PLC: Disconnected")
        plc_status_font_size = UIScaling.scale_font(12)
        self.plc_status_label.setStyleSheet(f"color: #888; font-size: {plc_status_font_size}px;")
        top_bar.addWidget(self.plc_status_label)
        
        # Connect signal for thread-safe capture
        self.plc_capture_signal.connect(self.capture_image)
        
        self._init_plc_trigger()

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.output_dir)
        if path:
            self.folder_input.setText(path)
            self.output_dir = path
            # Save to settings for persistence
            self.settings["last_dataset_path"] = path
            JsonUtility.save_to_json(os.path.join("output", "settings", "app_settings.json"), self.settings)

    def update_output_dir(self, text):
        self.output_dir = text

    def toggle_plc(self):
        if not PLC_AVAILABLE:
            return
            
        if self.plc_running:
            self.stop_plc()
        else:
            self.start_plc()

    def start_plc(self):
        if not self.plc_trigger:
            self._init_plc_trigger()
            
        if self.plc_trigger:
            print("[Dataset] Starting PLC Trigger...")
            self.plc_running = True
            self.btn_plc_toggle.setText("PLC Trigger: ON")
            self.btn_plc_toggle.setStyleSheet("background: #2E7D32; color: white; font-weight: bold; border-radius: 8px;")
            threading.Thread(target=self.plc_trigger.start, daemon=True).start()

    def stop_plc(self):
        if self.plc_trigger:
            print("[Dataset] Stopping PLC Trigger...")
            self.plc_trigger.stop()
            self.plc_running = False
            self.btn_plc_toggle.setText("PLC Trigger: OFF")
            self.btn_plc_toggle.setStyleSheet("background: #444; color: #888; font-weight: bold; border-radius: 8px;")
            self.plc_status_label.setText("PLC: Disconnected")
            self.plc_status_label.setStyleSheet("color: #888; font-size: 12px;")

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
        """Called when PLC trigger fires (background thread)"""
        print("[PLC] TRIGGER FIRED! Emitting capture signal...")
        self.plc_capture_signal.emit()
    
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
        
        # Load params (ensure fresh)
        crop = self.settings.get("camera_crop", {})
        distortion = self.settings.get("lens_distortion", {})
        
        self.cap_thread = VideoCaptureThread(cam_source, is_ip, crop_params=crop, distortion_params=distortion)
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
        # Reload settings to get latest camera_index and folder
        self.settings = JsonUtility.load_from_json(os.path.join("output", "settings", "app_settings.json")) or {}
        
        # Update folder
        self.folder_input.setText(self.output_dir)
        
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
        
        self.stop_plc()

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
            h, w, ch = img_rgb.shape
            scale = min(max(1e-6, target_width / w), max(1e-6, target_height / h))
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w == 0 or new_h == 0: return QPixmap()
            resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            qimg = QImage(resized.data, new_w, new_h, 3 * new_w, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception:
            return QPixmap()

    def update_save_options(self, checked):
        self.settings["dataset_save_measurements"] = checked
        JsonUtility.save_to_json(os.path.join("output", "settings", "app_settings.json"), self.settings)

    def capture_image(self):
        print("[Dataset] capture_image method called")
        if self.live_frame is None: 
            print("[Dataset] No frame available yet")
            return
        
        try:
            # Ensure dir exists (it might have been typed manually)
            save_path = self.output_dir.strip()
            if not save_path:
                save_path = os.path.join("output", "dataset")
                
            abs_dir = os.path.abspath(save_path)
            os.makedirs(abs_dir, exist_ok=True)

            timestamp = int(time.time() * 1000)
            filename = f"dataset_{timestamp}.jpg"
            filepath = os.path.join(abs_dir, filename)
            
            # Decide what to save (Raw or Processed)
            frame_to_save = self.live_frame
            if self.chk_measure.isChecked():
                # Run measurement logic
                mmpx = self.settings.get("mm_per_px", 0.21)
                print(f"[Dataset] Running measurement overlay (mmpx: {mmpx})...")
                results, processed = measure_live_sandals(self.live_frame, mm_per_px=mmpx)
                frame_to_save = processed

            success = cv2.imwrite(filepath, frame_to_save)
            if success:
                print(f"[Dataset] SUCCESS! Saved to: {filepath}")
                self.capture_btn.setText("Saved!")
                QTimer.singleShot(1500, lambda: self.capture_btn.setText("📸 Capture Image (Manual)"))
            else:
                print(f"[Dataset] FAILED to write file: {filepath}")
                self.capture_btn.setText("Write Failed!")
        except Exception as e:
            print(f"[Dataset] CRITICAL ERROR during capture: {e}")
            import traceback
            traceback.print_exc()
            self.capture_btn.setText("System Error!")

    def start_consistency_test(self):
        if not self.cap_thread or not self.cap_thread.isRunning():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Camera is not running!")
            return

        from PySide6.QtWidgets import QInputDialog
        attempts, ok = QInputDialog.getInt(self, "Consistency Test", 
                                         "Number of attempts (frames):", 
                                         100, 10, 1000)
        if not ok:
            return

        # Map UI model selection to internal string
        model_map = {
            "Standard (CV)": "standard",
            "YOLO v8": "yolo",
            "FastSAM": "sam"
        }
        selected_text = self.model_select.currentText()
        model_type = model_map.get(selected_text, "standard")

        mmpx = self.settings.get("mm_per_px", 0.21)

        print(f"[Dataset] Starting Consistency Test: {attempts} attempts, model={model_type}")
        
        # Create thread
        self.test_thread = ConsistencyTestThread(
            video_thread=self.cap_thread,
            num_attempts=attempts,
            model_type=model_type,
            output_dir=self.output_dir,
            mm_per_px=mmpx,
            capture_images=self.chk_capture_images_test.isChecked()
        )
        
        self.test_thread.progress_update.connect(self.on_test_progress)
        self.test_thread.finished_test.connect(self.on_test_finished)
        self.test_thread.error_occurred.connect(self.on_test_error)
        
        # UI updates
        self.test_btn.setEnabled(False)
        self.capture_btn.setEnabled(False)
        self.test_btn.setText("Running...")
        
        self.test_thread.start()

    def on_test_progress(self, current, total):
        self.test_btn.setText(f"Running... {current}/{total}")

    def on_test_finished(self, file_path):
        from PySide6.QtWidgets import QMessageBox
        self.test_btn.setText("Test Consistency")
        self.test_btn.setEnabled(True)
        self.capture_btn.setEnabled(True)
        
        ext = "Excel file" if file_path.endswith(".xlsx") else "CSV file"
        QMessageBox.information(self, "Test Complete", f"Consistency test finished.\nSaved to {ext}:\n{file_path}")
        self.test_thread = None

    def on_test_error(self, err_msg):
        from PySide6.QtWidgets import QMessageBox
        self.test_btn.setText("Test Consistency")
        self.test_btn.setEnabled(True)
        self.capture_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Test Error", f"Error during test:\n{err_msg}")
        self.test_thread = None

