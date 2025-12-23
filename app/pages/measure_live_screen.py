
import cv2
import os
import datetime
import random
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QSizePolicy, QGridLayout, QMenu, QWidgetAction,
    QLineEdit, QScrollArea, QApplication, QScroller
)
from PySide6.QtCore import Qt, QTimer, QSize, QRect, Signal
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QAction, QDoubleValidator, QFont

import numpy as np
from model.measure_live_sandals import measure_live_sandals
from project_utilities.json_utility import JsonUtility
from app.widgets.preset_profile_overlay import PresetProfileOverlay, PROFILES_FILE
from app.utils.theme_manager import ThemeManager
from app.utils.camera_utils import open_video_capture
from app.utils.capture_thread import VideoCaptureThread
from app.utils.ui_scaling import UIScaling

# Global list to hold stuck threads so they aren't garbage collected abruptly
_zombie_threads = []

# Sensor trigger (optional - import safely)
try:
    from input.sensor_trigger import get_sensor, SensorConfig
    SENSOR_AVAILABLE = True
except ImportError:
    SENSOR_AVAILABLE = False

# PLC Modbus trigger (optional - import safely)
try:
    from input.plc_modbus_trigger import PLCModbusTrigger, ModbusConfig, check_pymodbus_available
    PLC_AVAILABLE = check_pymodbus_available()
except ImportError:
    PLC_AVAILABLE = False


# ---------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------
PRESETS_FILE = os.path.join("output", "settings", "presets.json")
SETTINGS_FILE = os.path.join("output", "settings", "app_settings.json")

# Default Presets (Testing Grouping)
DEFAULT_PRESETS = [
    {"sku": "E-0123M", "size": "36", "color_idx": 1},
    {"sku": "E-0123M", "size": "37", "color_idx": 1},
    {"sku": "E-0123M", "size": "38", "color_idx": 1},
    {"sku": "E-0123M", "size": "39", "color_idx": 1},
    {"sku": "E-0123M", "size": "40", "color_idx": 1},
    {"sku": "E-0123M", "size": "41", "color_idx": 1},
    {"sku": "E-0123M", "size": "42", "color_idx": 1},
    {"sku": "E-0123M", "size": "43", "color_idx": 1},

    {"sku": "E-9008L", "size": "36", "color_idx": 2},
    {"sku": "E-9008L", "size": "37", "color_idx": 2},
    {"sku": "E-9008L", "size": "38", "color_idx": 2},
    {"sku": "E-9008L", "size": "39", "color_idx": 2},
    {"sku": "E-9008L", "size": "40", "color_idx": 2},
    {"sku": "E-9008L", "size": "41", "color_idx": 2},

    {"sku": "X-5000-Pro", "size": "XS", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "S", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "M", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "L", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "XL", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "XXL", "color_idx": 3},

    {"sku": "A-1001X", "size": "37", "color_idx": 2},
    {"sku": "A-1001X", "size": "38", "color_idx": 2},
    {"sku": "A-1001X", "size": "39", "color_idx": 2},
    {"sku": "A-1001X", "size": "40", "color_idx": 2},
    {"sku": "A-1001X", "size": "41", "color_idx": 2},
    {"sku": "A-1001X", "size": "42", "color_idx": 2},
]


# Colors for SKUs
# 0: Gray (Empty), 1: Blue, 2: Pink, 3: Purple, 4: Orange
SKU_COLORS = {
    0: "#B0BEC5", # Gray
    1: "#2196F3", # Blue
    2: "#E91E63", # Pink
    3: "#9C27B0", # Purple
    4: "#FF9800"  # Orange
}

