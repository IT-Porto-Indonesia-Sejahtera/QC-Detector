
import os
import datetime
import uuid
from app.widgets.profile_editor_dialog import ProfileEditorDialog
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from project_utilities.json_utility import JsonUtility

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")

class PresetProfileDialog(QDialog):
    # Signals
    profile_selected = Signal(dict) # Emits the full profile dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Preset Profile")
        self.setModal(True)
        self.resize(500, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
            }
        """)
        
        # Data
        self.profiles = []
        self.load_profiles()
        
        # UI
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back.setFixedSize(40, 40)
        btn_back.setStyleSheet("border: none; font-size: 24px; font-weight: bold;")
        btn_back.clicked.connect(self.reject)
        
        lbl_title = QLabel("Select Preset Profile")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title)
        header.addStretch() # spacer to balance back button if needed, or just let title center
        # To truly center title with a left button, we might need a dummy right button or just stretch
        header.addSpacing(40) 
        
        layout.addLayout(header)
        
        # Scroll Area for Profiles
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: white;")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        # Render Cards
        self.render_profiles()
        
        # Floating Add Button (Centered at bottom)
        btn_add = QPushButton("+")
        btn_add.setFixedSize(50, 50)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 25px;
                font-size: 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
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
                    "presets": [] # Empty presets or default
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
        # Clear existing (except stretch)
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            elif item.spacerItem():
                pass # keep stretch if at end? No, recreate it.
        
        # Remove stretch to add items, add it back later
        # Actually simpler: clear all, add items, add stretch
        
        # Re-clear strictly
        QWidget().setLayout(self.scroll_layout) # Nuke it
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(15)
        
        for p in self.profiles:
            card = self.create_profile_card(p)
            self.scroll_layout.addWidget(card)
            
        self.scroll_layout.addStretch()

    def create_profile_card(self, profile):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #E0E0E0;
                border-radius: 10px;
            }
        """)
        card.setFixedHeight(100) # Or wrap content
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(15, 10, 15, 10)
        
        # Clickable background to select
        # We can simulate this by making the whole frame clickable or event filter.
        # Simpler: Make a transparent button covering it? 
        # Or just use mousePressEvent on the custom frame class.
        # Let's use a specialized inner widget click handling or just helper.
        
        # Left Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name = QLabel(profile.get("name", "Unknown"))
        name.setStyleSheet("font-weight: bold; font-size: 16px; color: black;")
        
        sub = QLabel(profile.get("sub_label", ""))
        sub.setStyleSheet("color: black; font-size: 14px;") # Changed from #555
        
        sku = QLabel(profile.get("sku_label", ""))
        sku.setStyleSheet("color: black; font-size: 14px;") # Changed from #555
        
        info_layout.addWidget(name)
        info_layout.addWidget(sub)
        info_layout.addWidget(sku)
        
        # Right Info & Actions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        updated_lbl = QLabel("Last Updated :")
        updated_lbl.setStyleSheet("font-weight: bold; color: black; font-size: 12px;")
        updated_val = QLabel(profile.get("last_updated", ""))
        updated_val.setStyleSheet("color: black; font-size: 12px;")
        
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        btn_edit = QPushButton("✏️") # Edit Icon
        btn_edit.setFixedSize(30, 30)
        btn_edit.setStyleSheet("border: none; font-size: 16px;")
        btn_edit.clicked.connect(lambda _, p=profile: self.edit_profile(p))
        
        btn_del = QPushButton("🗑️") # Delete Icon
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet("border: none; font-size: 16px;")
        btn_del.clicked.connect(lambda _, p=profile: self.delete_profile(p))
        
        actions_layout.addWidget(btn_edit)
        actions_layout.addWidget(btn_del)
        
        right_layout.addWidget(updated_lbl, alignment=Qt.AlignRight)
        right_layout.addWidget(updated_val, alignment=Qt.AlignRight)
        right_layout.addLayout(actions_layout)
        
        # Combine
        card_layout.addLayout(info_layout, stretch=1)
        card_layout.addLayout(right_layout)
        
        # Making the card clickable for selection (ignoring button clicks)
        # We'll attach a mousePressEvent to the card frame
        # Need to capture closure
        original_mousePass = card.mousePressEvent
        def on_card_click(event):
            self.on_profile_clicked(profile)
            if original_mousePass: original_mousePass(event)
            
        card.mousePressEvent = on_card_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card

    def on_profile_clicked(self, profile):
        self.profile_selected.emit(profile)
        self.accept()

    def add_profile(self):
        # Open Editor with new profile skeleton
        new_p = {
            "id": str(uuid.uuid4()),
            "presets": [] # Empty presets
            # Name/Date etc filled by editor
        }
        
        # Default tag suggestion
        idx = len(self.profiles) + 1
        new_p["name"] = f"Shift {idx}"
        
        dlg = ProfileEditorDialog(self, new_p)
        if dlg.exec():
            result = dlg.get_data()
            self.profiles.append(result)
            self.save_profiles()
            self.render_profiles()

    def edit_profile(self, profile):
        dlg = ProfileEditorDialog(self, profile)
        if dlg.exec():
            updated = dlg.get_data()
            # Update list
            for i, p in enumerate(self.profiles):
                if p["id"] == updated["id"]:
                    self.profiles[i] = updated
                    break
            self.save_profiles()
            self.render_profiles()

    def delete_profile(self, profile):
        # Confirm?
        # For now direct delete as requested in previous turn logic
        self.profiles = [p for p in self.profiles if p['id'] != profile['id']]
        self.save_profiles()
        self.render_profiles()

