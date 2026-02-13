
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
from PySide6.QtCore import Qt, QTimer, QSize, QRect, Signal, QThread, QThread
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QAction, QDoubleValidator, QFont

import numpy as np
from model.measure_live_sandals import measure_live_sandals
from project_utilities.json_utility import JsonUtility
from app.widgets.preset_profile_overlay import PresetProfileOverlay, PROFILES_FILE
from app.utils.theme_manager import ThemeManager
from app.utils.camera_utils import open_video_capture
from app.utils.capture_thread import VideoCaptureThread
from app.utils.ui_scaling import UIScaling
from backend.size_categorization import categorize_measurement, get_category_color
from app.widgets.settings_overlay import SettingsOverlay

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

# ---------------------------------------------------------------------
# Auto Calibration Worker
# ---------------------------------------------------------------------
class AutoCalibrationWorker(QThread):
    finished = Signal(dict)
    
    def __init__(self, frame, marker_size):
        super().__init__()
        self.frame = frame
        self.marker_size = marker_size
        
    def run(self):
        try:
            from backend.aruco_utils import detect_aruco_markers
            success, result = detect_aruco_markers(self.frame, self.marker_size)
            if success:
                self.finished.emit(result)
            else:
                self.finished.emit({"success": False})
        except Exception as e:
            print(f"[AutoCalib] Error: {e}")
            self.finished.emit({"success": False})

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
        self.current_otorisasi = 0.0
        self.last_result = None
        
        # Profile State
        self.active_profile_id = None
        self.active_profile_data = {}
        self.presets = DEFAULT_PRESETS
        self._preset_click_guard = False  # Prevent double-click on presets
        self._render_debounce = False  # Prevent rapid re-renders
        
        # UI Layout Containers (initialized to None)
        self.left_presets_layout = None
        self.right_presets_layout = None
        self.classic_presets_layout = None
        
        # Load Data
        self.load_settings()
        self.load_active_profile() # Replaces direct load_presets
        
        # Camera Setup
        self.cap_thread = None
        self.live_frame = None
        self.captured_frame = None
        self.is_paused = False # If True, show captured_frame instead of live_frame

        # Auto-Calibration State
        self.autocalib_worker = None
        self.frame_counter = 0
        self.last_autocalib_time = 0
        self.autocalib_cooldown = 5.0 # Seconds
        self.autocalib_msg_timer = QTimer()
        self.autocalib_msg_timer.timeout.connect(self.hide_autocalib_msg)

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
            
        # Navigate to Profiles Page
        if self.parent_widget:
            self.parent_widget.go_to_profiles(from_live=True)

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
        # A profile was selected from the overlay — refresh live screen
        self.refresh_data()

    # ... (skipping some methods not shown here, will target show_settings_menu below)

    def show_settings_menu(self):
        # Check settings password first
        from app.widgets.password_dialog import PasswordDialog
        
        if not PasswordDialog.authenticate(self, password_type="settings"):
            return  # Password incorrect or cancelled
        
        # Open Quick Settings Overlay
        overlay = SettingsOverlay(self)
        overlay.settings_saved.connect(self.refresh_data)
        overlay.show_overlay()

    def init_ui(self):
        # Use theme variables
        self.setStyleSheet(f"background-color: {self.theme['bg_main']}; color: {self.theme['text_main']};")
        
        if self.layout_mode == "classic":
            self.setup_classic_layout()
        elif self.layout_mode == "minimal":
            self.setup_minimal_layout()
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

    def refresh_data(self):
        """Refresh settings and profile data from JSON files."""
        print("Refreshing LiveCameraScreen data...")
        old_layout_mode = getattr(self, 'layout_mode', None)
        self.load_settings()
        self.load_active_profile()
        
        # If layout mode changed, we need a full UI rebuild
        if old_layout_mode is not None and old_layout_mode != self.layout_mode:
            print(f"Layout mode changed from {old_layout_mode} to {self.layout_mode}. Rebuilding...")
            self._rebuild_ui()
        else:
            self.render_presets()
            self.update_info_bar()
            
        # Update running camera thread if active
        if self.cap_thread and self.cap_thread.isRunning():
            self.cap_thread.update_params(
                crop_params=self.camera_crop,
                distortion_params=self.lens_distortion,
                aspect_ratio_correction=self.aspect_ratio_correction
            )

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
            # Camera crop settings
            self.camera_crop = self.settings.get("camera_crop", {})
            self.lens_distortion = self.settings.get("lens_distortion", {})
            self.detection_model = self.settings.get("detection_model", "standard")
            self.mounting_height = self.settings.get("mounting_height", 1000.0)
            self.sandal_thickness = self.settings.get("sandal_thickness", 15.0)
            self.aspect_ratio_correction = self.settings.get("aspect_ratio_correction", 1.0)
            self.force_width = self.settings.get("force_width", 0)
            self.force_height = self.settings.get("force_height", 0)
        else:
            self.mm_per_px = 0.215984148
            self.camera_index = 0
            self.active_profile_id = None
            self.layout_mode = "split"
            self.ip_presets = []
            self.active_ip_preset_id = None
            self.camera_crop = {}
            self.lens_distortion = {}
            self.detection_model = "standard"
            self.mounting_height = 1000.0
            self.sandal_thickness = 15.0
            self.aspect_ratio_correction = 1.0
            self.force_width = 0
            self.force_height = 0

    def setup_minimal_layout(self):
        """Minimal Layout: Full-screen preview with overlay controls."""
        from PySide6.QtWidgets import QStackedLayout
        
        # Use Stacked Layout for Overlay
        stack = QStackedLayout()
        stack.setStackingMode(QStackedLayout.StackAll)
        self.setLayout(stack)

        # --- Layer 1: Content (Preview & Hidden Stuff) ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Full-screen Preview Label
        self.preview_label = QLabel("Waiting for Capture...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_font_size = UIScaling.scale_font(48)
        self.preview_label.setStyleSheet(f"""
            background-color: #1C1C1E; 
            color: #666666; 
            font-weight: bold; 
            font-size: {preview_font_size}px;
        """)
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        content_layout.addWidget(self.preview_label, 1)
        
        # Hidden info bar (needed for compatibility)
        self.info_bar = QLabel("")
        self.info_bar.setVisible(False)
        content_layout.addWidget(self.info_bar)
        
        # Hidden counters/details (needed for compatibility)
        self.lbl_good = QLabel("0"); self.lbl_good.setVisible(False)
        self.lbl_bs = QLabel("0"); self.lbl_bs.setVisible(False)
        self.lbl_big_result = QLabel("-"); self.lbl_big_result.setVisible(False)
        self.val_detail_sku = QLabel("-"); self.val_detail_sku.setVisible(False)
        self.val_detail_len = QLabel("-"); self.val_detail_len.setVisible(False)
        self.val_detail_wid = QLabel("-"); self.val_detail_wid.setVisible(False)
        self.val_detail_res = QLabel("-"); self.val_detail_res.setVisible(False)
        
        # Dummy hidden panels
        self.left_panel = QFrame(); self.left_panel.setVisible(False)
        self.left_presets_container = QWidget()
        self.left_presets_layout = QVBoxLayout(self.left_presets_container)
        self.right_panel = QFrame(); self.right_panel.setVisible(False)
        self.right_presets_container = QWidget()
        self.right_presets_layout = QVBoxLayout(self.right_presets_container)
        self.lbl_left_team = QLabel("")
        self.lbl_right_team = QLabel("")
        
        stack.addWidget(content_widget)
        
        # --- Layer 2: Overlay Controls ---
        overlay_widget = QWidget()
        overlay_widget.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(15, 15, 15, 15)
        
        # Top Bar
        top_bar = QHBoxLayout()
        
        # Button Style (More visible)
        btn_size = UIScaling.scale(55)
        btn_font = UIScaling.scale_font(28)
        btn_style = f"""
            QPushButton {{
                background-color: rgba(30, 30, 30, 0.6);
                color: white;
                border-radius: {btn_size//2}px;
                font-size: {btn_font}px;
                border: 2px solid rgba(255, 255, 255, 0.4);
            }}
            QPushButton:hover {{
                background-color: rgba(0, 122, 255, 0.8);
                border: 2px solid white;
            }}
        """
        
        btn_back = QPushButton("←")
        btn_back.setFixedSize(btn_size, btn_size)
        btn_back.setStyleSheet(btn_style)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setToolTip("Back to Menu")
        btn_back.clicked.connect(self.go_back)
        
        btn_settings = QPushButton("⚙️")
        btn_settings.setFixedSize(btn_size, btn_size)
        btn_settings.setStyleSheet(btn_style)
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.setToolTip("Open settings")
        btn_settings.clicked.connect(self.show_settings_menu)
        
        top_bar.addWidget(btn_back)
        top_bar.addStretch()
        
        # Model Selection Dropdown (overlay style)
        self.model_combo = QComboBox()
        self.model_combo.addItem("YOLO-Seg (AI - Recommended)", "yolo")
        self.model_combo.addItem("Standard (Beige Ready)", "standard")
        self.model_combo.addItem("FastSAM (AI)", "sam")
        self.model_combo.addItem("Advanced (YOLO-X + SAM)", "advanced")
        # Find index for current model
        idx = self.model_combo.findData(self.detection_model)
        if idx != -1: self.model_combo.setCurrentIndex(idx)
        
        self.model_combo.setMinimumWidth(UIScaling.scale(150))
        self.model_combo.setFixedHeight(btn_size)
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(30, 30, 30, 0.6);
                color: white;
                border-radius: {UIScaling.scale(8)}px;
                padding: 10px;
                font-size: {UIScaling.scale_font(16)}px;
                border: 2px solid rgba(255, 255, 255, 0.4);
                font-weight: bold;
            }}
            QComboBox::drop-down {{ border: 0; }}
            QComboBox QAbstractItemView {{
                background-color: #1C1C1E;
                color: white;
                selection-background-color: #007AFF;
            }}
        """)
        top_bar.addWidget(self.model_combo)
        top_bar.addSpacing(10)
        
        top_bar.addWidget(btn_settings)
        
        overlay_layout.addLayout(top_bar)
        overlay_layout.addStretch() # Push everything up
        
        stack.addWidget(overlay_widget)
        
        # --- Layer 3: Status Overlay (Loading/Error) ---
        self.status_overlay = QFrame()
        self.status_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        status_layout = QVBoxLayout(self.status_overlay)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {UIScaling.scale_font(24)}px;")
        status_layout.addWidget(self.status_label)
        self.status_overlay.hide()
        stack.addWidget(self.status_overlay)
        
        stack.setCurrentIndex(1) # CRITICAL: Put the overlay on top interaction-wise

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
        
        # Switch Button (Arrows) - REMOVED
        # self.btn_switch = QPushButton("⇄")
        # self.btn_switch.setFixedSize(ctrl_btn_size, ctrl_btn_size)
        # self.btn_switch.setStyleSheet(f"QPushButton {{ background: #E3F2FD; color: #1565C0; border-radius: {ctrl_btn_radius}px; font-size: {ctrl_btn_font_size}px; border: 1px solid #BBDEFB; }} QPushButton:hover {{ background: #BBDEFB; }}")
        # self.btn_switch.clicked.connect(self.on_switch_sides)
        
        # Settings
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(ctrl_btn_size, ctrl_btn_size)
        self.settings_btn.setStyleSheet(f"QPushButton {{ background: #F5F5F5; color: #333333; border-radius: {ctrl_btn_radius}px; font-size: {ctrl_btn_font_size}px; border: 1px solid #E0E0E0; }} QPushButton:hover {{ background: #E8E8E8; }}")
        self.settings_btn.clicked.connect(self.show_settings_menu)
        
        top_ctrl_layout.addWidget(self.back_button)
        top_ctrl_layout.addWidget(self.info_bar, 1) 
        
        # Model selection for standard layouts
        self.model_combo = QComboBox()
        self.model_combo.addItem("YOLO-Seg (AI)", "yolo")
        self.model_combo.addItem("Standard", "standard")
        self.model_combo.addItem("FastSAM", "sam")
        self.model_combo.addItem("Advanced (YOLO-X + SAM)", "advanced")
        self.model_combo.setFixedWidth(UIScaling.scale(120))
        self.model_combo.setFixedHeight(ctrl_btn_size)
        
        # Consistent styling for the combo box
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #F5F5F5;
                color: #333333;
                border: 1px solid #E0E0E0;
                border-radius: {info_bar_radius}px;
                padding: 1px 5px;
                font-size: {UIScaling.scale_font(13)}px;
                font-weight: bold;
            }}
            QComboBox::drop-down {{ border: 0; }}
        """)
        
        idx = self.model_combo.findData(self.detection_model)
        if idx != -1: self.model_combo.setCurrentIndex(idx)
        top_ctrl_layout.addWidget(self.model_combo)

        top_ctrl_layout.addWidget(btn_edit)
        # Switch button removed (Position is now explicit Left/Right)
        # top_ctrl_layout.addWidget(self.btn_switch)
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
        self.lbl_detail_oto = QLabel("Auto-Oto :")
        self.val_detail_oto = QLabel("-")
        self.lbl_detail_res = QLabel("Result :")
        self.val_detail_res = QLabel("-")
        
        detail_font_size = UIScaling.scale_font(18)
        label_style = f"font-weight: bold; color: #999999; font-size: {detail_font_size}px;"
        val_style = f"font-weight: bold; color: #333333; font-size: {detail_font_size}px;"
        
        for w in [self.lbl_detail_sku, self.lbl_detail_len, self.lbl_detail_wid, self.lbl_detail_oto, self.lbl_detail_res]: w.setStyleSheet(label_style)
        for w in [self.val_detail_sku, self.val_detail_len, self.val_detail_wid, self.val_detail_oto, self.val_detail_res]: 
            w.setAlignment(Qt.AlignRight)
            w.setStyleSheet(val_style)
            
        details_layout.addWidget(self.lbl_detail_sku, 0, 0); details_layout.addWidget(self.val_detail_sku, 0, 1)
        details_layout.addWidget(self.lbl_detail_len, 1, 0); details_layout.addWidget(self.val_detail_len, 1, 1)
        details_layout.addWidget(self.lbl_detail_wid, 2, 0); details_layout.addWidget(self.val_detail_wid, 2, 1)
        details_layout.addWidget(self.lbl_detail_oto, 3, 0); details_layout.addWidget(self.val_detail_oto, 3, 1)
        details_layout.addWidget(self.lbl_detail_res, 4, 0); details_layout.addWidget(self.val_detail_res, 4, 1)
        
        layout.addLayout(details_layout)
        
        # Add Status Label to preview background (overlay style)
        self.status_overlay = QFrame(self.preview_label)
        self.status_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.4); border-radius: 8px;")
        self.status_overlay.hide()
        stat_l = QVBoxLayout(self.status_overlay)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-weight: bold; font-size: 18px;")
        stat_l.addWidget(self.status_label)
        
        return panel
            
    def save_settings(self):
        # We should load existing settings first to not overwrite other fields
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        
        settings.update({
            "mm_per_px": self.mm_per_px,
            "camera_index": self.camera_index,
            "active_profile_id": self.active_profile_id,
            "ip_camera_username": getattr(self, "ip_camera_username", ""),
            "ip_camera_password": getattr(self, "ip_camera_password", ""),
            "detection_model": self.model_combo.currentData() if hasattr(self, 'model_combo') else self.detection_model
        })
        JsonUtility.save_to_json(SETTINGS_FILE, settings)



    def render_presets(self):
        # Debounce rapid re-render calls
        if self._render_debounce:
            return
        self._render_debounce = True
        QTimer.singleShot(50, self._do_render_presets)
    
    def _do_render_presets(self):
        self._render_debounce = False
        if self.layout_mode == "minimal":
            return # Minimal mode has no presets to render
            
        if self.layout_mode == "classic":
            # CLASSIC MODE: All presets in left panel, but split by Position
            # We treat Left as Top/First and Right as Bottom/Second
                
            self._clear_layout(self.classic_presets_layout)
            
            # Create a Horizontal Split within the Left Panel
            h_split_widget = QWidget()
            h_split = QHBoxLayout(h_split_widget)
            h_split.setContentsMargins(0, 0, 0, 0)
            h_split.setSpacing(10)
            
            # Left (Kiri) Container
            container_L = QWidget()
            layout_L = QVBoxLayout(container_L)
            layout_L.setContentsMargins(0, 0, 0, 0)
            
            # Right (Kanan) Container
            container_R = QWidget()
            layout_R = QVBoxLayout(container_R)
            layout_R.setContentsMargins(0, 0, 0, 0)
            
            # Filter Presets
            presets_L = []
            presets_R = []
            
            for p in self.presets:
                # Map Team to Position if needed
                pos = str(p.get("team", "")).lower().strip()
                sub = str(p.get("sub_label", "")).lower().strip()
                
                # Logic: Explicit Left/Right OR fallback A->Left, B->Right
                is_left = "left" in pos or "kiri" in pos or "team a" in pos or pos == "a"
                is_right = "right" in pos or "kanan" in pos or "team b" in pos or pos == "b"
                
                if is_left: presets_L.append(p)
                elif is_right: presets_R.append(p)
                else: presets_L.append(p) # Default to Left if undefined
            
            # Render to respective layouts
            self._render_presets_auto_fit(presets_L, layout_L)
            self._render_presets_auto_fit(presets_R, layout_R)
            
            # Add to Split Layout (50/50 split within the 55% panel)
            h_split.addWidget(container_L, 50)
            h_split.addWidget(container_R, 50)
            
            # Add Split Widget to Main Classic Layout
            self.classic_presets_layout.addWidget(h_split_widget)

        else:
            # SPLIT MODE: Left/Right Logic
            # Switch button is removed as per requirement
            
            if hasattr(self, 'btn_switch'): 
                self.btn_switch.setVisible(False)
                
            # Update Headers
            self.lbl_left_team.setText("Left (Kiri)")
            self.lbl_right_team.setText("Right (Kanan)")
            
            # Filter Presets
            presets_left = []
            presets_right = []
            
            for p in self.presets:
                # Map Team to Position if needed
                pos = str(p.get("team", "")).lower().strip()
                
                # Logic: Explicit Left/Right OR fallback A->Left, B->Right
                is_left = "left" in pos or "kiri" in pos or "team a" in pos or pos == "a"
                is_right = "right" in pos or "kanan" in pos or "team b" in pos or pos == "b"
                
                if is_left: presets_left.append(p)
                elif is_right: presets_right.append(p)
                else: presets_left.append(p) # Default to Left if undefined
                
            # Clear existing items
            self._clear_layout(self.left_presets_layout)
            self._clear_layout(self.right_presets_layout)
            
            # Render to layouts
            self._render_presets_auto_fit(presets_left, self.left_presets_layout)
            self._render_presets_auto_fit(presets_right, self.right_presets_layout)
        
    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    self._clear_layout(sub_layout)

    def _render_presets_auto_fit(self, presets, parent_layout):
        """
        Renders presets into parent_layout using a dynamic Auto-Fit approach.
        """
        if parent_layout is None:
            return
        
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
                display_size = str(size)
                
                color_idx = p.get("color_idx", 0)
                bg_color = SKU_COLORS.get(color_idx, "#E0E0E0")
                
                btn = QPushButton(display_size)
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
            
        # Add stretch at end to push everything up
        parent_layout.addStretch()

    def on_preset_clicked(self, idx):
        # Prevent double-click (300ms cooldown)
        if self._preset_click_guard:
            return
        self._preset_click_guard = True
        QTimer.singleShot(300, self._reset_preset_guard)
        
        if idx < 0 or idx >= len(self.presets):
            return
            
        p = self.presets[idx]
        self.current_sku = p.get("sku", "---")
        self.current_size = p.get("size", "---")
        self.current_otorisasi = float(p.get("otorisasi", 0) or 0)
        
        # Update UI
        self.val_detail_sku.setText(f"{self.current_sku}/{self.current_size}")
        if hasattr(self, 'val_detail_oto'):
            self.val_detail_oto.setText(f"{self.current_otorisasi:+.1f}")
        print(f"Selected Preset {idx}: {self.current_sku} / {self.current_size} (+{self.current_otorisasi})")
    
    def _reset_preset_guard(self):
        self._preset_click_guard = False

    def capture_frame(self):
        if self.live_frame is None:
            return
            
        # Show Loading Indicator
        self.show_status("Processing...", is_error=False)
        QApplication.processEvents() # Force UI update
        
        self.is_paused = True # Freeze preview
        
        # Determine model
        use_sam = False
        use_yolo = False
        use_advanced = False
        if hasattr(self, 'model_combo'):
            current_model = self.model_combo.currentData()
            use_yolo = (current_model == "yolo")
            use_sam = (current_model == "sam")
            use_advanced = (current_model == "advanced")
        else:
            use_yolo = (self.detection_model == "yolo")
            use_sam = (self.detection_model == "sam")
            use_advanced = (self.detection_model == "advanced")
            
        try:
            # Apply Height Correction (Parallax)
            # Formula: mm_px_corrected = mm_px * (H - T) / H
            h_cam = getattr(self, 'mounting_height', 1000.0)
            t_obj = getattr(self, 'sandal_thickness', 15.0)
            mm_px_corrected = self.mm_per_px * (h_cam - t_obj) / h_cam if h_cam > 0 else self.mm_per_px
            
            # Process with selected detection method
            results, processed = measure_live_sandals(
                self.live_frame.copy(),
                mm_per_px=mm_px_corrected,
                draw_output=True,
                save_out=None, # Optional: save to file
                use_sam=use_sam,
                use_yolo=use_yolo,
                use_advanced=use_advanced
            )
            
            self.captured_frame = processed
            
            # Display Results
            if results:
                self.hide_status()
                r = results[0]
                px_length = r.get("px_length", 0)
                px_width = r.get("px_width", 0)
                length_mm = r.get("real_length_mm", 0)
                width_mm = r.get("real_width_mm", 0) # Assumed exist
                # If not in dict, calc from cm
                if not width_mm: width_mm = r.get("real_width_cm", 0) * 10
                
                # Debug output for pixel measurements
                print(f"[CAPTURE] Pixel Length: {px_length:.2f} px | Pixel Width: {px_width:.2f} px")
                print(f"[CAPTURE] mm/px (Base): {self.mm_per_px:.6f} | mm/px (Corrected): {mm_px_corrected:.6f}")
                print(f"[CAPTURE] Real Length: {length_mm:.2f} mm | Real Width: {width_mm:.2f} mm")
                
                # --- Size-Based Categorization ---
                # Get current size and otorisasi from preset
                try:
                    selected_size = float(self.current_size) if self.current_size not in ["---", "-", ""] else 0
                except:
                    selected_size = 0
                otorisasi = getattr(self, 'current_otorisasi', 0.0) or 0.0
                
                if selected_size > 0:
                    cat_result = categorize_measurement(length_mm, selected_size, otorisasi)
                    category = cat_result["category"]
                    detail = cat_result["detail"]
                    deviation_mm = cat_result["deviation_mm"]
                    print(f"[CAPTURE] Size: {selected_size} | Otorisasi: {otorisasi} | Target: {cat_result['target_length_mm']} mm")
                    print(f"[CAPTURE] Deviation: {deviation_mm:.2f} mm ({cat_result['deviation_size']:.4f} size units) => {detail}")
                else:
                    # Logic Change: Force REJECT (BS) if no size selected
                    category = "REJECT"
                    detail = "No Size Selected"
                    print(f"[CAPTURE] No size selected, defaulting to REJECT/BS")
                
                self.val_detail_len.setText(f"{length_mm:.2f} mm")
                self.val_detail_wid.setText(f"{width_mm:.2f} mm")
                self.val_detail_res.setText(category)

                
                # BIG Style: White BG, Dark Text, Colored Background
                # Content: SIZE on top (Big), STATUS on bottom (Smaller)
                display_size = self.current_size if self.current_size != "---" else "-"
                
                res_font_size = UIScaling.scale_font(48)
                res_padding = UIScaling.scale(20)
                res_radius = UIScaling.scale(15)
                bg_color = get_category_color(category)
                
                if category == "GOOD":
                    self.good_count += 1
                    self.lbl_big_result.setText(f"{display_size}\nGOOD")
                    self.lbl_big_result.setStyleSheet(f"color: white; background-color: {bg_color}; padding: {res_padding}px; border-radius: {res_radius}px; border: none; font-size: {res_font_size}px; font-weight: 900;")
                    self._write_plc_result(is_good=True)
                elif category == "OVEN":
                    # OVEN counts as neither good nor reject for now
                    self.lbl_big_result.setText(f"{display_size}\nOVEN")
                    self.lbl_big_result.setStyleSheet(f"color: white; background-color: {bg_color}; padding: {res_padding}px; border-radius: {res_radius}px; border: none; font-size: {res_font_size}px; font-weight: 900;")
                    # TODO: Determine PLC behavior for OVEN
                else:  # REJECT
                    self.bs_count += 1
                    self.lbl_big_result.setText(f"{display_size}\nREJECT")
                    self.lbl_big_result.setStyleSheet(f"color: white; background-color: {bg_color}; padding: {res_padding}px; border-radius: {res_radius}px; border: none; font-size: {res_font_size}px; font-weight: 900;")
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
            
        except Exception as e:
            print(f"[Capture] Error: {e}")
            self.show_status(f"Error: {str(e)}", is_error=True)
            self.val_detail_res.setText("ERROR")
            self.lbl_big_result.setText("-\nERROR")
            self.lbl_big_result.setStyleSheet("color: white; background-color: #D32F2F; font-size: 48px; font-weight: 900; border-radius: 15px;")
        
        # Auto-resume after showing result (allows sensor to trigger again)
        QTimer.singleShot(1500, self.resume_live)  # Resume after 1.5 seconds

    def show_status(self, text, is_error=False):
        if not hasattr(self, 'status_label'): return
        self.status_label.setText(text)
        color = "rgba(211, 47, 47, 0.8)" if is_error else "rgba(0, 0, 0, 0.5)"
        self.status_overlay.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        
        # For non-minimal layouts, position it over preview
        if self.layout_mode != "minimal":
             self.status_overlay.setGeometry(self.preview_label.rect())
             
        self.status_overlay.show()
        self.status_overlay.raise_()

    def hide_status(self):
        if hasattr(self, 'status_overlay'):
            self.status_overlay.hide()

    def resume_live(self):
        self.hide_status()
        self.is_paused = False

    def create_settings_menu(self):
        """Placeholder for settings menu (now managed via General Settings page)."""
        pass

    def update_counters(self):
        self.lbl_good.setText(f"{self.good_count}\nGood")
        self.lbl_bs.setText(f"{self.bs_count}\nBS")

    # ------------------------------------------------------------------
    # Camera & Frame Handling
    # ------------------------------------------------------------------
    def on_frame_received(self, frame):
        """Called by VideoCaptureThread when a new frame is available"""
        self.live_frame = frame
        
        # Display live frame if not paused
        if not self.is_paused:
             self.show_image(frame)
        
        # ---------------------------------------------------------------------
        # Auto-Recalibration Logic
        # ---------------------------------------------------------------------
        self.frame_counter += 1
        if self.frame_counter % 10 == 0:  # Check every 10 frames
            self.check_auto_calibration(frame)

    def check_auto_calibration(self, frame):
        import time
        now = time.time()
        
        # Cooldown check
        if (now - self.last_autocalib_time) < self.autocalib_cooldown:
            return
            
        # Don't start if worker is busy
        if self.autocalib_worker is not None and self.autocalib_worker.isRunning():
            return
            
        marker_size = self.settings.get("aruco_marker_size", 50.0)
        print(f"[AutoCalib] Checking... (Size: {marker_size})") # Debug log
        
        # Run in background
        self.autocalib_worker = AutoCalibrationWorker(frame.copy(), marker_size)
        self.autocalib_worker.finished.connect(self.on_autocalib_finished)
        self.autocalib_worker.start()
        
    def on_autocalib_finished(self, result):
        if not result.get("success", False):
            return
            
        count = result.get("marker_count", 0)
        print(f"[AutoCalib] Found {count} markers") 

        # strict trigger: MUST be 8 markers
        if count != 8:
            return
            
        # Stability check
        if result.get("stability", 0) < 60.0 or result.get("is_tilted", False):
            print(f"[AutoCalib] looks tilted")
            return
            
        raw_mmpx = result.get("mm_per_px", 0)
        if raw_mmpx <= 0:
            print(f"[AutoCalib] raw mm/px less than 0")
            return

        # Parallax Correction
        cam_h = self.settings.get("mounting_height", 1000.0)
        obj_h = self.settings.get("sandal_thickness", 0.0)
        
        if cam_h > 0:
            effective_mmpx = raw_mmpx * ((cam_h - obj_h) / cam_h)
        else:
            effective_mmpx = raw_mmpx
            
        # Hysteresis (1% change threshold)
        current = self.mm_per_px or 1.0  # Avoid div/0
        diff_percent = abs(effective_mmpx - current) / current
        print(f"[AutoCalib] diff percent : {diff_percent}")
        
        if diff_percent > 0.01:
            import time
            print(f"[AutoCalib] Updated: Raw={raw_mmpx:.4f}, Eff={effective_mmpx:.4f} (Diff: {diff_percent:.2%})")
            self.mm_per_px = effective_mmpx
            self.last_autocalib_time = time.time()
            
            # Update settings in memory and persist
            self.settings["mm_per_px"] = effective_mmpx
            
            # Persist to disk
            try:
                # We need to construct the full dict to save, as self.settings might be incomplete or we want to be safe
                # But self.settings is loaded from JsonUtility, so it should be fine.
                JsonUtility.save_to_json(SETTINGS_FILE, self.settings)
            except Exception as e:
                print(f"[AutoCalib] Failed to save settings: {e}")
                
            # Show UI feedback
            self.show_autocalib_msg(f"Auto-Calibrated: {effective_mmpx:.4f} mm/px")

    def show_autocalib_msg(self, msg):
        print(f"[AutoCalib] SHOW MSG: {msg}")
        # Use show_status which uses the overlay widget
        self.show_status(msg, is_error=False)
        self.status_overlay.setStyleSheet("background-color: rgba(76, 175, 80, 0.9); color: white; border-radius: 8px; font-weight: bold; font-size: 24px; padding: 10px;")
        
        # Override the timer to hide it
        self.autocalib_msg_timer.start(4000) 
        
    def hide_autocalib_msg(self):
        self.autocalib_msg_timer.stop()
        self.hide_status()

    def show_image(self, frame):
        if frame is None: return
        
        # Convert to Pixmap
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        
        # Scale to label using KeepAspectRatio
        lbl_w = self.preview_label.width()
        lbl_h = self.preview_label.height()
        
        if lbl_w > 0 and lbl_h > 0:
            pix = pix.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
        self.preview_label.setPixmap(pix)
    
    def cv2_to_pixmap(self, img):
        if img is None: return QPixmap()
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def showEvent(self, event):
        # Reload Data when showing screen (e.g. returning from Settings Page)
        self.refresh_data()
        self.start_camera()
        super().showEvent(event)

    def _rebuild_ui(self):
        """Clear and rebuild the entire UI for a new layout mode."""
        # Clear existing layout
        if self.layout():
            old_layout = self.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
            QWidget().setLayout(old_layout)  # Remove old layout from self
        
        # Rebuild UI with new layout mode
        self.init_ui()
        
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
            
            
            # Start background capture with crop params
            self.cap_thread = VideoCaptureThread(source, is_ip, 
                                                 crop_params=self.camera_crop, 
                                                 distortion_params=self.lens_distortion, 
                                                 aspect_ratio_correction=getattr(self, 'aspect_ratio_correction', 1.0),
                                                 force_width=getattr(self, 'force_width', 0),
                                                 force_height=getattr(self, 'force_height', 0))
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
                print(f"[LiveCamera] Thread {self.cap_thread} is stuck. Detaching and abandoning...")
                try:
                    self.cap_thread.frame_ready.disconnect(self.on_frame_received)
                    self.cap_thread.connection_failed.disconnect(self.on_camera_connection_failed)
                except Exception:
                    pass
                    
                self.cap_thread.setParent(None)
                # CRITICAL FIX: Keep a reference to the thread so it's not garbage collected while running
                # If GC happens while the C++ thread is stuck in a syscall (like cv2.read), it causes SIGABRT.
                _zombie_threads.append(self.cap_thread)
            
            self.cap_thread = None
        
        self.stop_sensor()
        self.stop_plc_trigger()

    def go_back(self):
        self.stop_camera()
        if self.parent_widget:
            self.parent_widget.go_back()
            
    def toggle_layout_mode(self):
        new_mode = "classic" if self.layout_mode == "split" else "split"
        self.layout_mode = new_mode
        self.save_settings()
        self.reload_ui()

    def reload_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.init_ui()
        
    def on_mm_changed(self, text):
        try:
            val = float(text)
            self.mm_per_px = val
            self.save_settings()
        except ValueError:
            pass

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
