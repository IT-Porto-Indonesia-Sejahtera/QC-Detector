import os
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility

class SettingsOverlay(BaseOverlay):
    """Settings overlay for application configuration"""
    
    settings_saved = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        # Make content box larger for settings
        self.content_box.setFixedSize(900, 600)
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: 15px;
            }}
        """)
        
        self.load_settings()
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
                "paths": {
                    "profile": "C://User/test/asd/",
                    "settings": "C://User/test/asd/",
                    "db": "C://User/test/asd/",
                    "results": "C://User/test/asd/"
                }
            }
        
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        btn_back = QPushButton("❮")
        btn_back.setFixedSize(40, 40)
        btn_back.setStyleSheet(f"border: none; font-size: 24px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Settings")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {self.theme['text_main']};")
        
        btn_save = QPushButton("Save")
        btn_save.setFixedSize(120, 40)
        btn_save.setStyleSheet(f"""
            background-color: #F5F5F5;
            border-radius: 8px;
            font-weight: bold;
            color: #333333;
            font-size: 16px;
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
        preview_box = QFrame()
        preview_box.setFixedSize(450, 260)
        preview_box.setStyleSheet("background-color: #E0E0E0; border-radius: 10px;")
        preview_layout = QVBoxLayout(preview_box)
        preview_label = QLabel("Test Camera\nPreview")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #999999;")
        preview_layout.addWidget(preview_label)
        left_col.addWidget(preview_box)
        
        # Camera selector
        camera_row = QHBoxLayout()
        lbl_camera = QLabel("Camera")
        lbl_camera.setFixedWidth(80)
        lbl_camera.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 16px; font-weight: bold;")
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Camera 0", "Camera 1", "Camera 2"])
        self.camera_combo.setCurrentIndex(self.settings.get("camera_index", 0))
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
        
        camera_row.addWidget(lbl_camera)
        camera_row.addWidget(self.camera_combo)
        left_col.addLayout(camera_row)
        
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
    
    def save_settings_clicked(self):
        """Save settings to file"""
        self.settings["camera_index"] = self.camera_combo.currentIndex()
        self.settings["mm_per_px"] = float(self.mmpx_input.text())
        self.settings["sensor_delay"] = float(self.delay_input.text())
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
