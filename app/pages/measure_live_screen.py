
import cv2
import os
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QSizePolicy, QGridLayout, QMenu, QWidgetAction,
    QLineEdit, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, QTimer, QSize, QRect, Signal
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QAction, QDoubleValidator, QFont

import numpy as np
from model.measure_live_sandals import measure_live_sandals
from project_utilities.json_utility import JsonUtility
from app.widgets.preset_profile_overlay import PresetProfileOverlay, PROFILES_FILE
from app.utils.theme_manager import ThemeManager


# ---------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------
PRESETS_FILE = os.path.join("output", "settings", "presets.json")
SETTINGS_FILE = os.path.join("output", "settings", "settings.json")

# Default Presets (24 slots)
DEFAULT_PRESETS = [{"label": f"Slot {i+1}", "sku": "", "size": "", "color_idx": 0} for i in range(24)]

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
        
    def open_profile_dialog(self):
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
        # Optional: set panel bg if different
        # left_panel.setStyleSheet(f"background-color: {self.theme['bg_panel']};") # Added from instruction snippet
        
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
        btn_edit.setFixedSize(60, 35)
        btn_edit.setStyleSheet("background-color: #F5F5F5; border-radius: 5px; color: #333333; border: 1px solid #E0E0E0;")
        btn_edit.clicked.connect(self.open_profile_dialog)
        
        header_layout.addWidget(lbl_presets)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.info_bar, stretch=1)
        header_layout.addWidget(btn_edit)
        
        left_layout.addLayout(header_layout) # Fixed: use left_layout
        
        # Presets Grid (4 rows x 6 cols)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8) # Tighter spacing
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.render_presets()
        
        # Wrap Grid in a container that allows expansion
        grid_container = QWidget()
        grid_container.setLayout(self.grid_layout)
        grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        left_layout.addWidget(grid_container, stretch=1) # Fixed: use left_layout
        
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
        self.back_button.setFixedSize(35, 35) # compact
        self.back_button.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #333333; border-radius: 17px; font-size: 18px; border: 1px solid #E0E0E0;
            }
            QPushButton:hover { background: #E8E8E8; }
        """)
        self.back_button.clicked.connect(self.go_back)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(35, 35) # compact
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #333333; border-radius: 17px; font-size: 18px; border: 1px solid #E0E0E0;
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
            if len(loaded_presets) == 24:
                self.presets = loaded_presets
            else:
                self.presets = DEFAULT_PRESETS # Should we update the profile? Nah, leave it safe.
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
        # Clear
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        # Rebuild 6x4
        for i, p in enumerate(self.presets):
            row, col = divmod(i, 6) # 6 columns
            
            sku = p.get("sku", "")
            size = p.get("size", "")
            color_idx = p.get("color_idx", 0)
            bg_color = SKU_COLORS.get(color_idx, "#B0BEC5")
            
            btn = QPushButton()
            # Removed FixedSize to allow expansion
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumSize(80, 80) # Minimum reasonable size
            
            # Text
            text = f"{sku}\n{size}" if sku else "Empty"
            btn.setText(text)
            
            # Style
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: none;
                    border-radius: 12px;
                    color: #333333;
                    font-weight: bold;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    border: 3px solid #666666;
                }}
                QPushButton:pressed {{
                    opacity: 0.8;
                }}
            """)
            
            # Click Handler
            btn.clicked.connect(lambda _, idx=i: self.on_preset_clicked(idx))
            
            self.grid_layout.addWidget(btn, row, col)

    def on_preset_clicked(self, idx):
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
            else:
                self.bs_count += 1
                self.lbl_big_result.setText(f"{display_size}\nREJECT")
                self.lbl_big_result.setStyleSheet("color: white; background-color: #D32F2F; padding: 20px; border-radius: 15px; border: none; font-size: 48px; font-weight: 900;")
                
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
            self.cap = cv2.VideoCapture(self.camera_index)
        self.timer.start(30)
        self.is_paused = False
        
    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

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
        self.settings_menu.exec(self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomLeft()))
        
    def on_mm_changed(self, text):
        try:
            val = float(text)
            self.mm_per_px = val
            self.save_settings()
        except ValueError:
            pass

    def resume_live(self):
        self.is_paused = False

