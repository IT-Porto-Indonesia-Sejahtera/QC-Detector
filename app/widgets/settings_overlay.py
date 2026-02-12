import os
import json
import threading
from datetime import datetime
import cv2
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QWidget, QPlainTextEdit,
    QGridLayout, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QImage, QPixmap
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ip_camera_discovery import get_discovery, DiscoveredCamera
from app.utils.camera_utils import open_video_capture
from project_utilities.json_utility import JsonUtility
from app.utils.capture_thread import VideoCaptureThread
from app.utils.ui_scaling import UIScaling
from backend.get_product_sku import ProductSKUWorker
from app.utils import fetch_logger
from backend.aruco_utils import detect_aruco_marker
from app.widgets.aruco_calibration_dialog import ArucoCalibrationDialog

class VBoxWithLabel(QVBoxLayout):
    def __init__(self, text, widget):
        super().__init__()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8B95A5; font-weight: bold; font-size: 11px; background: transparent; border: none;")
        self.addWidget(lbl)
        self.addWidget(widget)

class SettingsOverlay(BaseOverlay):
    """Settings overlay for application configuration"""
    
    settings_saved = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        self.cap_thread = None
        self.sku_worker = None
        
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

        # Industrial palette constants
        self._C = {
            'bg': '#1B1F27', 'surface': '#252A34', 'surface_hover': '#2E3440',
            'text': '#E8ECF1', 'text_sub': '#8B95A5',
            'accent': '#3B82F6', 'accent_hover': '#2563EB',
            'green': '#22C55E', 'danger': '#EF4444',
            'input_bg': '#1E2330', 'input_border': '#3A4150',
            'input_focus': '#3B82F6',
        }
        
        self.btn_secondary_style = f"""
            QPushButton {{
                background-color: {self._C['surface']};
                color: {self._C['accent']};
                border: 1px solid {self._C['input_border']};
                border-radius: 8px; padding: 12px;
                font-weight: bold; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {self._C['surface_hover']}; }}
        """
        
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
    
    def load_settings_to_ui(self):
        """Update UI fields with loaded settings"""
        s = self.settings
        self.mmpx_input.setText(str(s.get("mm_per_px", 0.21)))
        
        # Model
        det_mode = s.get("detection_model", "standard")
        idx = self.det_model.findData(det_mode)
        if idx != -1: self.det_model.setCurrentIndex(idx)
        
        # Layout
        lay_mode = s.get("layout_mode", "classic")
        if lay_mode == "split": self.layout_combo.setCurrentIndex(1)
        elif lay_mode == "minimal": self.layout_combo.setCurrentIndex(2)
        else: self.layout_combo.setCurrentIndex(0)
        
        self.delay_input.setText(str(s.get("sensor_delay", 0.2)))
        
        # ArUco & Heights
        self.marker_size_input.setText(str(s.get("aruco_marker_size", 50.0)))
        self.cam_height_input.setText(str(s.get("mounting_height", 1000.0)))
        self.obj_thickness_input.setText(str(s.get("sandal_thickness", 15.0)))
        
        # Crop
        crop = s.get("camera_crop", {})
        self.crop_left.setText(str(crop.get("left", 0)))
        self.crop_right.setText(str(crop.get("right", 0)))
        self.crop_top.setText(str(crop.get("top", 0)))
        self.crop_bottom.setText(str(crop.get("bottom", 0)))
        
        rot = crop.get("rotation", 0)
        ridx = self.rotation_combo.findData(rot)
        if ridx != -1: self.rotation_combo.setCurrentIndex(ridx)
        
        self.aspect_ratio_input.setText(str(s.get("aspect_ratio_correction", 1.0)))
        self.force_w.setText(str(s.get("force_width", 0)))
        self.force_h.setText(str(s.get("force_height", 0)))
        
        # Distortion
        dist = s.get("lens_distortion", {})
        self.k1.setText(str(dist.get("k1", 0.0)))
        self.k2.setText(str(dist.get("k2", 0.0)))
        self.p1.setText(str(dist.get("p1", 0.0)))
        self.p2.setText(str(dist.get("p2", 0.0)))
        self.k3.setText(str(dist.get("k3", 0.0)))
        self.fx.setText(str(dist.get("fx", 0.0)))
        self.fy.setText(str(dist.get("fy", 0.0)))
        self.cx.setText(str(dist.get("cx", 0.0)))
        self.cy.setText(str(dist.get("cy", 0.0)))
        
        is_auto = s.get("auto_estimate_matrix", False)
        self.btn_auto_matrix.setChecked(is_auto)
        self.on_auto_matrix_toggle(is_auto)
        
        self.sensor_port_input.setText(s.get("sensor_port", ""))
        self.plc_port_input.setText(s.get("plc_port", ""))
        self.plc_trig_input.setText(str(s.get("plc_trigger_reg", 12)))
        self.plc_res_input.setText(str(s.get("plc_result_reg", 13)))
        
        self.update_preset_combo()
        cam_idx = s.get("camera_index", 0)
        self.set_camera_ui_state(cam_idx)
    
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
        
    def update_content_size(self):
        """Override base to allow wider settings area"""
        parent = self.parent()
        if not parent: return
        p_size = parent.size()
        self.resize(p_size)
        
        # We want 900x650 but not more than 95% of parent
        scaled_w = UIScaling.scale(900)
        scaled_h = UIScaling.scale(650)
        max_w = int(p_size.width() * 0.95)
        max_h = int(p_size.height() * 0.95)
        
        target_w = min(scaled_w, max_w)
        target_h = min(scaled_h, max_h)
        self.content_box.setFixedSize(target_w, target_h)

    def setup_settings_ui(self):
        # Alias for backward compatibility
        self.init_ui = self.setup_settings_ui
        
        C = self._C  # shorthand
        
        # Use a scroll area for the entire settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {C['bg']}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['input_border']}; border-radius: 4px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {C['text_sub']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        scroll_layout.setSpacing(20)
        
        scroll.setWidget(scroll_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(scroll)
        
        # Header
        header = QHBoxLayout(); header.setContentsMargins(10, 0, 10, 0)
        
        btn_back = QPushButton("❮ Back"); btn_back.setFixedHeight(UIScaling.scale(40))
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(f"border: none; font-size: {UIScaling.scale_font(16)}px; font-weight: bold; color: {C['accent']}; background: transparent;")
        btn_back.clicked.connect(self.close_overlay)
        header.addWidget(btn_back)
        header.addSpacing(10)
        
        lbl_title = QLabel("System Settings")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: bold; color: {C['text']};")
        header.addWidget(lbl_title); header.addStretch()
        
        btn_apply = QPushButton("Apply"); self.style_button(btn_apply); btn_apply.clicked.connect(self.apply_settings_clicked)
        btn_save = QPushButton("Save && Exit"); self.style_button(btn_save, True); btn_save.clicked.connect(self.save_settings_clicked)
        header.addWidget(btn_apply); header.addSpacing(10); header.addWidget(btn_save); scroll_layout.addLayout(header)
        
        # Content Layout
        columns = QHBoxLayout(); columns.setSpacing(20)
        left_col = QVBoxLayout(); left_col.setSpacing(20)
        right_col = QVBoxLayout(); right_col.setSpacing(20)
        
        # --- LEFT: Camera & IP ---
        cam_card, cam_layout = self.create_card("Camera Configuration")
        self.preview_box = QLabel("Test Feed"); self.preview_box.setAlignment(Qt.AlignCenter)
        self.preview_box.setFixedSize(UIScaling.scale(400), UIScaling.scale(250))
        self.preview_box.setStyleSheet(f"background: {C['input_bg']}; border-radius: 10px; color: {C['text_sub']}; font-weight: bold; border: 1px solid {C['input_border']};")
        cam_layout.addWidget(self.preview_box, 0, Qt.AlignHCenter)
        self.btn_preview = QPushButton("Start Test Feed"); self.style_button(self.btn_preview, True); self.btn_preview.clicked.connect(self.toggle_preview); cam_layout.addWidget(self.btn_preview)
        
        cam_layout.addWidget(self.create_styled_label("Camera Source:"))
        self.camera_combo = QComboBox(); self.camera_combo.addItem("IP Network Camera", "ip")
        if self.available_cameras:
            for idx in self.available_cameras: self.camera_combo.insertItem(0, f"USB Camera {idx}", idx)
        self.style_input(self.camera_combo); self.camera_combo.currentIndexChanged.connect(self.on_camera_combo_change); cam_layout.addWidget(self.camera_combo)
        cam_layout.addStretch()
        left_col.addWidget(cam_card)
        
        self.ip_camera_section, ip_layout = self.create_card("IP Camera Details")
        h_preset = QHBoxLayout(); self.ip_preset_combo = QComboBox(); self.style_input(self.ip_preset_combo)
        self.ip_preset_combo.currentIndexChanged.connect(self.on_ip_preset_change)
        btn_new = QPushButton("+ New"); self.style_button(btn_new); btn_new.clicked.connect(self.add_new_preset)
        h_preset.addWidget(self.ip_preset_combo, 1); h_preset.addWidget(btn_new); ip_layout.addLayout(h_preset)
        self.ip_address_input = QLineEdit(); self.style_input(self.ip_address_input); ip_layout.addWidget(self.create_styled_label("Address")); ip_layout.addWidget(self.ip_address_input)
        h_params = QHBoxLayout()
        self.protocol_combo = QComboBox(); self.protocol_combo.addItems(["rtsp", "http"]); self.style_input(self.protocol_combo)
        self.ip_port_input = QLineEdit(); self.ip_port_input.setPlaceholderText("554"); self.style_input(self.ip_port_input)
        self.transport_combo = QComboBox(); self.transport_combo.addItems(["tcp", "udp"]); self.style_input(self.transport_combo)
        
        h_params.addLayout(VBoxWithLabel("Proto", self.protocol_combo))
        h_params.addLayout(VBoxWithLabel("Port", self.ip_port_input))
        h_params.addLayout(VBoxWithLabel("Transport", self.transport_combo))
        ip_layout.addLayout(h_params)
        
        self.ip_path_input = QLineEdit(); self.ip_path_input.setPlaceholderText("/live/ch1"); self.style_input(self.ip_path_input); ip_layout.addWidget(self.create_styled_label("Path")); ip_layout.addWidget(self.ip_path_input)
        h_auth = QHBoxLayout(); self.ip_username_input = QLineEdit(); self.ip_username_input.setPlaceholderText("User"); self.style_input(self.ip_username_input)
        self.ip_password_input = QLineEdit(); self.ip_password_input.setEchoMode(QLineEdit.Password); self.ip_password_input.setPlaceholderText("Pass"); self.style_input(self.ip_password_input)
        h_auth.addWidget(self.ip_username_input); h_auth.addWidget(self.ip_password_input); ip_layout.addLayout(h_auth)
        h_disc = QHBoxLayout(); self.btn_scan_cameras = QPushButton("🔍 Scan Network"); self.style_button(self.btn_scan_cameras); self.btn_scan_cameras.clicked.connect(self.scan_for_cameras)
        self.discovered_combo = QComboBox(); self.discovered_combo.addItem("-- Discovered --"); self.style_input(self.discovered_combo); self.discovered_combo.currentIndexChanged.connect(self.on_discovered_camera_selected)
        h_disc.addWidget(self.btn_scan_cameras); h_disc.addWidget(self.discovered_combo, 1); ip_layout.addLayout(h_disc)
        self.connection_status = QLabel(""); self.connection_status.setStyleSheet(f"color: {C['text_sub']}; font-size: 11px;"); ip_layout.addWidget(self.connection_status)
        ip_layout.addStretch()
        left_col.addWidget(self.ip_camera_section)
        left_col.addStretch(1)
        
        # --- RIGHT: Params & HW ---
        p_card, p_layout = self.create_card("Application Parameters")
        p_layout.addWidget(self.create_styled_label("Resolution (mm/px):"))
        self.mmpx_input = QLineEdit(); self.style_input(self.mmpx_input); p_layout.addWidget(self.mmpx_input)
        p_layout.addWidget(self.create_styled_label("Detection Model:"))
        self.det_model = QComboBox(); self.det_model.addItem("Standard (Contour)", "standard"); self.det_model.addItem("SAM (AI)", "sam"); self.style_input(self.det_model); p_layout.addWidget(self.det_model)
        p_layout.addWidget(self.create_styled_label("Layout Mode:"))
        self.layout_combo = QComboBox(); self.layout_combo.addItems(["Classic", "Split", "Minimal"]); self.style_input(self.layout_combo); p_layout.addWidget(self.layout_combo)
        p_layout.addWidget(self.create_styled_label("Sensor Delay (s):"))
        self.delay_input = QLineEdit(); self.style_input(self.delay_input); p_layout.addWidget(self.delay_input)
        p_layout.addStretch()
        right_col.addWidget(p_card)
        
        aruco_card, aruco_layout = self.create_card("Auto Calibration System")
        aruco_layout.addWidget(self.create_styled_label("Marker Size (mm):"))
        self.marker_size_input = QLineEdit(); self.style_input(self.marker_size_input); aruco_layout.addWidget(self.marker_size_input)
        h_height = QHBoxLayout(); self.cam_height_input = QLineEdit(); self.style_input(self.cam_height_input); self.obj_thickness_input = QLineEdit(); self.style_input(self.obj_thickness_input)
        h_height.addLayout(VBoxWithLabel("Mount Height", self.cam_height_input)); h_height.addLayout(VBoxWithLabel("Sandal Thick", self.obj_thickness_input)); aruco_layout.addLayout(h_height)
        h_ctrl = QHBoxLayout(); self.btn_run_calibration = QPushButton("Run Auto Calibration"); self.style_button(self.btn_run_calibration, True); self.btn_run_calibration.clicked.connect(self.run_auto_calibration)
        self.btn_debug_aruco = QPushButton("🔍 Debug Off"); self.style_button(self.btn_debug_aruco); self.btn_debug_aruco.setFixedWidth(UIScaling.scale(120)); self.btn_debug_aruco.clicked.connect(self.toggle_aruco_debug); self.aruco_debug_active = False
        h_ctrl.addWidget(self.btn_run_calibration, 1); h_ctrl.addWidget(self.btn_debug_aruco); aruco_layout.addLayout(h_ctrl)
        aruco_layout.addStretch()
        right_col.addWidget(aruco_card)
        
        crop_card, crop_layout = self.create_card("Camera Region of Interest")
        crop_layout.addWidget(self.create_styled_label("Crop L/R/T/B (%):"))
        h_crop1 = QHBoxLayout(); self.crop_left = QLineEdit(); self.style_input(self.crop_left); self.crop_right = QLineEdit(); self.style_input(self.crop_right)
        h_crop1.addWidget(self.crop_left); h_crop1.addWidget(self.crop_right); crop_layout.addLayout(h_crop1)
        h_crop2 = QHBoxLayout(); self.crop_top = QLineEdit(); self.style_input(self.crop_top); self.crop_bottom = QLineEdit(); self.style_input(self.crop_bottom)
        h_crop2.addWidget(self.crop_top); h_crop2.addWidget(self.crop_bottom); crop_layout.addLayout(h_crop2)
        crop_layout.addWidget(self.create_styled_label("Rotation:"))
        self.rotation_combo = QComboBox(); self.rotation_combo.addItems(["0°", "90° CW", "180°", "90° CCW"]); self.rotation_combo.setItemData(0, 0); self.rotation_combo.setItemData(1, 90); self.rotation_combo.setItemData(2, 180); self.rotation_combo.setItemData(3, 270); self.style_input(self.rotation_combo); self.rotation_combo.currentIndexChanged.connect(self.update_live_params); crop_layout.addWidget(self.rotation_combo)
        crop_layout.addStretch()
        crop_layout.addWidget(self.create_styled_label("Aspect Ratio / Resolution:"))
        self.aspect_ratio_input = QLineEdit(); self.style_input(self.aspect_ratio_input); crop_layout.addWidget(self.aspect_ratio_input)
        h_res = QHBoxLayout(); self.force_w = QLineEdit(); self.style_input(self.force_w); self.force_h = QLineEdit(); self.style_input(self.force_h)
        h_res.addLayout(VBoxWithLabel("W", self.force_w)); h_res.addLayout(VBoxWithLabel("H", self.force_h)); crop_layout.addLayout(h_res)
        right_col.addWidget(crop_card)
        
        dist_card, dist_layout = self.create_card("Lens Distortion Correction")
        self.dist_preset = QComboBox(); self.dist_preset.addItems(["Custom", "No Distortion", "Mild Barrel", "Medium Barrel", "Strong Barrel"]); self.style_input(self.dist_preset); self.dist_preset.currentIndexChanged.connect(self.on_dist_preset_change); dist_layout.addWidget(self.create_styled_label("Preset")); dist_layout.addWidget(self.dist_preset)
        h_k = QHBoxLayout()
        self.k1 = QLineEdit(); self.style_input(self.k1)
        self.k2 = QLineEdit(); self.style_input(self.k2)
        self.p1 = QLineEdit(); self.style_input(self.p1)
        self.p2 = QLineEdit(); self.style_input(self.p2)
        self.k3 = QLineEdit(); self.style_input(self.k3)
        h_k.addLayout(VBoxWithLabel("k1", self.k1)); h_k.addLayout(VBoxWithLabel("k2", self.k2)); h_k.addLayout(VBoxWithLabel("p1", self.p1))
        h_k.addLayout(VBoxWithLabel("p2", self.p2)); h_k.addLayout(VBoxWithLabel("k3", self.k3))
        dist_layout.addLayout(h_k)
        
        h_mat_ctrl = QHBoxLayout(); self.btn_auto_matrix = QPushButton("Auto Matrix: OFF"); self.btn_auto_matrix.setCheckable(True); self.style_button(self.btn_auto_matrix); self.btn_auto_matrix.clicked.connect(self.on_auto_matrix_toggle); h_mat_ctrl.addWidget(self.btn_auto_matrix); dist_layout.addLayout(h_mat_ctrl)
        h_mat = QHBoxLayout(); self.fx = QLineEdit(); self.style_input(self.fx); self.fy = QLineEdit(); self.style_input(self.fy); self.cx = QLineEdit(); self.style_input(self.cx); self.cy = QLineEdit(); self.style_input(self.cy)
        h_mat.addLayout(VBoxWithLabel("fx", self.fx)); h_mat.addLayout(VBoxWithLabel("fy", self.fy)); dist_layout.addLayout(h_mat)
        h_mat2 = QHBoxLayout(); h_mat2.addLayout(VBoxWithLabel("cx", self.cx)); h_mat2.addLayout(VBoxWithLabel("cy", self.cy)); dist_layout.addLayout(h_mat2)
        dist_layout.addStretch()
        right_col.addWidget(dist_card)
        
        hw_card, hw_layout = self.create_card("Hardware Integration")
        self.sensor_port_input = QLineEdit(); self.style_input(self.sensor_port_input); self.plc_port_input = QLineEdit(); self.style_input(self.plc_port_input)
        hw_layout.addLayout(VBoxWithLabel("Sensor Port", self.sensor_port_input)); hw_layout.addLayout(VBoxWithLabel("PLC Port", self.plc_port_input))
        h_regs = QHBoxLayout(); self.plc_trig_input = QLineEdit(); self.style_input(self.plc_trig_input); self.plc_res_input = QLineEdit(); self.style_input(self.plc_res_input)
        h_regs.addLayout(VBoxWithLabel("Trig Reg", self.plc_trig_input)); h_regs.addLayout(VBoxWithLabel("Res Reg", self.plc_res_input)); hw_layout.addLayout(h_regs)
        hw_layout.addStretch()
        right_col.addWidget(hw_card)
        
        sync_card, sync_layout = self.create_card("Database Sync")
        self.btn_fetch = QPushButton("🔄 Fetch SKU Data"); self.style_button(self.btn_fetch, True); self.btn_fetch.clicked.connect(self.start_fetch_sku); sync_layout.addWidget(self.btn_fetch)
        
        h_sync_info = QHBoxLayout()
        self.last_fetch_label = QLabel("Last Updated: Never"); self.last_fetch_label.setStyleSheet(f"color: {C['text_sub']}; font-size: 11px;")
        self.log_stats_label = QLabel(""); self.log_stats_label.setStyleSheet(f"color: {C['text_sub']}; font-size: 11px;")
        h_sync_info.addWidget(self.last_fetch_label); h_sync_info.addStretch(); h_sync_info.addWidget(self.log_stats_label)
        sync_layout.addLayout(h_sync_info)
        
        self.log_viewer = QPlainTextEdit(); self.log_viewer.setReadOnly(True); self.log_viewer.setFixedHeight(UIScaling.scale(100))
        self.log_viewer.setStyleSheet(f"background: {C['input_bg']}; color: {C['green']}; font-family: 'Menlo', 'Courier New'; font-size: 10px; border-radius: 8px; border: 1px solid {C['input_border']};")
        sync_layout.addWidget(self.log_viewer)
        sync_layout.addStretch()
        right_col.addWidget(sync_card)
        
        right_col.addStretch(1)
        
        columns.addLayout(left_col, 1); columns.addLayout(right_col, 1); scroll_layout.addLayout(columns)
        self.refresh_log_viewer(); self.load_settings_to_ui()

    def style_button(self, btn, primary=False):
        C = self._C
        if primary:
            bg, fg, hover = C['accent'], '#FFFFFF', C['accent_hover']
        else:
            bg, fg, hover = C['surface'], C['accent'], C['surface_hover']
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: {UIScaling.scale_font(14)}px;
                border: {'none' if primary else f'1px solid {C["input_border"]}'};
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: {C['surface']};
                color: {C['input_border']};
            }}
        """)

    def style_input(self, widget):
        C = self._C
        cls = widget.__class__.__name__
        widget.setStyleSheet(f"""
            {cls} {{
                border: 1px solid {C['input_border']};
                border-radius: 8px;
                padding: 10px;
                background: {C['input_bg']};
                color: {C['text']};
                font-size: {UIScaling.scale_font(14)}px;
            }}
            {cls}:focus {{
                border: 2px solid {C['input_focus']};
                padding: 9px;
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
            QComboBox QAbstractItemView {{
                background: {C['surface']};
                color: {C['text']};
                selection-background-color: {C['accent']};
                selection-color: white;
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                min-height: 28px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: {C['surface_hover']};
            }}
        """)
        # Force non-native popup on macOS so stylesheet applies to dropdown
        if isinstance(widget, QComboBox):
            from PySide6.QtWidgets import QListView
            view = QListView()
            view.setStyleSheet(f"""
                QListView {{
                    background: {C['surface']};
                    color: {C['text']};
                    border: 1px solid {C['input_border']};
                    border-radius: 4px;
                    outline: none;
                    padding: 4px;
                }}
                QListView::item {{
                    padding: 8px;
                    min-height: 28px;
                    border-radius: 4px;
                }}
                QListView::item:hover {{
                    background: {C['surface_hover']};
                }}
                QListView::item:selected {{
                    background: {C['accent']};
                    color: white;
                }}
            """)
            widget.setView(view)
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self.update_live_params)

    def create_card(self, title, is_sub_card=False):
        C = self._C
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setStyleSheet(f"""
            QFrame#cardFrame {{
                background: {C['surface']};
                border-radius: 12px;
                border: 1px solid {C['input_border']};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(12)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(f"color: {C['accent']}; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; border: none !important; background: transparent !important;")
        l.addWidget(lbl)
        return card, l

    def create_styled_label(self, text):
        C = self._C
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text']}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        return lbl

    def set_camera_ui_state(self, val):
        """Populate UI based on current settings value"""
        if isinstance(val, int) and val >= 0:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == val:
                    self.camera_combo.setCurrentIndex(i)
                    break
            if hasattr(self, 'ip_camera_section'): self.ip_camera_section.setVisible(False)
        else:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i) == "ip":
                    self.camera_combo.setCurrentIndex(i)
                    break
            if hasattr(self, 'ip_camera_section'): self.ip_camera_section.setVisible(True)
            active_id = self.settings.get("active_ip_preset_id")
            for i in range(self.ip_preset_combo.count()):
                if self.ip_preset_combo.itemData(i) == active_id:
                    self.ip_preset_combo.setCurrentIndex(i)
                    break

    def on_camera_combo_change(self, index):
        current_data = self.camera_combo.currentData()
        if current_data == "ip":
            if hasattr(self, 'ip_camera_section'): self.ip_camera_section.setVisible(True)
            if not self.discovered_cameras: self.scan_for_cameras()
        else:
            if hasattr(self, 'ip_camera_section'): self.ip_camera_section.setVisible(False)
        if self.cap_thread is not None: self.stop_preview(); self.start_preview()
    
    def scan_for_cameras(self):
        if self.is_scanning: return
        self.is_scanning = True
        self.btn_scan_cameras.setText("⏳ Scanning...")
        self.btn_scan_cameras.setEnabled(False)
        self.connection_status.setText("Scanning network for cameras...")
        self.connection_status.setStyleSheet("color: #2196F3; font-size: 12px; font-style: italic;")
        discovery = get_discovery()
        discovery.discover_cameras_async(timeout=5.0, callback=self._on_cameras_discovered)
    
    def _on_cameras_discovered(self, cameras):
        self.discovered_cameras = cameras
        self.is_scanning = False
        QTimer.singleShot(0, self._update_discovered_cameras_ui)
    
    def _update_discovered_cameras_ui(self):
        self.btn_scan_cameras.setText("🔍 Scan Network")
        self.btn_scan_cameras.setEnabled(True)
        self.discovered_combo.clear()
        if self.discovered_cameras:
            for cam in self.discovered_cameras: self.discovered_combo.addItem(str(cam), cam)
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
        crop = self.settings.get("camera_crop", {})
        distortion = self.settings.get("lens_distortion", {})
        aspect = self.settings.get("aspect_ratio_correction", 1.0)
        fw = self.settings.get("force_width", 0)
        fh = self.settings.get("force_height", 0)
        
        self.cap_thread = VideoCaptureThread(source, is_ip, crop_params=crop, distortion_params=distortion, aspect_ratio_correction=aspect, force_width=fw, force_height=fh)
        self.cap_thread.frame_ready.connect(self.on_frame_received)
        self.cap_thread.connection_failed.connect(self.on_connection_failed)
        self.cap_thread.connection_lost.connect(self.on_connection_lost)
        self.cap_thread.start()

    def on_dist_preset_change(self):
        txt = self.dist_preset.currentText()
        if "No Distortion" in txt:
            self.k1.setText("0.0"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Mild Barrel" in txt:
            self.k1.setText("-0.08"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Medium Barrel" in txt:
            self.k1.setText("-0.15"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Strong Barrel" in txt:
            self.k1.setText("-0.35"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        self.update_live_params()

    def on_auto_matrix_toggle(self, checked):
        if checked:
            self.btn_auto_matrix.setText("Auto Matrix: ON")
            self.btn_auto_matrix.setStyleSheet(self.btn_auto_matrix.styleSheet().replace("#E8E8ED", "#4CAF50").replace("#007AFF", "white"))
            for f in [self.fx, self.fy, self.cx, self.cy]: f.setEnabled(False)
        else:
            self.btn_auto_matrix.setText("Auto Matrix: OFF")
            self.style_button(self.btn_auto_matrix)
            for f in [self.fx, self.fy, self.cx, self.cy]: f.setEnabled(True)
        self.update_live_params()

    def toggle_aruco_debug(self):
        self.aruco_debug_active = not self.aruco_debug_active
        if self.aruco_debug_active:
            self.btn_debug_aruco.setText("🔍 Debug On")
            self.btn_debug_aruco.setStyleSheet(self.btn_debug_aruco.styleSheet().replace("#E8E8ED", "#FF9800").replace("#007AFF", "white"))
        else:
            self.btn_debug_aruco.setText("🔍 Debug Off")
            self.style_button(self.btn_debug_aruco)

    def parse_aspect_ratio_input(self, text):
        if not text: return 1.0
        try:
            if ':' in text:
                parts = text.split(':')
                return float(parts[0]) / float(parts[1]) if len(parts) == 2 else 1.0
            elif '/' in text:
                parts = text.split('/')
                return float(parts[0]) / float(parts[1]) if len(parts) == 2 else 1.0
            return float(text)
        except: return 1.0

    def update_live_params(self):
        """Update running capture thread with current UI values (real-time feedback)"""
        if not self.cap_thread or not self.cap_thread.isRunning():
            return
            
        try:
            # Gather crop params
            crop = {
                "left": int(self.crop_left.text() or 0),
                "right": int(self.crop_right.text() or 0),
                "top": int(self.crop_top.text() or 0),
                "bottom": int(self.crop_bottom.text() or 0),
                "rotation": self.rotation_combo.currentData()
            }
            # Distortion params
            dist = {
                "k1": float(self.k1.text() or 0),
                "k2": float(self.k2.text() or 0),
                "p1": float(self.p1.text() or 0),
                "p2": float(self.p2.text() or 0),
                "k3": float(self.k3.text() or 0),
                "fx": float(self.fx.text() or 0),
                "fy": float(self.fy.text() or 0),
                "cx": float(self.cx.text() or 0),
                "cy": float(self.cy.text() or 0)
            }
            aspect = self.parse_aspect_ratio_input(self.aspect_ratio_input.text())
            self.cap_thread.update_params(crop_params=crop, distortion_params=dist, aspect_ratio_correction=aspect)
        except Exception:
            pass

    def on_frame_received(self, frame):
        # UI Housekeeping on first successful frame
        if self.btn_preview.text() == "⌛ Connecting...":
            self.btn_preview.setEnabled(True)
            self.btn_preview.setText("Stop Test Feed")
            self.btn_preview.setStyleSheet("""
                QPushButton { background-color: #EF4444; color: white; border-radius: 8px; font-weight: bold; }
                QPushButton:hover { background-color: #DC2626; }
            """)
            
        out_frame = frame
        if hasattr(self, 'aruco_debug_active') and self.aruco_debug_active:
            try:
                ms = float(self.marker_size_input.text() or 50.0)
                success, res = detect_aruco_marker(frame, ms)
                if success:
                    out_frame = res['annotated_frame']
                    count = res.get('marker_count', 1)
                    tilt_txt = ' (TILTED!)' if res.get('is_tilted') else ''
                    self.connection_status.setText(f"Live: {res['mm_per_px']:.6f} mm/px | {count} markers{tilt_txt}")
                    self.connection_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                else:
                    self.connection_status.setText(f"Searching: {res['error']}")
                    self.connection_status.setStyleSheet("color: #8B95A5;")
            except Exception as e:
                self.connection_status.setText(f"Error: {str(e)[:50]}")

        # Convert to Pixmap and Display
        try:
            frame_rgb = cv2.cvtColor(out_frame, cv2.COLOR_BGR2RGB)
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
        self.preview_box.setStyleSheet("background-color: #3B1515; border: 1px solid #EF4444; color: #EF4444; border-radius: 10px; font-weight: bold;")

    def on_connection_lost(self):
        self.stop_preview()
        self.preview_box.setText("Connection lost.\nCheck camera or network.")
        self.preview_box.setStyleSheet("background-color: #3B2B10; border-radius: 10px; color: #F59E0B; font-weight: bold;")

    def stop_preview(self):
        if self.cap_thread:
            self.cap_thread.stop()
            self.cap_thread = None
            
        self.preview_box.setText("Camera\nPreview")
        self.preview_box.setStyleSheet(f"background-color: #1E2330; border-radius: 10px; color: #8B95A5; font-size: 16px; font-weight: bold; border: 1px solid #3A4150;")
        self.preview_box.setPixmap(QPixmap())
        self.btn_preview.setText("Start Test Feed")
        self.btn_preview.setStyleSheet("""
            QPushButton { background-color: #3B82F6; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        
    
    def close_overlay(self):
        self.stop_preview()
        super().close_overlay()

    def apply_settings_clicked(self):
        """Save settings without closing overlay"""
        self.save_current_settings()
        self.connection_status.setText("Settings applied!")
        self.connection_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        # Briefly change color to show feedback
        original_style = self.connection_status.styleSheet()
        QTimer.singleShot(2000, lambda: self.connection_status.setStyleSheet(original_style))

    def save_settings_clicked(self):
        """Save settings and close overlay"""
        self.save_current_settings()
        self.close_overlay()

    def save_current_settings(self):
        """Internal helper to gather and save settings"""
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
            
        self.settings["aruco_marker_size"] = float(self.marker_size_input.text() or 50.0)
        self.settings["mounting_height"] = float(self.cam_height_input.text() or 1000.0)
        self.settings["sandal_thickness"] = float(self.obj_thickness_input.text() or 0.0)
        self.settings["mm_per_px"] = float(self.mmpx_input.text() or 0.21)
        self.settings["sensor_delay"] = float(self.delay_input.text() or 0.2)
        
        # Save Crop & Rotation
        self.settings["camera_crop"] = {
            "left": int(self.crop_left.text() or 0),
            "right": int(self.crop_right.text() or 0),
            "top": int(self.crop_top.text() or 0),
            "bottom": int(self.crop_bottom.text() or 0),
            "rotation": self.rotation_combo.currentData()
        }
        
        # Save Aspect & Resolution
        self.settings["aspect_ratio_correction"] = self.parse_aspect_ratio_input(self.aspect_ratio_input.text())
        self.settings["force_width"] = int(self.force_w.text() or 0)
        self.settings["force_height"] = int(self.force_h.text() or 0)

        # Save Distortion
        self.settings["lens_distortion"] = {
            "k1": float(self.k1.text() or 0), "k2": float(self.k2.text() or 0),
            "p1": float(self.p1.text() or 0), "p2": float(self.p2.text() or 0), "k3": float(self.k3.text() or 0),
            "fx": float(self.fx.text() or 0), "fy": float(self.fy.text() or 0),
            "cx": float(self.cx.text() or 0), "cy": float(self.cy.text() or 0)
        }
        self.settings["auto_estimate_matrix"] = self.btn_auto_matrix.isChecked()

        # Save Layout & Model
        mode_idx = self.layout_combo.currentIndex()
        self.settings["layout_mode"] = ["classic", "split", "minimal"][mode_idx]
        self.settings["detection_model"] = self.det_model.currentData()
        
        self.settings["ip_camera_presets"] = self.ip_presets
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
                background-color: #252A34;
                border-radius: {UIScaling.scale(8)}px;
                color: #8B95A5;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: bold;
                padding: {UIScaling.scale(8)}px {UIScaling.scale(15)}px;
                border: 1px solid #3A4150;
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

    # -------------------------------------------------------------------------
    # Auto Calibration Logic
    # -------------------------------------------------------------------------

    def run_auto_calibration(self):
        """Capture frame and run ArUco detection for auto mm/px calibration"""
        # 1. Validation: Is camera active?
        if self.cap_thread is None or not self.cap_thread.isRunning():
            self.connection_status.setText("Error: Camera must be active (Start Test Feed first)")
            self.connection_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return

        # 2. Get Marker Size
        try:
            marker_size = float(self.marker_size_input.text())
            if marker_size <= 0: raise ValueError
        except ValueError:
            self.connection_status.setText("Error: Invalid Marker Size")
            self.connection_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return

        # 3. Capture Frame
        # We need to get the latest frame from the capture thread
        frame = getattr(self.cap_thread, 'last_frame', None)
        if frame is None:
            self.connection_status.setText("Error: No frame captured from camera")
            self.connection_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return

        # 4. Detect Marker
        self.btn_run_calibration.setEnabled(False)
        self.btn_run_calibration.setText("Detecting...")
        
        success, result = detect_aruco_marker(frame, marker_size)
        
        if not success:
            self.connection_status.setText(f"Error: {result['error']}")
            self.connection_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            self.btn_run_calibration.setEnabled(True)
            self.btn_run_calibration.setText("Run Auto Calibration")
            return

        # 5. Success - Show Confirmation Dialog
        self.connection_status.setText("Marker detected!")
        self.connection_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        try:
            current_mmpx = float(self.mmpx_input.text() or 0.21)
        except:
            current_mmpx = 0.21

        dialog = ArucoCalibrationDialog(self, result, current_mmpx)
        if dialog.exec():
            # User accepted
            new_mmpx = dialog.get_result()
            self.mmpx_input.setText(f"{new_mmpx:.8f}")
            self.connection_status.setText(f"Calibrated: {new_mmpx:.6f} mm/px applied")
            self.connection_status.setStyleSheet("color: #22C55E; font-weight: bold;")
        else:
            self.connection_status.setText("Calibration cancelled by user")
            self.connection_status.setStyleSheet("color: #8B95A5;")

        self.btn_run_calibration.setEnabled(True)
        self.btn_run_calibration.setText("Run Auto Calibration")

