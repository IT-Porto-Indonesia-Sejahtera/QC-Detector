import os
import json
import threading
from datetime import datetime
import cv2
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QWidget, QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QImage, QPixmap
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ip_camera_discovery import get_discovery, DiscoveredCamera
from project_utilities.json_utility import JsonUtility
from app.utils.capture_thread import VideoCaptureThread
from app.utils.ui_scaling import UIScaling
from backend.get_product_sku import ProductSKUWorker
from app.utils import fetch_logger

class SettingsOverlay(BaseOverlay):
    """Settings overlay for application configuration"""
    
    settings_saved = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        self.cap_thread = None
        
        # IP Camera Discovery State
        self.discovered_cameras = []
        self.is_scanning = False
        self.available_cameras = []  # Detected USB cameras
        self.camera_thread = None  # For background camera operations
        
        # IP Presets State
        self.ip_presets = []
        self.current_preset = None
        
        # Make content box responsive for settings
        scaled_w = UIScaling.scale(900)
        scaled_h = UIScaling.scale(650)
        
        # Ensure it doesn't exceed 90% of screen
        screen_size = UIScaling.get_screen_size()
        max_w = int(screen_size.width() * 0.9)
        max_h = int(screen_size.height() * 0.9)
        
        self.content_box.setMinimumSize(UIScaling.scale(500), UIScaling.scale(400))
        self.content_box.setMaximumSize(min(scaled_w, max_w), min(scaled_h, max_h))
        self.content_box.resize(min(scaled_w, max_w), min(scaled_h, max_h))

        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: {UIScaling.scale(15)}px;
            }}
        """)
        
        self.load_settings()
        self.detect_available_cameras()  # Detect cameras before UI init
        self.setup_settings_ui()
        
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
                    "results": "C://User/test/asd/"
                },
                "ip_camera_presets": [],
                "active_ip_preset_id": None,
                "sensor_port": "",
                "plc_port": "",
                "plc_trigger_reg": 12,
                "plc_result_reg": 13,
                "layout_mode": "classic"
            }
        
        self.ip_presets = self.settings.get("ip_camera_presets", [])
        active_id = self.settings.get("active_ip_preset_id")
        
        # Initialize with a default preset if empty
        if not self.ip_presets:
            default_preset = {
                "id": "default-rtsp",
                "name": "Default RTSP",
                "protocol": "rtsp",
                "address": "192.168.1.64",
                "port": "554",
                "path": "/stream1",
                "username": self.settings.get("ip_camera_username", "admin"),
                "password": self.settings.get("ip_camera_password", "Porto.cctv"),
                "transport": "tcp"
            }
            self.ip_presets = [default_preset]
            self.settings["ip_camera_presets"] = self.ip_presets
            
        # Set current preset
        self.current_preset = next((p for p in self.ip_presets if p["id"] == active_id), self.ip_presets[0])
    
    def detect_available_cameras(self):
        """Quickly detect available USB cameras (runs at init)"""
        import time
        self.available_cameras = []
        self.camera_detection_error = None
        
        # Small delay to allow previous camera to fully release
        time.sleep(0.3)
        
        # Check first 3 camera indices (0-2) for speed
        for idx in range(3):
            try:
                # Use centralized utility for detection
                cap = open_video_capture(idx, timeout_ms=1000)
                
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        self.available_cameras.append(idx)
                elif cap:
                    cap.release()
            except Exception as e:
                self.camera_detection_error = str(e)
                continue
        
        # Fallback: If no cameras detected but settings has a valid camera index, include it
        if not self.available_cameras:
            saved_idx = self.settings.get("camera_index", 0)
            if isinstance(saved_idx, int) and saved_idx >= 0:
                self.available_cameras.append(saved_idx)
        
    def setup_settings_ui(self):
        # Alias for backward compatibility if any external callers still use init_ui
        self.init_ui = self.setup_settings_ui
        # Use a scroll area for the entire settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(20)
        
        scroll.setWidget(scroll_content)
        
        # Add the scroll area directly to the existing content_layout
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(scroll)
        
        # Styles
        input_padding = UIScaling.scale(10)
        input_radius = UIScaling.scale(8)
        input_font_size = UIScaling.scale_font(14)
        
        self.line_edit_style = f"""
            QLineEdit, QComboBox {{
                padding: {input_padding}px;
                border: 1px solid {self.theme['border']};
                border-radius: {input_radius}px;
                background-color: white;
                color: #333333;
                font-size: {input_font_size}px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #2196F3;
            }}
        """
        
        btn_sec_font_size = UIScaling.scale_font(14)
        btn_sec_padding_v = UIScaling.scale(8)
        btn_sec_padding_h = UIScaling.scale(15)
        
        self.btn_secondary_style = f"""
            QPushButton {{
                background-color: #F5F5F5;
                border-radius: {input_radius}px;
                color: #333333;
                font-size: {btn_sec_font_size}px;
                font-weight: bold;
                padding: {btn_sec_padding_v}px {btn_sec_padding_h}px;
            }}
            QPushButton:hover {{
                background-color: #EEEEEE;
            }}
        """

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(10, 10, 10, 0)
        
        btn_back = QPushButton("❮")
        btn_back_size = UIScaling.scale(45)
        btn_back_font_size = UIScaling.scale_font(20)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                border: none; 
                font-size: {btn_back_font_size}px; 
                font-weight: bold; 
                color: {self.theme['text_main']};
                background-color: #F5F5F5;
                border-radius: {btn_back_size // 2}px;
            }}
            QPushButton:hover {{ background-color: #EEEEEE; }}
        """)
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Application Settings")
        title_font_size = UIScaling.scale_font(24)
        lbl_title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; color: {self.theme['text_main']}; margin-left: 10px;")
        
        btn_save = QPushButton("Save Settings")
        btn_save_w = UIScaling.scale(160)
        btn_save_h = UIScaling.scale(45)
        btn_save_font_size = UIScaling.scale_font(16)
        btn_save.setFixedSize(btn_save_w, btn_save_h)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                border-radius: {UIScaling.scale(10)}px;
                font-weight: bold;
                color: white;
                font-size: {btn_save_font_size}px;
            }}
            QPushButton:hover {{ background-color: #1E88E5; }}
        """)
        btn_save.clicked.connect(self.save_settings_clicked)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(btn_save)
        self.main_layout.addLayout(header)

        # Content - Split into two columns
        columns = QHBoxLayout()
        columns.setSpacing(20)
        
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        
        right_col = QVBoxLayout()
        right_col.setSpacing(20)
        
        # --- LEFT COLUMN: Camera & Preview ---
        camera_card, card_layout = self.create_card("Camera Configuration")

        # Preview placeholder
        self.preview_box = QLabel("Test Camera\nPreview")
        self.preview_box.setAlignment(Qt.AlignCenter)
        self.preview_box.setFixedSize(UIScaling.scale(400), UIScaling.scale(250))
        preview_font_size = UIScaling.scale_font(16)
        self.preview_box.setStyleSheet(f"""
            background-color: #2D2D2D; 
            border-radius: {UIScaling.scale(10)}px;
            color: #CCCCCC;
            font-size: {preview_font_size}px; 
            font-weight: bold;
        """)
        card_layout.addWidget(self.preview_box, 0, Qt.AlignCenter)
        
        self.btn_preview = QPushButton("Start Test Feed")
        self.btn_preview.setFixedHeight(UIScaling.scale(40))
        self.btn_preview.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border-radius: {UIScaling.scale(8)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
        """)
        self.btn_preview.clicked.connect(self.toggle_preview)
        card_layout.addWidget(self.btn_preview)

        # Camera selector
        lbl_camera = QLabel("Camera Source Selection")
        lbl_cam_font_size = UIScaling.scale_font(13)
        lbl_camera.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: {lbl_cam_font_size}px; font-weight: bold;")
        card_layout.addWidget(lbl_camera)
        
        self.camera_combo = QComboBox()
        if self.available_cameras:
            for idx in self.available_cameras:
                self.camera_combo.addItem(f"USB Camera {idx}", idx)
        else:
            self.camera_combo.addItem("No USB cameras detected", -1)
        self.camera_combo.addItem("IP Network Camera", "ip")
        self.camera_combo.setStyleSheet(self.line_edit_style)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_combo_change)
        card_layout.addWidget(self.camera_combo)
        
        left_col.addWidget(camera_card)

        # IP Camera Section (Hidden by default)
        self.ip_camera_section, ip_layout = self.create_card("IP Camera Details", is_sub_card=True)

        # Preset Row
        preset_row = QHBoxLayout()
        self.ip_preset_combo = QComboBox()
        self.ip_preset_combo.setStyleSheet(self.line_edit_style)
        self.ip_preset_combo.currentIndexChanged.connect(self.on_ip_preset_change)
        
        self.btn_new_preset = QPushButton("+ New")
        self.btn_new_preset.setStyleSheet(self.btn_secondary_style)
        self.btn_new_preset.clicked.connect(self.add_new_preset)
        
        preset_row.addWidget(self.ip_preset_combo, 1)
        preset_row.addWidget(self.btn_new_preset)
        ip_layout.addLayout(preset_row)

        # Connection Params
        params_grid = QHBoxLayout()
        
        proto_v = QVBoxLayout()
        proto_v.addWidget(QLabel("Protocol"))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["rtsp", "http", "https", "rtmp", "rtmps"])
        self.protocol_combo.setStyleSheet(self.line_edit_style)
        proto_v.addWidget(self.protocol_combo)
        params_grid.addLayout(proto_v, 1)

        trans_v = QVBoxLayout()
        trans_v.addWidget(QLabel("Transport"))
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["tcp", "udp"])
        self.transport_combo.setStyleSheet(self.line_edit_style)
        trans_v.addWidget(self.transport_combo)
        params_grid.addLayout(trans_v, 1)
        
        ip_layout.addLayout(params_grid)

        # Host & Port
        host_row = QHBoxLayout()
        host_v = QVBoxLayout()
        host_v.addWidget(QLabel("IP Address / Hostname"))
        self.ip_address_input = QLineEdit()
        self.ip_address_input.setPlaceholderText("192.168.1.100")
        self.ip_address_input.setStyleSheet(self.line_edit_style)
        host_v.addWidget(self.ip_address_input)
        host_row.addLayout(host_v, 3)

        port_v = QVBoxLayout()
        port_v.addWidget(QLabel("Port"))
        self.ip_port_input = QLineEdit()
        self.ip_port_input.setPlaceholderText("554")
        self.ip_port_input.setStyleSheet(self.line_edit_style)
        port_v.addWidget(self.ip_port_input)
        host_row.addLayout(port_v, 1)
        ip_layout.addLayout(host_row)

        # Path
        path_v = QVBoxLayout()
        path_v.addWidget(QLabel("RTSP Path"))
        self.ip_path_input = QLineEdit()
        self.ip_path_input.setPlaceholderText("/live/ch1")
        self.ip_path_input.setStyleSheet(self.line_edit_style)
        path_v.addWidget(self.ip_path_input)
        ip_layout.addLayout(path_v)

        # Auth
        auth_row = QHBoxLayout()
        user_v = QVBoxLayout()
        user_v.addWidget(QLabel("Username"))
        self.ip_username_input = QLineEdit()
        self.ip_username_input.setStyleSheet(self.line_edit_style)
        user_v.addWidget(self.ip_username_input)
        auth_row.addLayout(user_v)

        pass_v = QVBoxLayout()
        pass_v.addWidget(QLabel("Password"))
        self.ip_password_input = QLineEdit()
        self.ip_password_input.setEchoMode(QLineEdit.Password)
        self.ip_password_input.setStyleSheet(self.line_edit_style)
        pass_v.addWidget(self.ip_password_input)
        auth_row.addLayout(pass_v)
        ip_layout.addLayout(auth_row)

        disc_group = QHBoxLayout()
        self.btn_scan_cameras = QPushButton("🔍 Scan Network")
        self.btn_scan_cameras.setFixedHeight(UIScaling.scale(40))
        self.btn_scan_cameras.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border-radius: {UIScaling.scale(8)}px;
                font-weight: bold;
                padding: 0 {UIScaling.scale(15)}px;
            }}
            QPushButton:hover {{ background-color: #1E88E5; }}
        """)
        self.btn_scan_cameras.clicked.connect(self.scan_for_cameras)
        
        self.discovered_combo = QComboBox()
        self.discovered_combo.addItem("-- Discovered Cameras --")
        self.discovered_combo.setStyleSheet(self.line_edit_style)
        self.discovered_combo.currentIndexChanged.connect(self.on_discovered_camera_selected)
        
        disc_group.addWidget(self.btn_scan_cameras)
        disc_group.addWidget(self.discovered_combo, 1)
        ip_layout.addLayout(disc_group)
        
        self.connection_status = QLabel("")
        conn_status_font_size = UIScaling.scale_font(11)
        self.connection_status.setStyleSheet(f"color: #666666; font-size: {conn_status_font_size}px;")
        ip_layout.addWidget(self.connection_status)

        left_col.addWidget(self.ip_camera_section)
        left_col.addStretch()

        # --- RIGHT COLUMN: Parameters & Paths ---
        # Parameters Card
        params_card, p_layout = self.create_card("Application Parameters")

        # Layout Mode
        layout_v = QVBoxLayout()
        layout_lbl = QLabel("App Layout Mode")
        l_font = UIScaling.scale_font(14)
        layout_lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {l_font}px; font-weight: bold;")
        layout_v.addWidget(layout_lbl)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Classic (2-Panel)", "Split (3-Panel)"])
        self.layout_combo.setStyleSheet(self.line_edit_style)
        # Set current value
        current_mode = self.settings.get("layout_mode", "classic")
        idx = 1 if current_mode == "split" else 0
        self.layout_combo.setCurrentIndex(idx)
        layout_v.addWidget(self.layout_combo)
        p_layout.addLayout(layout_v)

        mmpx_row, self.mmpx_input = self.create_input_row("Resolution (mm/px)", str(self.settings.get("mm_per_px", 0.21)), help_text="Pixel to real-world size conversion")
        p_layout.addLayout(mmpx_row)

        delay_row, self.delay_input = self.create_input_row("Sensor Delay (ms)", str(self.settings.get("sensor_delay", 0.2)), help_text="Time to wait for conveyor stability")
        p_layout.addLayout(delay_row)
        
        right_col.addWidget(params_card)

        # Path Settings Card
        paths_card, path_layout = self.create_card("Storage & Directories")

        paths = self.settings.get("paths", {})
        
        p_row, self.profile_input = self.create_path_row("Device Profiles", paths.get("profile", ""))
        path_layout.addLayout(p_row)
        
        s_row, self.settings_input = self.create_path_row("Configuration", paths.get("settings", ""))
        path_layout.addLayout(s_row)
        
        db_row, self.db_input = self.create_path_row("Database", paths.get("db", ""))
        path_layout.addLayout(db_row)
        
        r_row, self.results_input = self.create_path_row("Analysis Results", paths.get("results", ""))
        path_layout.addLayout(r_row)
        
        right_col.addWidget(paths_card)

        # System Info Card
        info_card, info_layout = self.create_card("System Information")
        
        status_row = self.create_info_row("Cloud Sync Status", self.settings.get("fetch_status", "Offline"))
        info_layout.addLayout(status_row)
        
        last_fetch = self.settings.get("last_fetched", "Never")
        self.last_fetch_label = QLabel(f"Last Updated: {last_fetch}")
        lbl_font_size = UIScaling.scale_font(13)
        self.last_fetch_label.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {lbl_font_size}px; font-weight: bold;")
        
        self.btn_fetch = QPushButton("Refresh Now")
        self.btn_fetch.setStyleSheet(self.btn_secondary_style)
        self.btn_fetch.clicked.connect(self.start_fetch_sku)
        
        fetch_row = QHBoxLayout()
        fetch_row.setContentsMargins(5, 5, 5, 5)
        fetch_row.addWidget(self.last_fetch_label, 1)
        fetch_row.addWidget(self.btn_fetch)
        info_layout.addLayout(fetch_row)
        
        # Worker reference
        self.sku_worker = None

        right_col.addWidget(info_card)
        
        # Hardware Integration Card
        hw_card, hw_layout = self.create_card("Hardware Integration")
        
        s_port_row, self.sensor_port_input = self.create_input_row("Sensor Serial Port", self.settings.get("sensor_port", ""), help_text="e.g. COM6 or /dev/ttyUSB0")
        hw_layout.addLayout(s_port_row)
        
        p_port_row, self.plc_port_input = self.create_input_row("PLC Serial Port", self.settings.get("plc_port", ""), help_text="e.g. COM7 or /dev/ttyUSB1")
        hw_layout.addLayout(p_port_row)
        
        hw_regs = QHBoxLayout()
        trig_v, self.plc_trig_input = self.create_input_row("Trigger Reg", str(self.settings.get("plc_trigger_reg", 12)))
        hw_regs.addLayout(trig_v)
        
        res_v, self.plc_res_input = self.create_input_row("Result Reg", str(self.settings.get("plc_result_reg", 13)))
        hw_regs.addLayout(res_v)
        hw_layout.addLayout(hw_regs)
        
        right_col.addWidget(hw_card)
        
        # Fetch Log Viewer Card
        log_card, log_layout = self.create_card("Fetch Activity Log")
        
        # Log viewer text area
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFixedHeight(UIScaling.scale(120))
        log_font_size = UIScaling.scale_font(11)
        self.log_viewer.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid {self.theme['border']};
                border-radius: {UIScaling.scale(6)}px;
                font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
                font-size: {log_font_size}px;
                padding: {UIScaling.scale(8)}px;
            }}
        """)
        log_layout.addWidget(self.log_viewer)
        
        # Log controls row
        log_controls = QHBoxLayout()
        
        self.log_stats_label = QLabel("")
        stats_font_size = UIScaling.scale_font(11)
        self.log_stats_label.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: {stats_font_size}px;")
        log_controls.addWidget(self.log_stats_label, 1)
        
        btn_refresh_log = QPushButton("↻ Refresh")
        btn_refresh_log.setStyleSheet(self.btn_secondary_style)
        btn_refresh_log.clicked.connect(self.refresh_log_viewer)
        log_controls.addWidget(btn_refresh_log)
        
        btn_clear_log = QPushButton("🗑 Clear Log")
        btn_clear_log.setStyleSheet(self.btn_secondary_style)
        btn_clear_log.clicked.connect(self.clear_fetch_log)
        log_controls.addWidget(btn_clear_log)
        
        log_layout.addLayout(log_controls)
        
        right_col.addWidget(log_card)
        right_col.addStretch()

        columns.addLayout(left_col, 1)
        columns.addLayout(right_col, 1)
        self.main_layout.addLayout(columns)
        
        # Initialize visibility
        self.update_preset_combo()
        curr_idx = self.settings.get("camera_index", 0)
        self.set_camera_ui_state(curr_idx)
        
        # Load existing logs
        self.refresh_log_viewer()

    def create_card(self, title, is_sub_card=False):
        card = QFrame()
        bg = "#FFFFFF" if not is_sub_card else "#F8F9FA"
        border = self.theme['border'] if not is_sub_card else "#E9ECEF"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {UIScaling.scale(12)}px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        if title:
            title_lbl = QLabel(title.upper())
            title_font_size = UIScaling.scale_font(11)
            title_lbl.setStyleSheet(f"""
                color: #2196F3; 
                font-size: {title_font_size}px; 
                font-weight: bold; 
                margin-bottom: {UIScaling.scale(5)}px;
                letter-spacing: 1.2px;
            """)
            layout.addWidget(title_lbl)
            
        return card, layout

    def create_info_row(self, label_text, value_text, button_text=""):
        """Create a row with label, value, and optional button"""
        row = QHBoxLayout()
        row.setContentsMargins(5, 5, 5, 5)
        
        lbl = QLabel(label_text)
        font_size = UIScaling.scale_font(13)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {font_size}px; font-weight: bold;")
        
        row.addWidget(lbl, 1)
        
        if value_text:
            value = QLabel(value_text)
            value.setStyleSheet(f"color: #2196F3; font-weight: bold; font-size: {font_size}px;")
            row.addWidget(value)
        
        if button_text:
            btn = QPushButton(button_text)
            btn.setStyleSheet(self.btn_secondary_style)
            row.addWidget(btn)
        
        return row
    
    def create_input_row(self, label_text, value, suffix="", help_text=""):
        """Create a styled input row with label and optional help text"""
        container = QVBoxLayout()
        container.setSpacing(4)
        
        lbl_row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl_font_size = UIScaling.scale_font(14)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {lbl_font_size}px; font-weight: bold;")
        lbl_row.addWidget(lbl)
        
        if suffix:
            suff = QLabel(suffix)
            suff_font_size = UIScaling.scale_font(12)
            suff.setStyleSheet(f"color: #999999; font-size: {suff_font_size}px;")
            lbl_row.addWidget(suff)
        
        lbl_row.addStretch()
        container.addLayout(lbl_row)
        
        if help_text:
            h_lbl = QLabel(help_text)
            h_font_size = UIScaling.scale_font(11)
            h_lbl.setStyleSheet(f"color: #888888; font-size: {h_font_size}px;")
            container.addWidget(h_lbl)
            
        input_field = QLineEdit()
        input_field.setText(value)
        input_field.setStyleSheet(self.line_edit_style)
        container.addWidget(input_field)
        
        return (container, input_field)
    
    def create_path_row(self, label_text, value):
        """Create a row for path selection"""
        container = QVBoxLayout()
        container.setSpacing(4)
        
        lbl = QLabel(label_text)
        lbl_font_size = UIScaling.scale_font(14)
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {lbl_font_size}px; font-weight: bold;")
        container.addWidget(lbl)
        
        row = QHBoxLayout()
        input_field = QLineEdit()
        input_field.setText(value)
        input_field.setStyleSheet(self.line_edit_style)
        
        btn = QPushButton("📁")
        btn_size = UIScaling.scale(40)
        btn_font_size = UIScaling.scale_font(18)
        btn.setFixedSize(btn_size, btn_size)
        btn.setStyleSheet(self.btn_secondary_style + f"padding: 0; font-size: {btn_font_size}px;")
        
        row.addWidget(input_field, 1)
        row.addWidget(btn)
        container.addLayout(row)
        
        return (container, input_field)
    
    # -------------------------------------------------------------------------
    # Camera Logic
    # -------------------------------------------------------------------------
    
    def set_camera_ui_state(self, val):
        """Populate UI based on current settings value"""
        if isinstance(val, int) and val >= 0:
            # USB Camera
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == val:
                    self.camera_combo.setCurrentIndex(i)
                    break
            self.ip_camera_section.setVisible(False)
        else:
            # IP Camera
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == "ip":
                    self.camera_combo.setCurrentIndex(i)
                    break
            self.ip_camera_section.setVisible(True)
            
            # If val is a dict (internal use) or the active_ip_preset_id
            active_id = self.settings.get("active_ip_preset_id")
            for i in range(self.ip_preset_combo.count()):
                if self.ip_preset_combo.itemData(i) == active_id:
                    self.ip_preset_combo.setCurrentIndex(i)
                    break

    def on_camera_combo_change(self, index):
        current_data = self.camera_combo.currentData()
        if current_data == "ip":  # IP Camera
            self.ip_camera_section.setVisible(True)
            # Auto-trigger scan if no cameras found yet
            if not self.discovered_cameras:
                self.scan_for_cameras()
        else:
            self.ip_camera_section.setVisible(False)
            
        # Restart preview if running
        if self.cap_thread is not None:
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
        """When a discovered camera is selected, populate the fields"""
        if index <= 0 or not self.discovered_cameras:
            return
            
        cam = self.discovered_combo.currentData()
        if cam and isinstance(cam, DiscoveredCamera):
            self.ip_address_input.setText(cam.ip)
            self.ip_port_input.setText(str(cam.port))
            self.ip_path_input.setText(cam.rtsp_path)
            self.connection_status.setText(f"Populated from: {cam}")
            
    # --- New Preset Management Methods ---
    
    def update_preset_combo(self):
        """Re-populate IP preset dropdown"""
        self.ip_preset_combo.blockSignals(True)
        self.ip_preset_combo.clear()
        for p in self.ip_presets:
            self.ip_preset_combo.addItem(p["name"], p["id"])
        
        # Select active
        active_id = self.settings.get("active_ip_preset_id")
        idx = self.ip_preset_combo.findData(active_id)
        if idx >= 0:
            self.ip_preset_combo.setCurrentIndex(idx)
        elif self.ip_preset_combo.count() > 0:
            self.ip_preset_combo.setCurrentIndex(0)
            
        self.ip_preset_combo.blockSignals(False)
        self.load_preset_to_ui()

    def load_preset_to_ui(self):
        """Load currently selected preset data into input fields"""
        preset_id = self.ip_preset_combo.currentData()
        preset = next((p for p in self.ip_presets if p["id"] == preset_id), None)
        
        if not preset:
            return
            
        self.current_preset = preset
        self.protocol_combo.setCurrentText(preset.get("protocol", "rtsp"))
        self.ip_address_input.setText(preset.get("address", ""))
        self.ip_port_input.setText(str(preset.get("port", "554")))
        self.ip_path_input.setText(preset.get("path", ""))
        self.ip_username_input.setText(preset.get("username", ""))
        self.ip_password_input.setText(preset.get("password", ""))
        self.transport_combo.setCurrentText(preset.get("transport", "tcp"))

    def on_ip_preset_change(self, index):
        self.load_preset_to_ui()
        if self.cap_thread is not None:
            self.stop_preview()
            self.start_preview()

    def add_new_preset(self):
        from datetime import datetime
        new_id = f"preset-{int(datetime.now().timestamp())}"
        new_preset = {
            "id": new_id,
            "name": f"New Preset {len(self.ip_presets) + 1}",
            "protocol": "rtsp",
            "address": "",
            "port": "554",
            "path": "",
            "username": "",
            "password": "",
            "transport": "tcp"
        }
        self.ip_presets.append(new_preset)
        self.settings["active_ip_preset_id"] = new_id
        self.update_preset_combo()

    def delete_current_preset(self):
        if len(self.ip_presets) <= 1:
            return # Keep at least one
            
        preset_id = self.ip_preset_combo.currentData()
        self.ip_presets = [p for p in self.ip_presets if p["id"] != preset_id]
        self.settings["active_ip_preset_id"] = self.ip_presets[0]["id"]
        self.update_preset_combo()

    def get_selected_camera_source(self):
        """Get the camera source - either index or a dict for IP cameras"""
        current_data = self.camera_combo.currentData()
        
        if current_data == "ip":
            # IP Camera: Return current preset with updated fields from UI
            return {
                "id": self.ip_preset_combo.currentData(),
                "name": self.ip_preset_combo.currentText(),
                "protocol": self.protocol_combo.currentText(),
                "address": self.ip_address_input.text().strip(),
                "port": self.ip_port_input.text().strip(),
                "path": self.ip_path_input.text().strip(),
                "username": self.ip_username_input.text().strip(),
                "password": self.ip_password_input.text().strip(),
                "transport": self.transport_combo.currentText()
            }
        else:
            return current_data

    def toggle_preview(self):
        if self.cap_thread is not None:
            self.stop_preview()
        else:
            self.start_preview()
            
    def start_preview(self):
        source = self.get_selected_camera_source()
        is_ip = not isinstance(source, int)
        
        # UI Feedback
        self.btn_preview.setText("⌛ Connecting...")
        self.btn_preview.setEnabled(False)
        self.preview_box.setText("Connecting to camera...\nPlease wait.")
        self.preview_box.setStyleSheet(f"background-color: #2D2D2D; border-radius: 10px; color: {self.theme['text_sub']}; font-size: 14px;")

        # Start background capture
        self.cap_thread = VideoCaptureThread(source, is_ip)
        self.cap_thread.frame_ready.connect(self.on_frame_received)
        self.cap_thread.connection_failed.connect(self.on_connection_failed)
        self.cap_thread.connection_lost.connect(self.on_connection_lost)
        self.cap_thread.start()

    def on_frame_received(self, frame):
        # UI Housekeeping on first successful frame
        if self.btn_preview.text() == "⌛ Connecting...":
            self.btn_preview.setEnabled(True)
            self.btn_preview.setText("Stop Test Feed")
            self.btn_preview.setStyleSheet("""
                QPushButton { background-color: #F44336; color: white; border-radius: 8px; font-weight: bold; }
                QPushButton:hover { background-color: #D32F2F; }
            """)
            
        # Convert to Pixmap and Display
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            self.preview_box.setPixmap(pix.scaled(self.preview_box.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"[Settings] Render error: {e}")

    def on_connection_failed(self, error_msg):
        self.btn_preview.setEnabled(True)
        self.btn_preview.setText("Start Test Feed")
        self.preview_box.setText(f"Connection failed:\n{error_msg}")
        self.preview_box.setStyleSheet("background-color: #FFF2F2; border: 1px solid #FFCDD2; color: #D32F2F; border-radius: 10px; font-weight: bold;")

    def on_connection_lost(self):
        self.stop_preview()
        self.preview_box.setText("Connection lost.\nCheck camera or network.")
        self.preview_box.setStyleSheet("background-color: #FFF3E0; border-radius: 10px; color: #E65100; font-weight: bold;")

    def stop_preview(self):
        if self.cap_thread:
            self.cap_thread.stop()
            self.cap_thread = None
            
        self.preview_box.setText("Camera\nPreview")
        self.preview_box.setStyleSheet(f"background-color: #2D2D2D; border-radius: 10px; color: #CCCCCC; font-size: 16px; font-weight: bold;")
        self.preview_box.setPixmap(QPixmap())
        self.btn_preview.setText("Start Test Feed")
        self.btn_preview.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #43A047; }
        """)
        
    
    def close_overlay(self):
        self.stop_preview()
        super().close_overlay()

    def save_settings_clicked(self):
        """Save settings to file"""
        source = self.get_selected_camera_source()
        
        # Update settings object
        if isinstance(source, dict):
            # IP Preset: Update the specific preset in the list
            preset_id = source["id"]
            for i, p in enumerate(self.ip_presets):
                if p["id"] == preset_id:
                    self.ip_presets[i] = source
                    break
            
            self.settings["camera_index"] = "ip" # Flag that IP is active
            self.settings["active_ip_preset_id"] = preset_id
        else:
            self.settings["camera_index"] = source
            
        self.settings["mm_per_px"] = float(self.mmpx_input.text() or 0.21)
        self.settings["sensor_delay"] = float(self.delay_input.text() or 0.2)
        
        # Save Layout Mode
        mode_idx = self.layout_combo.currentIndex()
        self.settings["layout_mode"] = "split" if mode_idx == 1 else "classic"
        
        self.settings["ip_camera_presets"] = self.ip_presets
        
        self.settings["paths"] = {
            "profile": self.profile_input.text(),
            "settings": self.settings_input.text(),
            "db": self.db_input.text(),
            "results": self.results_input.text()
        }
        
        self.settings["sensor_port"] = self.sensor_port_input.text().strip()
        self.settings["plc_port"] = self.plc_port_input.text().strip()
        try:
            self.settings["plc_trigger_reg"] = int(self.plc_trig_input.text().strip() or 12)
            self.settings["plc_result_reg"] = int(self.plc_res_input.text().strip() or 13)
        except ValueError:
            pass
        
        settings_file = os.path.join("output", "settings", "app_settings.json")
        JsonUtility.save_to_json(settings_file, self.settings)
        
        self.settings_saved.emit(self.settings)
        self.close_overlay()

    # -------------------------------------------------------------------------
    # SKU Fetch Logic
    # -------------------------------------------------------------------------
    
    def start_fetch_sku(self):
        """Start fetching SKU data from database"""
        if self.sku_worker is not None and self.sku_worker.isRunning():
            return  # Already fetching
        
        # Update UI to loading state
        self.btn_fetch.setText("⏳ Fetching...")
        self.btn_fetch.setEnabled(False)
        self.btn_fetch.setStyleSheet(f"""
            QPushButton {{
                background-color: #E0E0E0;
                border-radius: {UIScaling.scale(8)}px;
                color: #666666;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: bold;
                padding: {UIScaling.scale(8)}px {UIScaling.scale(15)}px;
            }}
        """)
        
        # Start worker thread
        self.sku_worker = ProductSKUWorker()
        self.sku_worker.finished.connect(self.on_fetch_complete)
        self.sku_worker.error.connect(self.on_fetch_error)
        self.sku_worker.start()
    
    def on_fetch_complete(self, products):
        """Handle successful SKU fetch"""
        result_file = os.path.join("output", "settings", "result.json")
        
        # Check if we got actual results or empty (possibly due to connection failure)
        if not products:
            # Don't overwrite existing result.json with empty data
            print("[Settings] Fetch returned empty - likely connection failed. Keeping existing data.")
            self.btn_fetch.setText("⚠ No Data")
            self.btn_fetch.setEnabled(True)
            self.btn_fetch.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFF3E0;
                    border-radius: {UIScaling.scale(8)}px;
                    color: #E65100;
                    font-size: {UIScaling.scale_font(14)}px;
                    font-weight: bold;
                    padding: {UIScaling.scale(8)}px {UIScaling.scale(15)}px;
                }}
                QPushButton:hover {{
                    background-color: #FFE0B2;
                }}
            """)
            self.settings["fetch_status"] = "empty - connection may have failed"
            # Log warning
            fetch_logger.log_warning("Fetch returned 0 products - connection may have failed")
            self.refresh_log_viewer()
            # Reset button after delay
            QTimer.singleShot(3000, lambda: (
                self.btn_fetch.setText("Refresh Now"),
                self.btn_fetch.setStyleSheet(self.btn_secondary_style)
            ))
            return
        
        # Save result to file for debugging
        try:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"[Settings] Fetched {len(products)} SKUs, saved to {result_file}")
        except Exception as e:
            print(f"[Settings] Error saving result.json: {e}")
        
        # Update settings with fetch status
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.settings["last_fetched"] = now
        self.settings["fetch_status"] = "success"
        
        # Update UI
        self.last_fetch_label.setText(f"Last Updated: {now}")
        self.btn_fetch.setText(f"✓ {len(products)} SKUs")
        self.btn_fetch.setEnabled(True)
        self.btn_fetch.setStyleSheet(self.btn_secondary_style)
        
        # Log success
        fetch_logger.log_success(f"Fetched {len(products)} SKUs successfully")
        self.refresh_log_viewer()
        
        # Brief success indication
        QTimer.singleShot(2000, lambda: self.btn_fetch.setText("Refresh Now"))
    
    def on_fetch_error(self, error_msg):
        """Handle SKU fetch error"""
        print(f"[Settings] Fetch error: {error_msg}")
        
        # Update settings
        self.settings["fetch_status"] = f"error: {error_msg}"
        
        # Update UI
        self.btn_fetch.setText("⚠ Retry")
        self.btn_fetch.setEnabled(True)
        self.btn_fetch.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFEBEE;
                border-radius: {UIScaling.scale(8)}px;
                color: #D32F2F;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: bold;
                padding: {UIScaling.scale(8)}px {UIScaling.scale(15)}px;
            }}
            QPushButton:hover {{
                background-color: #FFCDD2;
            }}
        """)
        
        # Log error
        fetch_logger.log_error(f"Fetch failed: {error_msg}")
        self.refresh_log_viewer()

    # -------------------------------------------------------------------------
    # Log Viewer Methods
    # -------------------------------------------------------------------------
    
    def refresh_log_viewer(self):
        """Refresh the log viewer content"""
        try:
            log_content = fetch_logger.get_logs()
            self.log_viewer.setPlainText(log_content)
            
            # Scroll to bottom to show latest entries
            scrollbar = self.log_viewer.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # Update stats
            stats = fetch_logger.get_log_stats()
            self.log_stats_label.setText(
                f"{stats['total_entries']} entries | "
                f"{stats['success_count']} success | "
                f"{stats['error_count']} errors"
            )
        except Exception as e:
            self.log_viewer.setPlainText(f"Error loading logs: {e}")
    
    def clear_fetch_log(self):
        """Clear all log entries"""
        if fetch_logger.clear_logs():
            fetch_logger.log_info("Log cleared by user")
            self.refresh_log_viewer()

