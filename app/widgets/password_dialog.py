import hashlib
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager

class PasswordDialog(BaseOverlay):
    """Password overlay for profile operations"""
    
    authenticated = Signal()
    
    def __init__(self, parent=None, password_type="preset"):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        self.password_correct = False
        self.password_type = password_type  # "preset" or "settings"
        
        # Style content box
        self.content_box.setFixedSize(450, 280)
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: 15px;
            }}
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Enter Password")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {self.theme['text_main']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 12px;
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                font-size: 16px;
                background-color: white;
                color: #333333;
            }}
        """)
        self.password_input.returnPressed.connect(self.verify_password)
        layout.addWidget(self.password_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(48)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #333333;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
        """)
        btn_cancel.clicked.connect(self.cancel)
        
        btn_ok = QPushButton("OK")
        btn_ok.setFixedHeight(48)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_ok.clicked.connect(self.verify_password)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
        
        # Hint label - different for each type
        if self.password_type == "preset":
            hint = QLabel("Default password: admin")
        else:
            hint = QLabel("Default password: settings")
        hint.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: 14px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Focus on password input
        self.password_input.setFocus()
        
    def verify_password(self):
        """Verify the entered password against stored hash"""
        from project_utilities.json_utility import JsonUtility
        import os
        
        # Load password hashes from settings
        settings_file = os.path.join("output", "settings", "auth.json")
        settings = JsonUtility.load_from_json(settings_file)
        
        # Check if we need to migrate from old format or create new
        if not settings or "preset_hash" not in settings or "settings_hash" not in settings:
            # First time or old format - set default passwords
            preset_hash = hashlib.sha256("admin".encode()).hexdigest()
            settings_hash = hashlib.sha256("settings".encode()).hexdigest()
            settings = {
                "preset_hash": preset_hash,
                "settings_hash": settings_hash
            }
            JsonUtility.save_to_json(settings_file, settings)
        
        # Hash the entered password
        entered_password = self.password_input.text()
        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        
        # Get the correct hash for this password type
        hash_key = f"{self.password_type}_hash"
        stored_hash = settings.get(hash_key)
        
        # Compare hashes
        if entered_hash == stored_hash:
            self.password_correct = True
            self.authenticated.emit()
            self.close_overlay()
        else:
            QMessageBox.warning(self, "Error", "Incorrect password!")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def cancel(self):
        """User cancelled authentication"""
        self.password_correct = False
        self.close_overlay()
    
    @staticmethod
    def authenticate(parent=None, password_type="preset"):
        """Static method to show password overlay and return if authenticated"""
        overlay = PasswordDialog(parent, password_type)
        # Wait for overlay to close
        from PySide6.QtCore import QEventLoop
        loop = QEventLoop()
        overlay.authenticated.connect(loop.quit)
        overlay.destroyed.connect(loop.quit)
        loop.exec()
        return overlay.password_correct
