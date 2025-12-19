
import cv2
import os
import datetime
import random
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
SETTINGS_FILE = os.path.join("output", "settings", "settings.json")

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

    {"sku": "E-9008L", "size": "38", "color_idx": 2},
    {"sku": "E-9008L", "size": "39", "color_idx": 2},
    {"sku": "E-9008L", "size": "40", "color_idx": 2},
    {"sku": "E-9008L", "size": "41", "color_idx": 2},

    {"sku": "X-5000-Pro", "size": "S", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "M", "color_idx": 3},
    {"sku": "X-5000-Pro", "size": "L", "color_idx": 3},

    {"sku": "A-1001X", "size": "38", "color_idx": 2},
    {"sku": "A-1001X", "size": "39", "color_idx": 2},
    {"sku": "A-1001X", "size": "40", "color_idx": 2},

    {"sku": "B-2020Y", "size": "S", "color_idx": 3},
    {"sku": "B-2020Y", "size": "M", "color_idx": 3},
    {"sku": "B-2020Y", "size": "L", "color_idx": 3},
    {"sku": "B-2020Y", "size": "XL", "color_idx": 3},

    {"sku": "C-3030Z", "size": "40", "color_idx": 4},
    {"sku": "C-3030Z", "size": "41", "color_idx": 4},
    {"sku": "C-3030Z", "size": "42", "color_idx": 4},
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
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
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
        
        # Main Layout: Left (Presets) vs Right (Preview/Stats)
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(10, 10, 10, 10)
        main_h_layout.setSpacing(10) # Changed from 20 to 10 based on instruction snippet
        self.setLayout(main_h_layout) # Moved from end of init_ui to here

        # -----------------------------------------------------
        # LEFT PANEL: Presets
        # -----------------------------------------------------
        left_panel = QFrame() # Changed from QVBoxLayout to QFrame based on instruction snippet
        left_layout = QVBoxLayout(left_panel) # Added from instruction snippet
        left_layout.setContentsMargins(0, 0, 0, 0) # Added from instruction snippet
        left_layout.setSpacing(10) # Added from instruction snippet
        
        # Header Row: "Presets" | Info Bar | Edit Button
        header_layout = QHBoxLayout()
        
        lbl_presets = QLabel("Presets")
        lbl_presets.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        # Info Bar (Shift 1, Team A...)
        self.info_bar = QLabel(" Loading... ")
        self.info_bar.setStyleSheet("""
            background-color: #F5F5F5; 
            color: #333333; 
            padding: 5px 15px; 
            border-radius: 5px; 
            font-weight: bold;
        """)
        self.info_bar.setFixedHeight(35)
        self.update_info_bar()
        
        btn_edit = QPushButton("Edit")
        btn_edit.setFixedSize(80, 50)
        btn_edit.setStyleSheet("background-color: #F5F5F5; border-radius: 5px; color: #333333; border: 1px solid #E0E0E0;")
        btn_edit.clicked.connect(self.open_profile_dialog)
        
        header_layout.addWidget(lbl_presets)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.info_bar, stretch=1)
        header_layout.addWidget(btn_edit)
        
        left_layout.addLayout(header_layout) # Fixed: use left_layout
        
        # --- SCROLL AREA FOR PRESETS ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        # Container for the content inside scroll area
        self.presets_container = QWidget()
        self.presets_container_layout = QVBoxLayout(self.presets_container)
        self.presets_container_layout.setSpacing(20) # Spacing between SKU groups
        self.presets_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area.setWidget(self.presets_container)
        
        # Enable Touch Scrolling (Kinetic)
        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        
        # Render the presets (Grouped by SKU)
        self.render_presets()
        
        left_layout.addWidget(self.scroll_area, stretch=1)
        
        # -------------------------------------------------------------
        # RIGHT PANEL: Preview & Stats
        # -------------------------------------------------------------
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10) # compacted
        
        # Top Controls: Back | Settings
        top_ctrl_layout = QHBoxLayout()
        
        self.back_button = QPushButton("←")
        self.back_button.setFixedSize(50, 50)
        self.back_button.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #333333; border-radius: 25px; font-size: 24px; border: 1px solid #E0E0E0;
            }
            QPushButton:hover { background: #E8E8E8; }
        """)
        self.back_button.clicked.connect(self.go_back)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(50, 50)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #333333; border-radius: 25px; font-size: 24px; border: 1px solid #E0E0E0;
            }
            QPushButton:hover { background: #E8E8E8; }
        """)
        self.settings_btn.clicked.connect(self.show_settings_menu)
        
        top_ctrl_layout.addWidget(self.back_button)
        top_ctrl_layout.addStretch()
        top_ctrl_layout.addWidget(self.settings_btn)
        
        right_layout.addLayout(top_ctrl_layout)
        
        # Review Frameshot
        self.preview_label = QLabel("Review\nFrameshot")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            background-color: #F8F8F8; 
            color: #AAAAAA; 
            border-radius: 8px;
            font-weight: bold;
            font-size: 60px;
            border: 3px solid #E0E0E0;
        """)
        # Make Preview smaller / fixed height
        self.preview_label.setFixedHeight(325) 
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        right_layout.addWidget(self.preview_label)
        
        # Counters: Good | BS
        counters_layout = QHBoxLayout()
        counters_layout.setSpacing(10)
        
        # Good Counter
        self.lbl_good = QLabel(f"{self.good_count}\nGood")
        self.lbl_good.setAlignment(Qt.AlignCenter)
        self.lbl_good.setMinimumHeight(100) # Increased height
        self.lbl_good.setStyleSheet("""
            background-color: #66BB6A; 
            color: white; 
            font-weight: bold; 
            font-size: 40px;
            border-radius: 5px;
            padding: 5px;
        """)
        
        # BS Counter
        self.lbl_bs = QLabel(f"{self.bs_count}\nBS")
        self.lbl_bs.setAlignment(Qt.AlignCenter)
        self.lbl_bs.setMinimumHeight(100) # Increased height
        self.lbl_bs.setStyleSheet("""
            background-color: #D32F2F; 
            color: white; 
            font-weight: bold; 
            font-size: 40px;
            border-radius: 5px;
            padding: 5px;
        """)
        
        counters_layout.addWidget(self.lbl_good)
        counters_layout.addWidget(self.lbl_bs)
        
        right_layout.addLayout(counters_layout)
        
        # Big Result (REJECT / ACCEPT)
        # Logic: Show SIZE (Big) \n STATUS (Small)
        self.lbl_big_result = QLabel("-\nIDLE")
        self.lbl_big_result.setAlignment(Qt.AlignCenter)
        self.lbl_big_result.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Fill space
        self.lbl_big_result.setStyleSheet("""
            color: #999999; 
            background-color: white; 
            font-size: 64px; 
            font-weight: 900; 
            padding: 10px; 
            border-radius: 15px; 
            border: 4px solid #E0E0E0;
        """)
        right_layout.addWidget(self.lbl_big_result, stretch=1) # Give it the stretch factor
        
        # Details Box
        details_layout = QGridLayout()
        details_layout.setVerticalSpacing(2) # tighter
        details_layout.setHorizontalSpacing(10)
        
        self.lbl_detail_sku = QLabel("SKU/Size :")
        self.val_detail_sku = QLabel("---/---")
        
        self.lbl_detail_len = QLabel("Length :")
        self.val_detail_len = QLabel("-")
        
        self.lbl_detail_wid = QLabel("Width :")
        self.val_detail_wid = QLabel("-")
        
        self.lbl_detail_res = QLabel("Result :")
        self.val_detail_res = QLabel("-")
        
        # Styling details - Updated for light theme
        label_style = "font-weight: bold; color: #999999; font-size: 24px;"
        val_style = "font-weight: bold; color: #333333; font-size: 24px;"

        for w in [self.lbl_detail_sku, self.lbl_detail_len, self.lbl_detail_wid, self.lbl_detail_res]:
            w.setStyleSheet(label_style)
            
        for w in [self.val_detail_sku, self.val_detail_len, self.val_detail_wid, self.val_detail_res]:
            w.setAlignment(Qt.AlignRight)
            w.setStyleSheet(val_style)

        details_layout.addWidget(self.lbl_detail_sku, 0, 0)
        details_layout.addWidget(self.val_detail_sku, 0, 1)
        details_layout.addWidget(self.lbl_detail_len, 1, 0)
        details_layout.addWidget(self.val_detail_len, 1, 1)
        details_layout.addWidget(self.lbl_detail_wid, 2, 0)
        details_layout.addWidget(self.val_detail_wid, 2, 1)
        details_layout.addWidget(self.lbl_detail_res, 3, 0)
        details_layout.addWidget(self.val_detail_res, 3, 1)
        
        right_layout.addLayout(details_layout)
        
        # Add layouts to main
        # Left Panel weight 65%, Right Panel weight 35%
        main_h_layout.addWidget(left_panel, 65)
        main_h_layout.addWidget(right_panel, 35)
        
        self.setLayout(main_h_layout)
        
        # Create Settings Menu (Hidden)
        self.create_settings_menu()

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
        settings = JsonUtility.load_from_json(SETTINGS_FILE)
        if settings:
            self.mm_per_px = settings.get("mm_per_px", 0.215984148)
            self.camera_index = settings.get("camera_index", 0)
            self.active_profile_id = settings.get("active_profile_id", None)
        else:
            self.mm_per_px = 0.215984148
            self.camera_index = 0
            self.active_profile_id = None
            
    def save_settings(self):
        data = {
            "mm_per_px": self.mm_per_px,
            "camera_index": self.camera_index,
            "active_profile_id": self.active_profile_id
        }
        JsonUtility.save_to_json(SETTINGS_FILE, data)

    def render_presets(self):
        # 1. Clear existing layout items
        # Recursively delete items if needed, or just clear widgets
        while self.presets_container_layout.count():
            item = self.presets_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            else:
                layout = item.layout()
                if layout:
                    # Recursively clear sub-layout if needed implementation
                    pass
        
        # 2. Group Presets by SKU
        # Use simple dict for grouping to maintain order of appearance if desired,
        # or just sort first. Let's group by appearance order.
        grouped = {}
        order = []
        
        for p in self.presets:
            sku = p.get("sku", "Unknown SKU")
            if not sku: sku = "Unknown SKU"
            
            if sku not in grouped:
                grouped[sku] = []
                order.append(sku)
            grouped[sku].append(p)
            
        # 3. Create Sections for each SKU
        for sku in order:
            items = grouped[sku]
            
            # -- SECTION HEADER --
            lbl_header = QLabel(sku)
            lbl_header.setStyleSheet("font-size: 24px; font-weight: bold; color: #333333; margin-top: 10px;")
            self.presets_container_layout.addWidget(lbl_header)
            
            # -- GRID FOR ITEMS --
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(10)
            grid.setContentsMargins(0, 0, 0, 0)
            
            # Populate Grid (5 columns max based on mockup)
            cols = 6
            grid.setAlignment(Qt.AlignLeft | Qt.AlignTop) # Align grid content to top-left
            
            for i, p in enumerate(items):
                row, col = divmod(i, cols)
                
                size = p.get("size", "??")
                color_idx = p.get("color_idx", 0)
                
                # Determine color
                bg_color = SKU_COLORS.get(color_idx, "#E0E0E0")
                
                btn = QPushButton(str(size))
                btn.setFixedSize(150, 190) # Fixed Size matching mockup roughly
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        border: none;
                        border-radius: 12px;
                        color: #000000;
                        font-weight: bold;
                        font-size: 32px;
                    }}
                    QPushButton:hover {{
                        border: 3px solid #666666;
                    }}
                    QPushButton:pressed {{
                        opacity: 0.8;
                    }}
                """)
                
                # Connect click
                # WARNING: Loop variable capture issue. Use default arg.
                try:
                    global_idx = self.presets.index(p)
                except ValueError:
                    global_idx = -1
                
                btn.clicked.connect(lambda _, idx=global_idx: self.on_preset_clicked(idx))
                
                grid.addWidget(btn, row, col)
            
            # Align items to left/top
            # If we have few items, they should stick to left.
            # QGridLayout puts them in 0,0 0,1 etc so they are left by default.
            
            self.presets_container_layout.addWidget(grid_widget)
            
        # Add stretch at bottom to push everything up
        self.presets_container_layout.addStretch()

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
            
            if pf == "PASS":
                self.good_count += 1
                self.lbl_big_result.setText(f"{display_size}\nGOOD")
                self.lbl_big_result.setStyleSheet("color: white; background-color: #4CAF50; padding: 20px; border-radius: 15px; border: none; font-size: 48px; font-weight: 900;")
                # Write random 1-4 to PLC register 13 for GOOD
                self._write_plc_result(is_good=True)
            else:
                self.bs_count += 1
                self.lbl_big_result.setText(f"{display_size}\nREJECT")
                self.lbl_big_result.setStyleSheet("color: white; background-color: #D32F2F; padding: 20px; border-radius: 15px; border: none; font-size: 48px; font-weight: 900;")
                # Write random 5-8 to PLC register 13 for BS
                self._write_plc_result(is_good=False)
                
            self.update_counters()
            
        else:
            self.val_detail_res.setText("-")
            self.val_detail_len.setText("-")
            self.val_detail_wid.setText("-")
            self.lbl_big_result.setText("-\nIDLE")
            # Idle: Grey text on white
            self.lbl_big_result.setStyleSheet("color: #999999; background-color: white; font-size: 48px; font-weight: 900; padding: 20px; border-radius: 15px; border: 4px solid #E0E0E0;")

            
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
    def update_frame(self):
        """
        Reads frame from camera but DOES NOT display it live.
        Only keeps self.live_frame fresh for capturing.
        """
        if not self.cap or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return
            
        self.live_frame = frame
        
        # REMOVED: Live feed display
        # if not self.is_paused:
        #    self.show_image(self.live_frame)

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
        pix = pix.scaled(lbl_w, lbl_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        if self.cap is None:
            # self.camera_index can be int or string (url)
            # cv2.VideoCapture handles both, but be sure it's correct type
            source = self.camera_index
            if isinstance(source, str):
                if source.isdigit():
                    source = int(source)
                # else: keep as string for URL
            
            try:
                # Use DirectShow backend on Windows for better compatibility
                if isinstance(source, int):
                    self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
                else:
                    self.cap = cv2.VideoCapture(source)
                
                # Set timeouts to avoid hanging
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
                    self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
                
                # Check if camera opened successfully
                if not self.cap or not self.cap.isOpened():
                    self.preview_label.setText("Camera not found.\nCheck Settings.")
                    self.preview_label.setStyleSheet("""
                        background-color: #FFEBEE; 
                        color: #C62828;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 24px;
                        border: 3px solid #E0E0E0;
                    """)
                    self.cap = None
                    return
                    
            except Exception as e:
                print(f"Error opening camera {source}: {e}")
                self.preview_label.setText(f"Camera Error:\n{str(e)[:50]}")
                self.preview_label.setStyleSheet("""
                    background-color: #FFEBEE; 
                    color: #C62828;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 18px;
                    border: 3px solid #E0E0E0;
                """)
                self.cap = None
                return
                
        self.timer.start(30)
        self.is_paused = False
        
        # Start sensor if available
        self.start_sensor()
        
        # Start PLC trigger if available
        self.start_plc_trigger()
        
    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        
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
        
        # Trigger Capture manually
        self.settings_menu.addAction("Refocus / Resume Live", self.resume_live)
        self.settings_menu.addAction("Capture Frame", self.capture_frame)
        
    def show_settings_menu(self):
        # Check settings password first
        from app.widgets.password_dialog import PasswordDialog
        
        if not PasswordDialog.authenticate(self, password_type="settings"):
            return  # Password incorrect or cancelled
        
        # Show settings overlay
        from app.widgets.settings_overlay import SettingsOverlay
        overlay = SettingsOverlay(self)
        overlay.settings_saved.connect(self.on_settings_saved)
    
    def on_settings_saved(self, settings):
        """Handle settings saved from overlay"""
        # Update local settings
        self.mm_per_px = settings.get("mm_per_px", self.mm_per_px)
        self.camera_index = settings.get("camera_index", self.camera_index)
        
        # Restart camera with new settings?
        self.stop_camera()
        self.start_camera()
        
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
            self.sensor.config.trigger_threshold_cm = 30.0  # Trigger at 30cm
            self.sensor.config.cooldown_seconds = 2.0  # 2 second cooldown
            
            # Set callbacks
            self.sensor.on_trigger = self.on_sensor_trigger
            self.sensor.on_connection_change = self.on_sensor_connection_change
            
            # Try to auto-connect
            if self.sensor.connect():
                self.sensor_enabled = True
                print("[Sensor] Connected and ready")
            else:
                print("[Sensor] Could not auto-connect - will retry on start_camera")
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
        """Start sensor reading"""
        if self.sensor and self.sensor_enabled:
            self.sensor.start()
    
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
        """Start PLC Modbus polling"""
        if self.plc_trigger and self.plc_enabled:
            print("[PLC] Starting Modbus polling...")
            self.plc_trigger.start()
    
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
        
        if is_good:
            value = random.randint(1, 4)
            print(f"[PLC] GOOD result - writing {value} to register 13")
        else:
            value = random.randint(5, 8)
            print(f"[PLC] BS result - writing {value} to register 13")
        
        self.plc_trigger.write_register(13, value)
        
        # Read back register 13 to verify
        read_value = self.plc_trigger.read_any_register(13)
        if read_value is not None:
            print(f"[PLC] Verified - Register 13 now contains: {read_value}")
        else:
            print(f"[PLC] Could not read back register 13 for verification")