class LiveCameraScreen(QWidget):
    # Signal for sensor trigger (thread-safe)
    sensor_triggered = Signal()
    # Signal for PLC trigger (thread-safe)
    plc_triggered = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowTitle("Live Camera QC")
        
        self.theme = ThemeManager.get_colors() # Initialize theme here
        
        
        # Team Layout State
        self.team_layout_order = "A_LEFT" # or "B_LEFT"
        
        # State
        self.good_count = 0
        self.bs_count = 0
        self.current_sku = "---"
        self.current_size = "---"
        self.last_result = None
        
        # Profile State
        self.active_profile_id = None
        self.active_profile_data = {}
        self.presets = DEFAULT_PRESETS # Added from instruction
        
        # Load Data
        self.load_settings()
        self.load_active_profile() # Replaces direct load_presets
        
        # Camera Setup
        self.cap_thread = None
        self.live_frame = None
        self.captured_frame = None
        self.is_paused = False # If True, show captured_frame instead of live_frame

        # Process State (Added from instruction)
        self.camera_thread = None
        self.last_frame = None
        self.last_results = None

        # UI Setup
        self.init_ui()
        
        # Spacebar shortcut for force capture (testing)
        from PySide6.QtGui import QShortcut, QKeySequence
        self.capture_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.capture_shortcut.activated.connect(self.capture_frame)
        
        # Sensor trigger setup
        self.sensor = None
        self.sensor_enabled = False
        self.sensor_triggered.connect(self.capture_frame)  # Thread-safe signal
        if SENSOR_AVAILABLE:
            self.setup_sensor()
        
        # PLC Modbus trigger setup
        self.plc_trigger = None
        self.plc_enabled = False
        self.plc_triggered.connect(self.capture_frame)  # Thread-safe signal
        if PLC_AVAILABLE:
            self.setup_plc_trigger()
        
    def open_profile_dialog(self):
        # Check password first
        from app.widgets.password_dialog import PasswordDialog
        
        if not PasswordDialog.authenticate(self):
            return  # Password incorrect or cancelled
        
        # Instantiate overlay with 'self' as parent so it covers this screen
        overlay = PresetProfileOverlay(self)
        overlay.profile_selected.connect(self.on_profile_selected)
        # No exec(), just let it exist. It manages its own show/close.
    
    
    def on_switch_sides(self):
        # Toggle side preference
        if self.team_layout_order == "A_LEFT":
            self.team_layout_order = "B_LEFT"
        else:
            self.team_layout_order = "A_LEFT"
            
        print(f"Switched sides: {self.team_layout_order}")
        # Re-render presets
        self.render_presets()
    
    def on_profile_selected(self, profile_data):
        # Update active profile when selected from dialog
        self.active_profile_id = profile_data.get("id")
        self.active_profile_data = profile_data
        self.presets = profile_data.get("presets", DEFAULT_PRESETS)
        
        # Save the active profile ID
        self.save_settings()
        
        # Update UI
        self.update_info_bar()
        self.render_presets()

    def init_ui(self):
        # Use theme variables
        self.setStyleSheet(f"background-color: {self.theme['bg_main']}; color: {self.theme['text_main']};")
        
        if self.layout_mode == "classic":
            self.setup_classic_layout()
        else:
            self.setup_split_layout()
            
        # Create Settings Menu (Hidden)
        self.create_settings_menu()
        
        # Initial UI Update
        self.update_info_bar()

    def setup_split_layout(self):
        # Main Layout: Left (Presets) vs Right (Preview/Stats)
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(10, 10, 10, 10)
        main_h_layout.setSpacing(10)
        self.setLayout(main_h_layout)

        # ---------------------------------------------------------------------
        # LAYOUT STRUCTURE: 
        # Left Panel (Team 1) | Middle Panel (Preview/Stats) | Right Panel (Team 2)
        # ---------------------------------------------------------------------

        # --- LEFT PANEL (30%) ---
        self.left_panel = QFrame()
        self.left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)
        
        # Presets container for Left side
        self.left_presets_container = QWidget()
        self.left_presets_layout = QVBoxLayout(self.left_presets_container)
        self.left_presets_layout.setSpacing(10)
        self.left_presets_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header for Left Panel (e.g. "Team A")
        self.lbl_left_team = QLabel("Team A")
        self.lbl_left_team.setAlignment(Qt.AlignCenter)
        team_font_size = UIScaling.scale_font(20)
        self.lbl_left_team.setStyleSheet(f"font-weight: bold; font-size: {team_font_size}px; color: {self.theme['text_main']}; padding: 5px;")
        
        self.left_layout.addWidget(self.lbl_left_team)
        self.left_layout.addWidget(self.left_presets_container, stretch=1)
        
        
        # --- RIGHT PANEL (30%) ---
        self.right_panel = QFrame()
        self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)
        
        # Presets container for Right side
        self.right_presets_container = QWidget()
        self.right_presets_layout = QVBoxLayout(self.right_presets_container)
        self.right_presets_layout.setSpacing(10)
        self.right_presets_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header for Right Panel (e.g. "Team B")
        self.lbl_right_team = QLabel("Team B")
        self.lbl_right_team.setAlignment(Qt.AlignCenter)
        self.lbl_right_team.setStyleSheet(f"font-weight: bold; font-size: {team_font_size}px; color: {self.theme['text_main']}; padding: 5px;")
        
        self.right_layout.addWidget(self.lbl_right_team)
        self.right_layout.addWidget(self.right_presets_container, stretch=1)


        # --- MIDDLE PANEL (40%) ---
        middle_panel = self._create_camera_panel()

        # Add to Main Layout: 35% - 30% - 35%
        # Middle (30%) is smaller than original 40% but bigger than 26%.
        # Reverting fixed width to allow proportional scaling.
        self.left_panel.setFixedWidth(16777215) # Unlock fixed width
        self.right_panel.setFixedWidth(16777215) # Unlock fixed width
        self.left_panel.setMinimumWidth(UIScaling.scale(50)) # Allow shrinking
        self.right_panel.setMinimumWidth(UIScaling.scale(50)) # Allow shrinking
        self.left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_h_layout.addWidget(self.left_panel, 35)
        main_h_layout.addWidget(middle_panel, 30)
        main_h_layout.addWidget(self.right_panel, 35)
        
        self.setLayout(main_h_layout)

        # Render Presets (Will populate left/right containers)
        self.render_presets()
        
        # Create Settings Menu (Hidden)
        self.create_settings_menu()
        
        # Initial UI Update
        self.update_info_bar()

    # ------------------------------------------------------------------
    # Data / Logic
    # ------------------------------------------------------------------
    def load_active_profile(self):
        # 1. Load profiles to ensure at least one exists (seeds file if needed)
        # We can reuse logic from Dialog or just look at file
        # But Dialog logic seeds it. Let's just try loading.
        profiles = JsonUtility.load_from_json(PROFILES_FILE)
        
        # If no profiles file, just create defaults here too? 
        # Or instantiate Dialog once to seed it? 
        # Let's seed defaults here if missing to be safe
        if not profiles:
            profiles = [
                {
                    "id": "default-1",
                    "name": "Shift 1",
                    "sub_label": "Team A",
                    "sku_label": "SKU E 9008 M",
                    "last_updated": datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
                    "presets": DEFAULT_PRESETS
                }
            ]
            JsonUtility.save_to_json(PROFILES_FILE, profiles)
            
        # 2. Find Active Profile
        self.active_profile_data = None
        if self.active_profile_id:
            for p in profiles:
                if p.get("id") == self.active_profile_id:
                    self.active_profile_data = p
                    break
        
        # 3. Fallback if not found
        if not self.active_profile_data and profiles:
            self.active_profile_data = profiles[0]
            self.active_profile_id = self.active_profile_data.get("id")
            self.save_settings() # Save the fallback ID
            
        # 4. Set Presets
        if self.active_profile_data:
            loaded_presets = self.active_profile_data.get("presets", [])
            # Validate length
            if loaded_presets:
                self.presets = loaded_presets
            else:
                self.presets = DEFAULT_PRESETS 
        else:
            self.presets = DEFAULT_PRESETS

    def update_info_bar(self):
        if self.active_profile_data:
            name = self.active_profile_data.get("name", "")
            sub = self.active_profile_data.get("sub_label", "")
            date_str = self.active_profile_data.get("last_updated", "").split(",")[0]
            self.info_bar.setText(f" {name}, {sub}            {date_str}")
        else:
            self.info_bar.setText(" No Profile Selected ")

    def load_settings(self):
        self.settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        if self.settings:
            self.mm_per_px = self.settings.get("mm_per_px", 0.215984148)
            self.camera_index = self.settings.get("camera_index", 0)
            self.active_profile_id = self.settings.get("active_profile_id", None)
            self.layout_mode = self.settings.get("layout_mode", "split") # split or classic
            
            # Handle IP Preset data
            self.ip_presets = self.settings.get("ip_camera_presets", [])
            self.active_ip_preset_id = self.settings.get("active_ip_preset_id", None)
        else:
            self.mm_per_px = 0.215984148
            self.camera_index = 0
            self.active_profile_id = None
            self.layout_mode = "split"
            self.ip_presets = []
            self.active_ip_preset_id = None

    def setup_classic_layout(self):
        # Classic Layout: Left (Presets Grid) | Right (Preview/Stats)
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(10, 10, 10, 10)
        main_h_layout.setSpacing(10)
        self.setLayout(main_h_layout)

        # --- LEFT PANEL (Presets) 30% ---
        self.left_panel = QFrame()
        self.left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)
        
        # Header for Presets
        lbl_presets_header = QLabel("Presets")
        lbl_presets_header.setAlignment(Qt.AlignCenter)
        header_font_size = UIScaling.scale_font(20)
        lbl_presets_header.setStyleSheet(f"font-weight: bold; font-size: {header_font_size}px; color: {self.theme['text_main']}; padding: 5px;")
        
        self.left_layout.addWidget(lbl_presets_header)
        
        # Presets container (Single container for all)
        self.classic_presets_container = QWidget()
        self.classic_presets_layout = QVBoxLayout(self.classic_presets_container)
        self.classic_presets_layout.setSpacing(10)
        self.classic_presets_layout.setContentsMargins(0, 0, 0, 0)
        
        self.left_layout.addWidget(self.classic_presets_container, 1)

        # --- RIGHT PANEL (Camera/Stats) 70% ---
        self.right_panel = QFrame() # Reusing right_panel name for the camera side in classic 
        self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)

        # Camera Panel reused
        self.camera_panel_widget = self._create_camera_panel()
        self.right_layout.addWidget(self.camera_panel_widget)

        # Add Panels to Main Layout
        main_h_layout.addWidget(self.left_panel, 70)
        main_h_layout.addWidget(self.right_panel, 30)
        
        # Render Presets
        self.render_presets()
        
    def _create_camera_panel(self):
        panel = QFrame()
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Top Controls: Back | Info | Edit | Switch | Settings
        top_ctrl_layout = QHBoxLayout()
        
        ctrl_btn_size = UIScaling.scale(50)
        ctrl_btn_radius = ctrl_btn_size // 2
        ctrl_btn_font_size = UIScaling.scale_font(24)
        
        # Back
        self.back_button = QPushButton("←")
        self.back_button.setFixedSize(ctrl_btn_size, ctrl_btn_size)
        self.back_button.setStyleSheet(f"QPushButton {{ background: #F5F5F5; color: #333333; border-radius: {ctrl_btn_radius}px; font-size: {ctrl_btn_font_size}px; border: 1px solid #E0E0E0; }} QPushButton:hover {{ background: #E8E8E8; }}")
        # Ensure only one connection if reused? 
        # Actually create_camera_panel creates NEW instances of buttons.
        # So we need to connect them here.
        self.back_button.clicked.connect(self.go_back)
        
        # Info Bar (Compact)
        self.info_bar = QLabel(" Loading... ")
        info_bar_font_size = UIScaling.scale_font(12) 
        info_bar_radius = UIScaling.scale(5)
        self.info_bar.setAlignment(Qt.AlignCenter)
        self.info_bar.setStyleSheet(f"background-color: #F5F5F5; color: #333333; padding: 5px; border-radius: {info_bar_radius}px; font-weight: bold; font-size: {info_bar_font_size}px;")
        self.info_bar.setFixedHeight(ctrl_btn_size)
        
        # Edit Button
        btn_edit = QPushButton("Edit")
        btn_edit.setFixedSize(UIScaling.scale(60), ctrl_btn_size)
        btn_edit_font_size = UIScaling.scale_font(12)
        btn_edit.setStyleSheet(f"background-color: #F5F5F5; border-radius: {info_bar_radius}px; color: #333333; border: 1px solid #E0E0E0; font-size: {btn_edit_font_size}px;")
        btn_edit.clicked.connect(self.open_profile_dialog)
        
        # Switch Button (Arrows)
        self.btn_switch = QPushButton("⇄")
        self.btn_switch.setFixedSize(ctrl_btn_size, ctrl_btn_size)
        self.btn_switch.setStyleSheet(f"QPushButton {{ background: #E3F2FD; color: #1565C0; border-radius: {ctrl_btn_radius}px; font-size: {ctrl_btn_font_size}px; border: 1px solid #BBDEFB; }} QPushButton:hover {{ background: #BBDEFB; }}")
        self.btn_switch.clicked.connect(self.on_switch_sides)
        
        # Settings
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(ctrl_btn_size, ctrl_btn_size)
        self.settings_btn.setStyleSheet(f"QPushButton {{ background: #F5F5F5; color: #333333; border-radius: {ctrl_btn_radius}px; font-size: {ctrl_btn_font_size}px; border: 1px solid #E0E0E0; }} QPushButton:hover {{ background: #E8E8E8; }}")
        self.settings_btn.clicked.connect(self.show_settings_menu)
        
        top_ctrl_layout.addWidget(self.back_button)
        top_ctrl_layout.addWidget(self.info_bar, 1) 
        top_ctrl_layout.addWidget(btn_edit)
        top_ctrl_layout.addWidget(self.btn_switch)
        top_ctrl_layout.addWidget(self.settings_btn)
        
        layout.addLayout(top_ctrl_layout)
        
        # Preview Label
        self.preview_label = QLabel("Review\nFrameshot")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_font_size = UIScaling.scale_font(36)
        preview_radius = UIScaling.scale(8)
        preview_border = UIScaling.scale(3)
        self.preview_label.setStyleSheet(f"""
            background-color: #F8F8F8; color: #AAAAAA; border-radius: {preview_radius}px; font-weight: bold; font-size: {preview_font_size}px; border: {preview_border}px solid #E0E0E0;
        """)
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview_label.setMinimumSize(UIScaling.scale(200), UIScaling.scale(150))
        
        layout.addWidget(self.preview_label, stretch=1)
        
        # Counters
        counters_layout = QHBoxLayout()
        counters_layout.setSpacing(UIScaling.scale(10))
        
        counter_font_size = UIScaling.scale_font(28)
        counter_height = UIScaling.scale(100) # Smaller height
        counter_radius = UIScaling.scale(5)
        
        self.lbl_good = QLabel(f"{self.good_count}\nGood")
        self.lbl_good.setAlignment(Qt.AlignCenter)
        self.lbl_good.setFixedHeight(counter_height)
        self.lbl_good.setStyleSheet(f"background-color: #66BB6A; color: white; font-weight: bold; font-size: {counter_font_size}px; border-radius: {counter_radius}px;")
        
        self.lbl_bs = QLabel(f"{self.bs_count}\nBS")
        self.lbl_bs.setAlignment(Qt.AlignCenter)
        self.lbl_bs.setFixedHeight(counter_height)
        self.lbl_bs.setStyleSheet(f"background-color: #D32F2F; color: white; font-weight: bold; font-size: {counter_font_size}px; border-radius: {counter_radius}px;")
        
        counters_layout.addWidget(self.lbl_good)
        counters_layout.addWidget(self.lbl_bs)
        
        layout.addLayout(counters_layout)
        
        # Big Result
        self.lbl_big_result = QLabel("-\nIDLE")
        self.lbl_big_result.setAlignment(Qt.AlignCenter)
        self.lbl_big_result.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        big_result_font_size = UIScaling.scale_font(48)
        big_result_radius = UIScaling.scale(15)
        self.lbl_big_result.setStyleSheet(f"color: #999999; background-color: white; font-size: {big_result_font_size}px; font-weight: 900; border-radius: {big_result_radius}px; border: 4px solid #E0E0E0;")
        
        layout.addWidget(self.lbl_big_result, stretch=2)
        
        # Details Box
        details_layout = QGridLayout()
        self.lbl_detail_sku = QLabel("SKU/Size :")
        self.val_detail_sku = QLabel("---/---")
        self.lbl_detail_len = QLabel("Length :")
        self.val_detail_len = QLabel("-")
        self.lbl_detail_wid = QLabel("Width :")
        self.val_detail_wid = QLabel("-")
        self.lbl_detail_res = QLabel("Result :")
        self.val_detail_res = QLabel("-")
        
        detail_font_size = UIScaling.scale_font(18)
        label_style = f"font-weight: bold; color: #999999; font-size: {detail_font_size}px;"
        val_style = f"font-weight: bold; color: #333333; font-size: {detail_font_size}px;"
        
        for w in [self.lbl_detail_sku, self.lbl_detail_len, self.lbl_detail_wid, self.lbl_detail_res]: w.setStyleSheet(label_style)
        for w in [self.val_detail_sku, self.val_detail_len, self.val_detail_wid, self.val_detail_res]: 
            w.setAlignment(Qt.AlignRight)
            w.setStyleSheet(val_style)
            
        details_layout.addWidget(self.lbl_detail_sku, 0, 0); details_layout.addWidget(self.val_detail_sku, 0, 1)
        details_layout.addWidget(self.lbl_detail_len, 1, 0); details_layout.addWidget(self.val_detail_len, 1, 1)
        details_layout.addWidget(self.lbl_detail_wid, 2, 0); details_layout.addWidget(self.val_detail_wid, 2, 1)
        details_layout.addWidget(self.lbl_detail_res, 3, 0); details_layout.addWidget(self.val_detail_res, 3, 1)
        
        layout.addLayout(details_layout)
        
        return panel 

            
    def save_settings(self):
        # We should load existing settings first to not overwrite other fields
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        
        settings.update({
            "mm_per_px": self.mm_per_px,
            "camera_index": self.camera_index,
            "active_profile_id": self.active_profile_id,
            "ip_camera_username": self.ip_camera_username,
            "ip_camera_password": self.ip_camera_password
        })
        JsonUtility.save_to_json(SETTINGS_FILE, settings)



    def render_presets(self):
        # Handle Layout Modes
        if self.layout_mode == "classic":
            # CLASSIC MODE: All presets in left panel, but split by Team A (Left) and B (Right)
            if hasattr(self, 'btn_switch'): 
                self.btn_switch.setVisible(False)
                
            self._clear_layout(self.classic_presets_layout)
            
            # Create a Horizontal Split within the Left Panel
            h_split_widget = QWidget()
            h_split = QHBoxLayout(h_split_widget)
            h_split.setContentsMargins(0, 0, 0, 0)
            h_split.setSpacing(10)
            
            # Team A Container
            container_A = QWidget()
            layout_A = QVBoxLayout(container_A)
            layout_A.setContentsMargins(0, 0, 0, 0)
            
            # Team B Container
            container_B = QWidget()
            layout_B = QVBoxLayout(container_B)
            layout_B.setContentsMargins(0, 0, 0, 0)
            
            # Filter Presets
            presets_A = [p for p in self.presets if p.get("team", "A") == "A"]
            presets_B = [p for p in self.presets if p.get("team", "A") == "B"]
            
            # Render to respective layouts
            self._render_presets_auto_fit(presets_A, layout_A)
            self._render_presets_auto_fit(presets_B, layout_B)
            
            # Add to Split Layout (50/50 split within the 55% panel)
            h_split.addWidget(container_A, 50)
            h_split.addWidget(container_B, 50)
            
            # Add Split Widget to Main Classic Layout
            self.classic_presets_layout.addWidget(h_split_widget)

        else:
            # SPLIT MODE: Team A/B Logic
            if hasattr(self, 'btn_switch'): 
                self.btn_switch.setVisible(True)
                
            # 1. Determine which team goes where
            # Default: A is Left, B is Right
            left_team = "A"
            right_team = "B"
            
            if self.team_layout_order == "B_LEFT":
                left_team = "B"
                right_team = "A"
                
            # 2. Update Headers
            self.lbl_left_team.setText(f"Team {left_team}")
            self.lbl_right_team.setText(f"Team {right_team}")
            
            # 3. Filter Presets
            presets_left = []
            presets_right = []
            
            for p in self.presets:
                p_team = p.get("team", "A") # Default to A
                if p_team == left_team:
                    presets_left.append(p)
                elif p_team == right_team:
                    presets_right.append(p)
                    
            # 4. Clear existing items
            self._clear_layout(self.left_presets_layout)
            self._clear_layout(self.right_presets_layout)
            
            # 5. Render to layouts
            self._render_presets_auto_fit(presets_left, self.left_presets_layout)
            self._render_presets_auto_fit(presets_right, self.right_presets_layout)
        
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            else:
                layout = item.layout()
                if layout:
                    self._clear_layout(layout)

    def _render_presets_auto_fit(self, presets, parent_layout):
        """
        Renders presets into parent_layout using a dynamic Auto-Fit approach.
        - No ScrollArea.
        - Groups are distributed evenly vertically (stretch=1).
        - Buttons expand to fill space.
        """
        if not presets:
            lbl_empty = QLabel("No Presets")
            lbl_empty.setAlignment(Qt.AlignCenter)
            parent_layout.addWidget(lbl_empty)
            return

        # Group by SKU
        grouped = {}
        order = []
        for p in presets:
            sku = p.get("sku", "Unknown SKU") or "Unknown SKU"
            if sku not in grouped:
                grouped[sku] = []
                order.append(sku)
            grouped[sku].append(p)
            
        # Create a container widget for each group to ensure equal vertical distribution
        for sku in order:
            items = grouped[sku]
            
            # Group Container (Header + Grid)
            group_container = QWidget()
            group_layout = QVBoxLayout(group_container)
            group_layout.setContentsMargins(0, 5, 0, 5)
            group_layout.setSpacing(5)
            
            # Header
            lbl_header = QLabel(sku)
            header_font_size = UIScaling.scale_font(18)
            lbl_header.setStyleSheet(f"font-size: {header_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
            lbl_header.setAlignment(Qt.AlignLeft)
            group_layout.addWidget(lbl_header)
            
            # Grid of Buttons
            grid = QGridLayout()
            grid.setSpacing(UIScaling.scale(10))
            grid.setContentsMargins(0, 0, 0, 0)
            
            columns = 3 # Fixed columns for consistency
            
            btn_radius = UIScaling.scale(12)
            btn_font_size = UIScaling.scale_font(32) # Slightly smaller to fit grid
            
            for i, p in enumerate(items):
                r, c = divmod(i, columns)
                
                size = p.get("size", "??")
                color_idx = p.get("color_idx", 0)
                bg_color = SKU_COLORS.get(color_idx, "#E0E0E0")
                
                btn = QPushButton(str(size))
                # Dynamic Sizing: Expanding Policy
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setStyleSheet(f"background-color: {bg_color}; border: none; border-radius: {btn_radius}px; color: #000000; font-weight: bold; font-size: {btn_font_size}px; padding: 5px;")
                
                try:
                    global_idx = self.presets.index(p)
                except ValueError:
                    global_idx = -1
                
                btn.clicked.connect(lambda _, idx=global_idx: self.on_preset_clicked(idx))
                
                grid.addWidget(btn, r, c)
            
            # Add grid to group layout, stretching to fill remaining space in group
            group_layout.addLayout(grid, stretch=1)
            
            # Add Group Container to Parent, with stretch=1 (Equal height for all groups)
            parent_layout.addWidget(group_container, stretch=1)

    def on_preset_clicked(self, idx):
        if idx < 0 or idx >= len(self.presets):
            return
            
        p = self.presets[idx]
        self.current_sku = p.get("sku", "---")
        self.current_size = p.get("size", "---")
        
        # Update UI
        self.val_detail_sku.setText(f"{self.current_sku}/{self.current_size}")
        print(f"Selected Preset {idx}: {self.current_sku} / {self.current_size}")

    def capture_frame(self):
        if self.live_frame is None:
            return
            
        self.is_paused = True # Freeze preview
        
        # Process
        results, processed = measure_live_sandals(
            self.live_frame.copy(),
            mm_per_px=self.mm_per_px,
            draw_output=True,
            save_out=None # Optional: save to file
        )
        
        self.captured_frame = processed
        
        # Display Results
        if results:
            r = results[0]
            length_mm = r.get("real_length_mm", 0)
            width_mm = r.get("real_width_mm", 0) # Assumed exist
            # If not in dict, calc from cm
            if not width_mm: width_mm = r.get("real_width_cm", 0) * 10
            
            pf = r.get("pass_fail", "FAIL")
            
            self.val_detail_len.setText(f"{length_mm:.2f} mm")
            self.val_detail_wid.setText(f"{width_mm:.2f} mm")
            self.val_detail_res.setText(pf)
            
            # BIG Style: White BG, Dark Text, Colored Background
            # Content: SIZE on top (Big), STATUS on bottom (Smaller)
            display_size = self.current_size if self.current_size != "---" else "-"
            
            res_font_size = UIScaling.scale_font(48)
            res_padding = UIScaling.scale(20)
            res_radius = UIScaling.scale(15)
            
            if pf == "PASS":
                self.good_count += 1
                self.lbl_big_result.setText(f"{display_size}\nGOOD")
                self.lbl_big_result.setStyleSheet(f"color: white; background-color: #4CAF50; padding: {res_padding}px; border-radius: {res_radius}px; border: none; font-size: {res_font_size}px; font-weight: 900;")
                # Write random 1-4 to PLC register 13 for GOOD
                self._write_plc_result(is_good=True)
            else:
                self.bs_count += 1
                self.lbl_big_result.setText(f"{display_size}\nREJECT")
                self.lbl_big_result.setStyleSheet(f"color: white; background-color: #D32F2F; padding: {res_padding}px; border-radius: {res_radius}px; border: none; font-size: {res_font_size}px; font-weight: 900;")
                # Write random 5-8 to PLC register 13 for BS
                self._write_plc_result(is_good=False)
                
            self.update_counters()
            
        else:
            self.val_detail_res.setText("-")
            self.val_detail_len.setText("-")
            self.val_detail_wid.setText("-")
            self.lbl_big_result.setText("-\nIDLE")
            # Idle: Grey text on white
            res_font_size = UIScaling.scale_font(48)
            res_padding = UIScaling.scale(20)
            res_radius = UIScaling.scale(15)
            self.lbl_big_result.setStyleSheet(f"color: #999999; background-color: white; font-size: {res_font_size}px; font-weight: 900; padding: {res_padding}px; border-radius: {res_radius}px; border: 4px solid #E0E0E0;")

            
        # Update Preview with processed frame
        self.show_image(self.captured_frame)
        
        # Auto-resume after showing result (allows sensor to trigger again)
        QTimer.singleShot(1500, self.resume_live)  # Resume after 1.5 seconds

    def update_counters(self):
        self.lbl_good.setText(f"{self.good_count}\nGood")
        self.lbl_bs.setText(f"{self.bs_count}\nBS")

    # ------------------------------------------------------------------
    # Camera & Frame Handling
    # ------------------------------------------------------------------
    def on_frame_received(self, frame):
        """Called by VideoCaptureThread when a new frame is available"""
        self.live_frame = frame
        
        # We don't display it live on the main preview, 
        # but we could if we wanted to. 
        # The logic here is that we only show the "Captured" (paused) frame.
        pass

    def show_image(self, frame):
        if frame is None: return
        
        # Convert to Pixmap
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        
        # Scale to label using KeepAspectRatio
        # The label might be taller than the image aspect ratio, causing padding.
        # We rely on AlignmentCenter to keep it in middle.
        
        lbl_w = self.preview_label.width()
        lbl_h = self.preview_label.height()
        
        # Scale to FIT the label (Letterbox if needed), ensuring full image visibility
        # Matches 'BoxFit.contain' behavior
        pix = pix.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # No cropping logic needed
            
        self.preview_label.setPixmap(pix)
            
        self.preview_label.setPixmap(pix)
    
    def cv2_to_pixmap(self, img):
        # ... existing utility if needed ...
        pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def showEvent(self, event):
        self.start_camera()
        super().showEvent(event)
        
    def hideEvent(self, event):
        self.stop_camera()
        super().hideEvent(event)
        
    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)
        
    def start_camera(self):
        if self.cap_thread is None:
            source = self.camera_index
            
            # If IP camera is active, resolve the preset
            if source == "ip":
                preset = next((p for p in self.ip_presets if p["id"] == self.active_ip_preset_id), None)
                if not preset and self.ip_presets:
                    preset = self.ip_presets[0]
                if preset:
                    source = preset
                else:
                    source = 0 
            elif isinstance(source, str) and source.isdigit():
                source = int(source)
            
            is_ip = not isinstance(source, int)
            
            # Start background capture
            self.cap_thread = VideoCaptureThread(source, is_ip)
            self.cap_thread.frame_ready.connect(self.on_frame_received)
            self.cap_thread.connection_failed.connect(self.on_camera_connection_failed)
            self.cap_thread.start()
            
        self.is_paused = False
        
        # Start sensor if available
        self.start_sensor()
        
        # Start PLC trigger if available
        self.start_plc_trigger()
        
    def on_camera_connection_failed(self, error):
        print(f"[Live] Camera connection failed: {error}")
        error_font_size = UIScaling.scale_font(28)
        error_radius = UIScaling.scale(8)
        self.preview_label.setText(f"Camera error.\nCheck settings.")
        self.preview_label.setStyleSheet(f"background-color: #FFF2F2; color: #D32F2F; border-radius: {error_radius}px; font-weight: bold; font-size: {error_font_size}px;")



    def stop_camera(self):
        if self.cap_thread:
            self.cap_thread.stop()
            
            # If thread is still running (timeout occurred), do NOT destroy it.
            if self.cap_thread.isRunning():
                print(f"[LiveCamera] Thread {self.cap_thread} is stuck. Detaching and abandoning (zombie)...")
                # Detach from parent (so it's not destroyed when self is destroyed)
                self.cap_thread.setParent(None)
                # Keep reference globally
                _zombie_threads.append(self.cap_thread)
            else:
                self.cap_thread = None
        else:
            self.cap_thread = None
        
        # Stop sensor
        self.stop_sensor()
        
        # Stop PLC trigger
        self.stop_plc_trigger()

    def go_back(self):
        self.stop_camera()
        if self.parent_widget:
            self.parent_widget.go_back()
            
    # ------------------------------------------------------------------
    # Settings Menu
    # ------------------------------------------------------------------
    def create_settings_menu(self):
        self.settings_menu = QMenu(self)
        
        # Helper to create input fields in menu
        self.mm_input = QLineEdit()
        self.mm_input.setText(str(self.mm_per_px))
        self.mm_input.setPlaceholderText("MM per Pixel")
        self.mm_input.textChanged.connect(self.on_mm_changed)
        
        mm_action = QWidgetAction(self)
        mm_action.setDefaultWidget(self.mm_input)
        
        self.settings_menu.addAction("MM per Pixel:")
        self.settings_menu.addAction(mm_action)
        self.settings_menu.addSeparator()

        # Layout Mode Switch
        current_layout_name = "Classic" if self.layout_mode == "split" else "Split" # Toggle text
        self.settings_menu.addAction(f"Switch to {current_layout_name} Layout", self.toggle_layout_mode)
        self.settings_menu.addSeparator()
        
        # Trigger Capture manually
        self.settings_menu.addAction("Refocus / Resume Live", self.resume_live)
        self.settings_menu.addAction("Capture Frame", self.capture_frame)

    def toggle_layout_mode(self):
        new_mode = "classic" if self.layout_mode == "split" else "split"
        self.layout_mode = new_mode
        self.save_settings()
        self.reload_ui()

    def reload_ui(self):
        # Clear existing layout
        if self.layout():
            # Reparenting the layout to a temporary widget deletes it
            QWidget().setLayout(self.layout())
        
        # Re-initialize UI
        self.init_ui()
        
    def show_settings_menu(self):
        # Check settings password first
        from app.widgets.password_dialog import PasswordDialog
        
        if not PasswordDialog.authenticate(self, password_type="settings"):
            return  # Password incorrect or cancelled
        
        # Stop camera so Settings Overlay can detect it
        self.stop_camera()
        
        # Show settings overlay
        from app.widgets.settings_overlay import SettingsOverlay
        overlay = SettingsOverlay(self)
        overlay.settings_saved.connect(self.on_settings_saved)
        
        # Restart camera when overlay closes
        overlay.closed.connect(self.start_camera)
    
    def on_settings_saved(self, settings):
        """Handle settings saved from overlay"""
        # Store old mode to check for changes
        old_mode = self.layout_mode
        
        # Reload all settings from file to get the complete updated state
        self.load_settings()
        
        # If layout mode changed, reload the UI
        if self.layout_mode != old_mode:
            print(f"[Live] Layout changed from {old_mode} to {self.layout_mode}. Reloading UI...")
            self.reload_ui()
        
        # Note: Camera will be restarted via the closed signal connection
        # But if on_settings_saved is called before closed, we need to ensure camera restarts
        # The stop_camera is already called in show_settings_menu before overlay opens
        
    def on_mm_changed(self, text):
        try:
            val = float(text)
            self.mm_per_px = val
            self.save_settings()
        except ValueError:
            pass

    def resume_live(self):
        self.is_paused = False

    # ------------------------------------------------------------------
    # Sensor Trigger
    # ------------------------------------------------------------------
    def setup_sensor(self):
        """Initialize sensor trigger"""
        if not SENSOR_AVAILABLE:
            return
        
        try:
            self.sensor = get_sensor()
            # Configure sensor
            sensor_port = self.settings.get("sensor_port", "")
            
            if not sensor_port:
                 print("[Live] Sensor not configured (port empty)")
                 self.sensor = None
                 return
                 
            self.sensor.config.port = sensor_port
            self.sensor.config.trigger_threshold_cm = 30.0
            self.sensor.config.cooldown_seconds = 2.0
            
            # Set callbacks
            self.sensor.on_trigger = self.on_sensor_trigger
            self.sensor.on_connection_change = self.on_sensor_connection_change
            
            # Note: We NO LONGER call connect() here to avoid blocking initialization.
            # connect() will be called in start_sensor() which we can move to a thread if needed.
            print("[Sensor] Initialized (connection deferred)")
        except Exception as e:
            print(f"[Sensor] Setup error: {e}")
            self.sensor = None
    
    def on_sensor_trigger(self):
        """Called when sensor detects object within threshold"""
        if not self.is_paused and self.live_frame is not None:
            print("[Sensor] Trigger received - capturing frame")
            # Emit signal to safely call capture_frame on main thread
            self.sensor_triggered.emit()
    
    def on_sensor_connection_change(self, connected: bool, message: str):
        """Called when sensor connection status changes"""
        print(f"[Sensor] {'Connected' if connected else 'Disconnected'}: {message}")
    
    def start_sensor(self):
        """Start sensor reading in background"""
        if self.sensor:
            # We can start it in a separate thread if connect itself is slow
            def task():
                try:
                    if self.sensor.connect():
                        self.sensor_enabled = True
                        self.sensor.start()
                except Exception as e:
                    print(f"[Sensor] Start error: {e}")
            
            threading.Thread(target=task, daemon=True).start()
    
    def stop_sensor(self):
        """Stop sensor reading"""
        if self.sensor:
            self.sensor.stop()

    # ------------------------------------------------------------------
    # PLC Modbus Trigger
    # ------------------------------------------------------------------
    def setup_plc_trigger(self):
        """Initialize PLC Modbus trigger"""
        if not PLC_AVAILABLE:
            print("[PLC] pymodbus not available. Install with: pip install pymodbus")
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
            self.plc_trigger.on_trigger = self.on_plc_trigger
            self.plc_trigger.on_value_update = self.on_plc_value_update
            self.plc_trigger.on_connection_change = self.on_plc_connection_change
            
            self.plc_enabled = True
            print("[PLC] Modbus trigger initialized")
            
        except Exception as e:
            print(f"[PLC] Setup error: {e}")
            self.plc_trigger = None
    
    def on_plc_trigger(self):
        """Called when PLC register changes from 0 to 1"""
        if not self.is_paused and self.live_frame is not None:
            print("[PLC] TRIGGER FIRED! Capturing frame...")
            # Emit signal to safely call capture_frame on main thread
            self.plc_triggered.emit()
    
    def on_plc_value_update(self, value):
        """Called when PLC register value is read"""
        print(f"[PLC] Register value: {value}")
    
    def on_plc_connection_change(self, connected: bool, message: str):
        """Called when PLC connection status changes"""
        print(f"[PLC] {'Connected' if connected else 'Disconnected'}: {message}")
    
    def start_plc_trigger(self):
        """Start PLC Modbus polling in background"""
        if self.plc_trigger:
            def task():
                try:
                    print("[PLC] Starting Modbus in background...")
                    if self.plc_trigger.start():
                        self.plc_enabled = True
                except Exception as e:
                    print(f"[PLC] Start error: {e}")
            
            threading.Thread(target=task, daemon=True).start()
    
    def stop_plc_trigger(self):
        """Stop PLC Modbus polling"""
        if self.plc_trigger:
            print("[PLC] Stopping Modbus polling...")
            self.plc_trigger.stop()
    
    def _write_plc_result(self, is_good: bool):
        """
        Write QC result to PLC register 13.
        GOOD: random 1-4
        BS/REJECT: random 5-8
        """
        if not self.plc_trigger or not self.plc_trigger.is_connected():
            print("[PLC] Cannot write result - not connected")
            return
        
        res_reg = int(self.settings.get("plc_result_reg", 13))
        if is_good:
            value = random.randint(1, 4)
            print(f"[PLC] GOOD result - writing {value} to register {res_reg}")
        else:
            value = random.randint(5, 8)
            print(f"[PLC] BS result - writing {value} to register {res_reg}")
        
        self.plc_trigger.write_register(res_reg, value)
        
        # Read back register to verify
        read_value = self.plc_trigger.read_any_register(res_reg)
        if read_value is not None:
            print(f"[PLC] Verified - Register {res_reg} now contains: {read_value}")
        else:
            print(f"[PLC] Could not read back register 13 for verification")
