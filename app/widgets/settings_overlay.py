import os
import threading
from datetime import datetime
import cv2
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QImage, QPixmap
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ip_camera_discovery import get_discovery, DiscoveredCamera
from project_utilities.json_utility import JsonUtility

class SettingsOverlay(BaseOverlay):
    """Settings overlay for application configuration"""
    
    settings_saved = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        # Test Camera State
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
        # IP Camera Discovery State
        self.discovered_cameras = []
        self.is_scanning = False
        self.available_cameras = []  # Detected USB cameras
        self.camera_thread = None  # For background camera operations
        
        # Make content box larger for settings
        self.content_box.setFixedSize(900, 650)
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: 15px;
            }}
        """)
        
        self.load_settings()
        self.detect_available_cameras()  # Detect cameras before UI init
        self.init_ui()
        
    def load_settings(self):
        """Load settings from file"""
        settings_file = os.path.join("output", "settings", "app_settings.json")
        self.settings = JsonUtility.load_from_json(settings_file)
        
        if not self.settings:
            self.settings = {
                "camera_index": 0,
                "mm_per_px": 0.2123459,
                "sensor_delay": 0.2123459,
                "fetch_status": "success",
                "last_fetched": datetime.now().strftime("%d/%m/%Y"),
                "ip_camera_username": "",
                "ip_camera_password": "",
                "paths": {
                    "profile": "C://User/test/asd/",
                    "settings": "C://User/test/asd/",
                    "db": "C://User/test/asd/",
                }
            }
    
    def detect_available_cameras(self):
        """Quickly detect available USB cameras (runs at init)"""
        self.available_cameras = []
        self.camera_detection_error = None
        
        # Check first 3 camera indices (0-2) for speed
        for idx in range(3):
            try:
                # Use DirectShow backend on Windows for faster detection
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                
                # Set timeout properties to avoid hanging
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 1000)  # 1 second timeout
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1000)
                
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        self.available_cameras.append(idx)
                else:
                    cap.release()
            except Exception as e:
                self.camera_detection_error = str(e)
                continue
        
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        btn_back = QPushButton("❮")
        btn_back.setFixedSize(60, 60)
        btn_back.setStyleSheet(f"border: none; font-size: 24px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Settings")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {self.theme['text_main']};")
        
        btn_save = QPushButton("Save")
        btn_save.setFixedSize(120, 50)
        btn_save.setStyleSheet(f"""
            background-color: #F5F5F5;
            border-radius: 8px;
            font-weight: bold;
            color: #333333;
            font-size: 18px;
        """)
        btn_save.clicked.connect(self.save_settings_clicked)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_save)
        layout.addLayout(header)
        
        # Main content - two columns
        content = QHBoxLayout()
        content.setSpacing(30)
        
        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        
        # Camera preview placeholder
        self.preview_box = QLabel("Test Camera\nPreview")
        self.preview_box.setAlignment(Qt.AlignCenter)
        self.preview_box.setFixedSize(450, 300)
        self.preview_box.setStyleSheet(f"""
            background-color: #E0E0E0; 
            border-radius: 10px;
            color: #999999;
            font-size: 18px; 
            font-weight: bold;
        """)
        left_col.addWidget(self.preview_box)
        
        # Preview Controls
        preview_ctrls = QHBoxLayout()
        
        self.btn_preview = QPushButton("Start Test Feed")
        self.btn_preview.setFixedHeight(36)
        self.btn_preview.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            border-radius: 8px;
            font-weight: bold;
        """)
        self.btn_preview.clicked.connect(self.toggle_preview)
        
        preview_ctrls.addWidget(self.btn_preview)
        left_col.addLayout(preview_ctrls)
        
        # Camera selector
        camera_row = QVBoxLayout()
        camera_row.setSpacing(5)
        
        lbl_camera = QLabel("Camera Source")
        lbl_camera.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 16px; font-weight: bold;")
        
        cam_input_row = QHBoxLayout()
        
        self.camera_combo = QComboBox()
        # Populate with detected cameras
        if self.available_cameras:
            for idx in self.available_cameras:
                self.camera_combo.addItem(f"Camera {idx} (detected)", idx)
        else:
            self.camera_combo.addItem("No cameras detected", -1)
        self.camera_combo.addItem("IP Camera", "ip")
        self.camera_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 14px;
            }}
        """)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_combo_change)
        
        cam_input_row.addWidget(self.camera_combo, 1)
        
        camera_row.addWidget(lbl_camera)
        camera_row.addLayout(cam_input_row)

        # =========== IP Camera Section (Hidden by default) ===========
        self.ip_camera_section = QWidget()
        ip_camera_layout = QVBoxLayout(self.ip_camera_section)
        ip_camera_layout.setContentsMargins(0, 5, 0, 0)
        ip_camera_layout.setSpacing(8)
        
        # Scan button and discovered cameras
        scan_row = QHBoxLayout()
        
        self.btn_scan_cameras = QPushButton("🔍 Scan Network")
        self.btn_scan_cameras.setFixedHeight(36)
        self.btn_scan_cameras.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_scan_cameras.clicked.connect(self.scan_for_cameras)
        
        self.discovered_combo = QComboBox()
        self.discovered_combo.addItem("No cameras found - click Scan")
        self.discovered_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 13px;
            }}
        """)
        self.discovered_combo.currentIndexChanged.connect(self.on_discovered_camera_selected)
        
        scan_row.addWidget(self.btn_scan_cameras)
        scan_row.addWidget(self.discovered_combo, 1)
        ip_camera_layout.addLayout(scan_row)
        
        # Custom URL Input
        self.camera_url_input = QLineEdit()
        self.camera_url_input.setPlaceholderText("Or enter manually: rtsp://ip:port/path")
        self.camera_url_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 14px;
            }}
        """)
        ip_camera_layout.addWidget(self.camera_url_input)
        
        # Username/Password row
        creds_row = QHBoxLayout()
        creds_row.setSpacing(10)
        
        lbl_user = QLabel("User:")
        lbl_user.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 13px;")
        lbl_user.setFixedWidth(40)
        
        self.ip_username_input = QLineEdit()
        self.ip_username_input.setPlaceholderText("username")
        self.ip_username_input.setText(self.settings.get("ip_camera_username", ""))
        self.ip_username_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 6px 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                color: #333333;
                font-size: 13px;
            }}
        """)
        
        lbl_pass = QLabel("Pass:")
        lbl_pass.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 13px;")
        lbl_pass.setFixedWidth(40)
        
        self.ip_password_input = QLineEdit()
        self.ip_password_input.setPlaceholderText("password")
        self.ip_password_input.setEchoMode(QLineEdit.Password)
        self.ip_password_input.setText(self.settings.get("ip_camera_password", ""))
        self.ip_password_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 6px 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                color: #333333;
                font-size: 13px;
            }}
        """)
        
        creds_row.addWidget(lbl_user)
        creds_row.addWidget(self.ip_username_input, 1)
        creds_row.addWidget(lbl_pass)
        creds_row.addWidget(self.ip_password_input, 1)
        ip_camera_layout.addLayout(creds_row)
        
        # Connection status
        self.connection_status = QLabel("")
        self.connection_status.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
        ip_camera_layout.addWidget(self.connection_status)
        
        self.ip_camera_section.setVisible(False)
        camera_row.addWidget(self.ip_camera_section)
        # =========== End IP Camera Section ===========
        
        left_col.addLayout(camera_row)
        
        # Init Camera Selection State
        curr_idx = self.settings.get("camera_index", 0)
        self.set_camera_ui_state(curr_idx)
        
        # mm/px row
        mmpx_row = QHBoxLayout()
        lbl_mmpx = QLabel("mm/px")
        lbl_mmpx.setFixedWidth(80)
        lbl_mmpx.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 16px; font-weight: bold;")
        
        self.mmpx_input = QLineEdit()
        self.mmpx_input.setText(str(self.settings.get("mm_per_px", 0.2123459)))
        self.mmpx_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 14px;
            }}
        """)
        
        btn_auto = QPushButton("auto")
        btn_auto.setFixedSize(70, 36)
        btn_auto.setStyleSheet("""
            background-color: #F5F5F5;
            border-radius: 8px;
            color: #333333;
            font-size: 14px;
        """)
        # btn_auto.clicked.connect(self.auto_calibrate) # Future feature
        
        mmpx_row.addWidget(lbl_mmpx)
        mmpx_row.addWidget(self.mmpx_input)
        mmpx_row.addWidget(btn_auto)
        left_col.addLayout(mmpx_row)
        
        left_col.addStretch()
        content.addLayout(left_col)
        
        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(15)
        
        # Fetch Status
        status_row = self.create_info_row("Fetch Status", self.settings.get("fetch_status", "success"), button_text="")
        right_col.addLayout(status_row)
        
        # Last Fetched
        fetch_row = self.create_info_row("Last Fetched : " + self.settings.get("last_fetched", "22/12/2025"), "", button_text="refetch")
        right_col.addLayout(fetch_row)
        
        # Sensor Delay
        delay_row = self.create_input_row("Sensor\nDelay", str(self.settings.get("sensor_delay", 0.2123459)), "ms")
        self.delay_input = delay_row[1]
        right_col.addLayout(delay_row[0])
        
        # Location/Path Settings header
        path_header = QLabel("Location/Path Settings")
        path_header.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 16px; font-weight: bold; margin-top: 10px;")
        right_col.addWidget(path_header)
        
        # Path inputs
        paths = self.settings.get("paths", {})
        profile_row = self.create_path_row("Profile", paths.get("profile", "C://User/test/asd/"))
        self.profile_input = profile_row[1]
        right_col.addLayout(profile_row[0])
        
        settings_row = self.create_path_row("Settings", paths.get("settings", "C://User/test/asd/"))
        self.settings_input = settings_row[1]
        right_col.addLayout(settings_row[0])
        
        db_row = self.create_path_row("DB", paths.get("db", "C://User/test/asd/"))
        self.db_input = db_row[1]
        right_col.addLayout(db_row[0])
        
        results_row = self.create_path_row("Results", paths.get("results", "C://User/test/asd/"))
        self.results_input = results_row[1]
        right_col.addLayout(results_row[0])
        
        right_col.addStretch()
        content.addLayout(right_col)
        
        layout.addLayout(content)
        
    def create_info_row(self, label_text, value_text, button_text=""):
        """Create a row with label, value, and optional button"""
        row = QHBoxLayout()
        row.setSpacing(10)
        
        lbl = QLabel(label_text)
        lbl.setFixedWidth(120)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14px; font-weight: bold;")
        
        value = QLabel(value_text)
        value.setStyleSheet("background-color: #F5F5F5; padding: 8px; border-radius: 8px; color: #333333; font-size: 14px;")
        
        row.addWidget(lbl)
        row.addWidget(value, 1)
        
        if button_text:
            btn = QPushButton(button_text)
            btn.setFixedSize(80, 36)
            btn.setStyleSheet("background-color: #F5F5F5; border-radius: 8px; color: #333333; font-size: 14px;")
            row.addWidget(btn)
        
        return row
    
    def create_input_row(self, label_text, value, suffix=""):
        """Create a row with label, input, and suffix"""
        row = QHBoxLayout()
        row.setSpacing(10)
        
        lbl = QLabel(label_text)
        lbl.setFixedWidth(120)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14px; font-weight: bold;")
        
        input_field = QLineEdit()
        input_field.setText(value)
        input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 14px;
            }}
        """)
        
        row.addWidget(lbl)
        row.addWidget(input_field, 1)
        
        if suffix:
            suffix_lbl = QLabel(suffix)
            suffix_lbl.setFixedWidth(30)
            suffix_lbl.setStyleSheet("color: #999999; font-size: 14px;")
            row.addWidget(suffix_lbl)
        
        return (row, input_field)
    
    def create_path_row(self, label_text, value):
        """Create a row for path input"""
        row = QHBoxLayout()
        row.setSpacing(10)
        
        lbl = QLabel(label_text)
        lbl.setFixedWidth(70)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14px; font-weight: bold;")
        
        input_field = QLineEdit()
        input_field.setText(value)
        input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                background-color: white;
                color: #333333;
                font-size: 14px;
            }}
        """)
        
        btn = QPushButton("...")
        btn.setFixedSize(40, 36)
        btn.setStyleSheet("background-color: #F5F5F5; border-radius: 8px; color: #333333; font-size: 14px;")
        
        row.addWidget(lbl)
        row.addWidget(input_field, 1)
        row.addWidget(btn)
        
        return (row, input_field)
    
    # -------------------------------------------------------------------------
    # Camera Logic
    # -------------------------------------------------------------------------
    
    def set_camera_ui_state(self, val):
        """Populate UI based on current settings value"""
        if isinstance(val, int) and val >= 0:
            # Find combo item with matching camera index
            found = False
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == val:
                    self.camera_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found and self.camera_combo.count() > 0:
                self.camera_combo.setCurrentIndex(0)  # Default to first
            self.ip_camera_section.setVisible(False)
            self.camera_url_input.setText("")
        else:
            # IP Camera - find and select IP Camera option
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == "ip":
                    self.camera_combo.setCurrentIndex(i)
                    break
            self.ip_camera_section.setVisible(True)
            self.camera_url_input.setText(str(val))

    def on_camera_combo_change(self, index):
        current_data = self.camera_combo.currentData()
        if current_data == "ip":  # IP Camera
            self.ip_camera_section.setVisible(True)
        else:
            self.ip_camera_section.setVisible(False)
            
        # Restart preview if running
        if self.timer.isActive():
            self.stop_preview()
            self.start_preview()
    
    def scan_for_cameras(self):
        """Scan network for IP cameras"""
        if self.is_scanning:
            return
            
        self.is_scanning = True
        self.btn_scan_cameras.setText("⏳ Scanning...")
        self.btn_scan_cameras.setEnabled(False)
        self.connection_status.setText("Scanning network for cameras...")
        self.connection_status.setStyleSheet("color: #2196F3; font-size: 12px; font-style: italic;")
        
        # Run discovery in background
        discovery = get_discovery()
        discovery.discover_cameras_async(
            timeout=5.0,
            callback=self._on_cameras_discovered
        )
    
    def _on_cameras_discovered(self, cameras):
        """Callback when camera discovery completes"""
        self.discovered_cameras = cameras
        self.is_scanning = False
        
        # Update UI (must be done via timer for thread safety)
        QTimer.singleShot(0, self._update_discovered_cameras_ui)
    
    def _update_discovered_cameras_ui(self):
        """Update the discovered cameras dropdown"""
        self.btn_scan_cameras.setText("🔍 Scan Network")
        self.btn_scan_cameras.setEnabled(True)
        
        self.discovered_combo.clear()
        
        if self.discovered_cameras:
            for cam in self.discovered_cameras:
                self.discovered_combo.addItem(str(cam), cam)
            self.connection_status.setText(f"Found {len(self.discovered_cameras)} camera(s)")
            self.connection_status.setStyleSheet("color: #4CAF50; font-size: 12px; font-style: italic;")
        else:
            self.discovered_combo.addItem("No cameras found")
            self.connection_status.setText("No cameras found. Try manual entry.")
            self.connection_status.setStyleSheet("color: #FF9800; font-size: 12px; font-style: italic;")
    
    def on_discovered_camera_selected(self, index):
        """When a discovered camera is selected, populate the URL field"""
        if index < 0 or not self.discovered_cameras:
            return
            
        if index < len(self.discovered_cameras):
            cam = self.discovered_cameras[index]
            # Build RTSP URL without credentials (user will add them)
            url = f"rtsp://{cam.ip}:{cam.port}{cam.rtsp_path}"
            self.camera_url_input.setText(url)
            self.connection_status.setText(f"Selected: {cam}")
            self.connection_status.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
            
    def get_selected_camera_source(self):
        """Get the camera source - either index or RTSP URL with credentials"""
        # Get the data associated with current selection
        current_data = self.camera_combo.currentData()
        
        # IP Camera selected
        if current_data == "ip":
            txt = self.camera_url_input.text().strip()
            
            # If no URL entered, try to build from discovered camera
            if not txt and self.discovered_cameras:
                combo_idx = self.discovered_combo.currentIndex()
                if combo_idx >= 0 and combo_idx < len(self.discovered_cameras):
                    cam = self.discovered_cameras[combo_idx]
                    username = self.ip_username_input.text().strip()
                    password = self.ip_password_input.text().strip()
                    return cam.get_rtsp_url(username, password)
            
            # If URL is provided, inject credentials if needed
            if txt:
                username = self.ip_username_input.text().strip()
                password = self.ip_password_input.text().strip()
                
                # If URL already has credentials, use as-is
                if "@" in txt:
                    return txt
                
                # Inject credentials into rtsp:// URL
                if username and password and txt.startswith("rtsp://"):
                    return txt.replace("rtsp://", f"rtsp://{username}:{password}@", 1)
                
                # Try to convert to int if it's a number string
                if txt.isdigit():
                    return int(txt)
                return txt
            
            return 0  # Default fallback
        elif isinstance(current_data, int) and current_data >= 0:
            # USB camera index
            return current_data
        else:
            return 0  # Fallback

    def toggle_preview(self):
        if self.timer.isActive():
            self.stop_preview()
        else:
            self.start_preview()
            
    def start_preview(self):
        source = self.get_selected_camera_source()
        self.frame_fail_count = 0  # Track consecutive frame failures
        
        try:
            self.cap = cv2.VideoCapture(source)
            
            # Give camera time to initialize
            if not self.cap.isOpened():
                if isinstance(source, int):
                    self.preview_box.setText(f"Camera {source} not found.\nTry a different source or\nconnect a camera.")
                else:
                    self.preview_box.setText("Failed to connect.\nCheck URL and credentials.")
                self.preview_box.setStyleSheet("""
                    background-color: #FFEBEE; 
                    border-radius: 10px;
                    color: #C62828;
                    font-size: 16px; 
                    font-weight: bold;
                """)
                return
            
            self.timer.start(30)  # 30ms interval ~33 fps
            self.btn_preview.setText("Stop Test Feed")
            self.btn_preview.setStyleSheet("""
                background-color: #F44336;
                color: white;
                border-radius: 8px;
                font-weight: bold;
            """)
        except Exception as e:
            self.preview_box.setText(f"Error: {str(e)}")
            self.preview_box.setStyleSheet("""
                background-color: #FFEBEE; 
                border-radius: 10px;
                color: #C62828;
                font-size: 14px; 
                font-weight: bold;
            """)
            
    def stop_preview(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
        self.preview_box.setText("Test Camera\nPreview")
        self.preview_box.setStyleSheet("""
            background-color: #E0E0E0; 
            border-radius: 10px;
            color: #999999;
            font-size: 18px; 
            font-weight: bold;
        """)
        self.preview_box.setPixmap(QPixmap())  # Clear
        self.btn_preview.setText("Start Test Feed")
        self.btn_preview.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            border-radius: 8px;
            font-weight: bold;
        """)

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret:
            # Track consecutive failures
            self.frame_fail_count = getattr(self, 'frame_fail_count', 0) + 1
            if self.frame_fail_count >= 10:
                self.stop_preview()
                self.preview_box.setText("Connection lost.\nCheck camera or network.")
                self.preview_box.setStyleSheet("""
                    background-color: #FFF3E0; 
                    border-radius: 10px;
                    color: #E65100;
                    font-size: 16px; 
                    font-weight: bold;
                """)
            return
        
        # Reset failure counter on successful frame
        self.frame_fail_count = 0
            
        # Convert to Pixmap
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        
        # Scale
        lbl_w = self.preview_box.width()
        lbl_h = self.preview_box.height()
        pix = pix.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_box.setPixmap(pix)
    
    def close_overlay(self):
        self.stop_preview()
        super().close_overlay()

    def save_settings_clicked(self):
        """Save settings to file"""
        self.settings["camera_index"] = self.get_selected_camera_source()
        self.settings["mm_per_px"] = float(self.mmpx_input.text())
        self.settings["sensor_delay"] = float(self.delay_input.text())
        self.settings["ip_camera_username"] = self.ip_username_input.text().strip()
        self.settings["ip_camera_password"] = self.ip_password_input.text().strip()
        self.settings["paths"] = {
            "profile": self.profile_input.text(),
            "settings": self.settings_input.text(),
            "db": self.db_input.text(),
            "results": self.results_input.text()
        }
        
        settings_file = os.path.join("output", "settings", "app_settings.json")
        JsonUtility.save_to_json(settings_file, self.settings)
        
        self.settings_saved.emit(self.settings)
        self.close_overlay()
