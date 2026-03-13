from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Qt
from app.utils.ui_scaling import UIScaling

import os
from project_utilities.json_utility import JsonUtility

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")


class MenuScreen(QWidget):
    def __init__(self, controller):
        super().__init__(controller)
        self.parent = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title_font_size = UIScaling.scale_font(28)
        title = QLabel("Sistem Deteksi Sandal QC")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; margin-bottom: 30px; color: #1C1C1E;")

        layout.addStretch(1)
        layout.addWidget(title)
        
        btn_font_size = UIScaling.scale_font(18)
        btn_min_w = UIScaling.scale(350)
        btn_min_h = UIScaling.scale(70)
        
        # Primary Action: RUN
        run_btn = QPushButton("▶  Mulai QC")
        run_btn.setMinimumSize(btn_min_w, btn_min_h)
        run_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {btn_font_size}px; 
                background-color: #007AFF; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #005BB5;
            }}
        """)
        run_btn.setCursor(Qt.PointingHandCursor)
        run_btn.clicked.connect(self.start_detection)
        
        # Combined: PRESETS & REPORT
        presets_btn = QPushButton("📋  Kelola Preset dan Laporan")
        presets_btn.setMinimumSize(btn_min_w, btn_min_h)
        presets_btn.setStyleSheet(self.secondary_button_style(btn_font_size))
        presets_btn.setCursor(Qt.PointingHandCursor)
        presets_btn.clicked.connect(self.go_to_presets)

        # Secondary Action: SETTINGS
        settings_btn = QPushButton("⚙️  Pengaturan Sistem")
        settings_btn.setMinimumSize(btn_min_w, btn_min_h)
        settings_btn.setStyleSheet(self.secondary_button_style(btn_font_size))
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self.go_to_settings)

        layout.addWidget(run_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(UIScaling.scale(15))
        layout.addWidget(presets_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(UIScaling.scale(15))
        layout.addWidget(settings_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.setLayout(layout)

    def secondary_button_style(self, font_size):
        return f"""
            QPushButton {{
                font-size: {font_size}px; 
                background-color: #E8E8ED; 
                color: #007AFF; 
                border-radius: 12px; 
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #D1D1D6;
            }}
        """

    def start_detection(self):
        """Check if there's an on_process preset before starting detection."""
        try:
            profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except Exception:
            profiles = []

        # Find on_process preset
        on_process = None
        for p in profiles:
            if p.get("status") in ("on_process", "active"):
                on_process = p
                break

        if on_process:
            # There's an active preset — go directly to live
            self.parent.go_to_live()
        else:
            # No on_process preset — show popup
            msg = QMessageBox(self)
            msg.setWindowTitle("Tidak Ada Preset Aktif")
            msg.setText("Tidak ada preset yang sedang berjalan.\nPilih dan mulai preset terlebih dahulu.")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.button(QMessageBox.Ok).setText("Buka Preset")
            msg.button(QMessageBox.Cancel).setText("Batal")
            msg.setStyleSheet("""
                QMessageBox { background-color: white; }
                QMessageBox QLabel { color: #333; font-size: 15px; padding: 12px; }
                QPushButton {
                    background-color: #F3F4F6; color: #333;
                    border: 1px solid #D1D5DB; border-radius: 8px;
                    padding: 8px 24px; font-size: 14px; margin: 5px; font-weight: 600;
                }
                QPushButton:hover { background-color: #E5E7EB; }
            """)
            if msg.exec() == QMessageBox.Ok:
                self.go_to_presets()

    def go_to_presets(self):
        from app.widgets.password_dialog import PasswordDialog
        if PasswordDialog.authenticate(self, password_type="preset"):
            self.parent.go_to_profiles()

    def go_to_settings(self):
        from app.widgets.password_dialog import PasswordDialog
        if PasswordDialog.authenticate(self, password_type="settings"):
            self.parent.go_to_settings()
