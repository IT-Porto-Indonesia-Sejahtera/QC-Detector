import hashlib
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling

class PasswordDialog(BaseOverlay):
    """Password overlay for profile operations"""
    
    authenticated = Signal()
    
    def __init__(self, parent=None, password_type="preset"):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        self.password_correct = False
        self.password_type = password_type  # "preset" or "settings"
        
        # Style content box
        scaled_w = UIScaling.scale(450)
        scaled_h = UIScaling.scale(280)
        
        # Ensure it doesn't exceed 90% of screen
        screen_size = UIScaling.get_screen_size()
        max_w = int(screen_size.width() * 0.9)
        max_h = int(screen_size.height() * 0.9)
        
        self.content_box.setMinimumSize(UIScaling.scale(300), UIScaling.scale(200))
        self.content_box.setMaximumSize(min(scaled_w, max_w), min(scaled_h, max_h))
        self.content_box.resize(min(scaled_w, max_w), min(scaled_h, max_h))

        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: {UIScaling.scale(15)}px;
            }}
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Masukan Password")
        title_font_size = UIScaling.scale_font(22)
        title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        input_padding = UIScaling.scale(12)
        input_font_size = UIScaling.scale_font(16)
        input_radius = UIScaling.scale(8)
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {input_padding}px;
                border: 1px solid {self.theme['border']};
                border-radius: {input_radius}px;
                font-size: {input_font_size}px;
                background-color: white;
                color: #333333;
            }}
        """)
        self.password_input.returnPressed.connect(self.verify_password)
        layout.addWidget(self.password_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_h = UIScaling.scale(48)
        btn_font_size = UIScaling.scale_font(16)
        btn_radius = UIScaling.scale(8)
        btn_padding_v = UIScaling.scale(12)
        btn_padding_h = UIScaling.scale(24)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(btn_h)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F5F5;
                color: #333333;
                border-radius: {btn_radius}px;
                padding: {btn_padding_v}px {btn_padding_h}px;
                font-weight: bold;
                font-size: {btn_font_size}px;
            }}
            QPushButton:hover {{
                background-color: #E8E8E8;
            }}
        """)
        btn_cancel.clicked.connect(self.cancel)
        
        btn_ok = QPushButton("OK")
        btn_ok.setFixedHeight(btn_h)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border-radius: {btn_radius}px;
                padding: {btn_padding_v}px {btn_padding_h}px;
                font-weight: bold;
                font-size: {btn_font_size}px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        btn_ok.clicked.connect(self.verify_password)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
        # Hint label removed as requested
        
        layout.addStretch()
        
        # Focus on password input
        self.password_input.setFocus()
        
    def verify_password(self):
        """Verify the entered password against stored hash in environment"""
        from app.utils.auth_utils import AuthUtils
        
        # Hash the entered password
        entered_password = self.password_input.text()
        
        # Get the correct hash for this password type
        if self.password_type == "preset":
            stored_hash = AuthUtils.get_admin_hash()
            default_password = "admin"
        else:
            stored_hash = AuthUtils.get_setting_hash()
            default_password = "settings"
        
        # Compare using AuthUtils
        # Fallback to local default if env hash is not set (during transition)
        if not stored_hash:
            import hashlib
            # Old logic fallback if .env is not yet configured with hashes
            entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
            # We still use the old "admin"/"settings" default if no hash in env
            expected_hash = hashlib.sha256(default_password.encode()).hexdigest()
            is_correct = (entered_hash == expected_hash)
        else:
            is_correct = AuthUtils.verify_password(entered_password, stored_hash)
        
        if is_correct:
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
