
import os
import datetime
import uuid
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from project_utilities.json_utility import JsonUtility
from app.widgets.base_overlay import BaseOverlay

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")

from app.utils.theme_manager import ThemeManager

class PresetProfileOverlay(BaseOverlay):
    # Signals
    profile_selected = Signal(dict) # Emits the full profile dict
    finished = Signal() # Emits when closed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        # Style Content Box
        self.content_box.setFixedSize(500, 600)
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: 15px;
            }}
        """)
        
        # Data
        self.profiles = []
        self.load_profiles()
        
        # UI
        self.init_ui()

    def init_ui(self):
        # Use content_layout from BaseOverlay
        layout = self.content_layout
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back.setFixedSize(40, 40)
        btn_back.setStyleSheet(f"border: none; font-size: 24px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Select Preset Profile")
        lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.theme['text_main']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title)
        header.addSpacing(40) 
        
        layout.addLayout(header)
        
        # Scroll Area for Profiles
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"border: none; background: {self.theme['bg_panel']};")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        # Render Cards
        self.render_profiles()
        
        # Floating Add Button
        btn_add = QPushButton("+")
        btn_add.setFixedSize(50, 50)
        # Use inverse colors for floating button? Or standard?
        # Let's keep black/white contrast or theme inverse.
        # If dark mode, maybe White button with Black text? 
        # For now, let's stick to "black" button in light, "white" in dark?
        # Actually ThemeManager has btn_bg.
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border-radius: 25px;
                font-size: 30px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        btn_add.clicked.connect(self.add_profile)
        
        # Center the add button
        add_container = QHBoxLayout()
        add_container.addStretch()
        add_container.addWidget(btn_add)
        add_container.addStretch()
        
        layout.addLayout(add_container)

    def load_profiles(self):
        loaded = JsonUtility.load_from_json(PROFILES_FILE)
        if loaded:
            self.profiles = loaded
        else:
            # Seed default if empty
            self.profiles = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Shift 1",
                    "sub_label": "Team A",
                    "sku_label": "SKU E 9008 M",
                    "last_updated": datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
                    "presets": []
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Shift 2",
                    "sub_label": "Team B",
                    "sku_label": "SKU E 9008 L",
                    "last_updated": datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
                    "presets": [] 
                }
            ]
            self.save_profiles()

    def save_profiles(self):
        JsonUtility.save_to_json(PROFILES_FILE, self.profiles)

    def render_profiles(self):
        # Clear existing
        QWidget().setLayout(self.scroll_layout) # Nuke it
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(15)
        
        for p in self.profiles:
            card = self.create_profile_card(p)
            self.scroll_layout.addWidget(card)
            
        self.scroll_layout.addStretch()

    def create_profile_card(self, profile):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_card']};
                border-radius: 10px;
            }}
        """)
        card.setFixedHeight(100)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(15, 10, 15, 10)
        
        # Left Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name = QLabel(profile.get("name", "Unknown"))
        name.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {self.theme['text_main']};")
        
        sub = QLabel(profile.get("sub_label", ""))
        sub.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14px;")
        
        sku = QLabel(profile.get("sku_label", ""))
        sku.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14px;")
        
        info_layout.addWidget(name)
        info_layout.addWidget(sub)
        info_layout.addWidget(sku)
        
        # Right Info & Actions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        updated_lbl = QLabel("Last Updated :")
        updated_lbl.setStyleSheet(f"font-weight: bold; color: {self.theme['text_main']}; font-size: 12px;")
        updated_val = QLabel(profile.get("last_updated", ""))
        updated_val.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 12px;")
        
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(30, 30)
        btn_edit.setStyleSheet(f"border: none; font-size: 16px; color: {self.theme['text_main']};")
        btn_edit.clicked.connect(lambda _, p=profile: self.edit_profile(p))
        
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet(f"border: none; font-size: 16px; color: {self.theme['text_main']};")
        btn_del.clicked.connect(lambda _, p=profile: self.delete_profile(p))
        
        actions_layout.addWidget(btn_edit)
        actions_layout.addWidget(btn_del)
        
        right_layout.addWidget(updated_lbl, alignment=Qt.AlignRight)
        right_layout.addWidget(updated_val, alignment=Qt.AlignRight)
        right_layout.addLayout(actions_layout)
        
        card_layout.addLayout(info_layout, stretch=1)
        card_layout.addLayout(right_layout)
        
        # Click handling
        original_mousePass = card.mousePressEvent
        def on_card_click(event):
            self.on_profile_clicked(profile)
            if original_mousePass: original_mousePass(event)
            
        card.mousePressEvent = on_card_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card

    def on_profile_clicked(self, profile):
        self.profile_selected.emit(profile)
        self.close_overlay()

    def add_profile(self):
        new_p = {
            "id": str(uuid.uuid4()),
            "presets": []
        }
        idx = len(self.profiles) + 1
        new_p["name"] = f"Shift {idx}"
        
        # Import internally (or pass Main controller)
        from app.widgets.profile_editor_overlay import ProfileEditorOverlay
        
        # We need to overlay ON TOP of this overlay? or on parent?
        # If we act like pages, we might want to hide this one or stack.
        # Simplest: Parent new overlay to the SAME parent (LiveScreen)
        overlay = ProfileEditorOverlay(self.parent(), new_p)
        overlay.data_saved.connect(self.on_editor_saved)
        # We don't need to hide this one necessarily, but user expects flow.
        # Since overlay has transparent BG, stacking them darkens background more.
        # Maybe hide "content_box" or just accept stack.
        
    def edit_profile(self, profile):
        from app.widgets.profile_editor_overlay import ProfileEditorOverlay
        overlay = ProfileEditorOverlay(self.parent(), profile)
        overlay.data_saved.connect(self.on_editor_saved)

    def on_editor_saved(self, profile_data):
        # Check if update or add
        exists = False
        for i, p in enumerate(self.profiles):
            if p["id"] == profile_data["id"]:
                self.profiles[i] = profile_data
                exists = True
                break
        
        if not exists:
            self.profiles.append(profile_data)
            
        self.save_profiles()
        self.render_profiles()

    def delete_profile(self, profile):
        self.profiles = [p for p in self.profiles if p['id'] != profile['id']]
        self.save_profiles()
        self.render_profiles()
    
    def close_overlay(self):
        self.finished.emit()
        super().close_overlay()
