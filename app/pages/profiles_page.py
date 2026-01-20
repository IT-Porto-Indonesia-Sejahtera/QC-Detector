import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QImage, QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from app.widgets.sku_selector_overlay import SkuSelectorOverlay

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")
SETTINGS_FILE = os.path.join("output", "settings", "app_settings.json")

class ProfilesPage(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.profiles = []
        self.sku_rows = []
        self.current_editing = None
        
        self.init_ui()
        self.load_profiles()

    def init_ui(self):
        self.setStyleSheet("background-color: #F2F2F7;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(UIScaling.scale(80))
        header.setStyleSheet(f"background-color: {self.theme['bg_panel']}; border-bottom: 1px solid {self.theme['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_back = QPushButton("❮ Back")
        btn_back.setFixedHeight(UIScaling.scale(40))
        btn_back.setStyleSheet(f"border: none; font-size: {UIScaling.scale_font(16)}px; font-weight: bold; color: {self.theme['text_main']}; background: transparent;")
        btn_back.clicked.connect(self.go_back)
        
        lbl_title = QLabel("Preset Profiles Management")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: bold; color: {self.theme['text_main']};")
        
        header_layout.addWidget(btn_back)
        header_layout.addSpacing(20)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addWidget(header)
        
        # Content
        content = QWidget()
        c_layout = QHBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(20)
        
        # --- LEFT: List of Profiles ---
        left = QFrame()
        left.setObjectName("leftPanel")
        left.setFixedWidth(UIScaling.scale(300))
        left.setStyleSheet("""
            QFrame#leftPanel {
                background: white; 
                border-radius: 12px; 
                border: 1px solid #E0E0E0;
            }
            QLabel {
                border: none;
                background: transparent;
                padding: 10px;
                font-weight: bold;
                color: #007AFF;
                font-size: 11px;
            }
        """)
        l_layout = QVBoxLayout(left)
        l_layout.addWidget(QLabel("SAVED PROFILES"))
        
        self.profile_list = QScrollArea()
        self.profile_list.setWidgetResizable(True)
        self.profile_list.setFrameShape(QFrame.NoFrame)
        self.profile_list.setStyleSheet("background: transparent;")
        self.profile_content = QWidget()
        self.profile_content.setStyleSheet("background: transparent;")
        self.profile_layout = QVBoxLayout(self.profile_content)
        self.profile_layout.setSpacing(10)
        self.profile_list.setWidget(self.profile_content)
        l_layout.addWidget(self.profile_list)
        
        btn_add = QPushButton("+ New Profile")
        btn_add.setFixedHeight(UIScaling.scale(45))
        self.style_button(btn_add, primary=True)
        btn_add.clicked.connect(self.create_profile)
        l_layout.addWidget(btn_add)
        c_layout.addWidget(left)
        
        # --- RIGHT: Editor ---
        self.editor_area = QFrame()
        self.editor_area.setObjectName("editorArea")
        self.editor_area.setStyleSheet("""
            QFrame#editorArea {
                background: white; 
                border-radius: 12px; 
                border: 1px solid #E0E0E0;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        self.editor_layout = QVBoxLayout(self.editor_area)
        self.editor_layout.setContentsMargins(25, 25, 25, 25)
        
        self.lbl_editor_title = QLabel("Select a profile to edit")
        self.lbl_editor_title.setAlignment(Qt.AlignCenter)
        self.lbl_editor_title.setStyleSheet("color: #999999; font-size: 18px; font-weight: bold; border: none;")
        self.editor_layout.addWidget(self.lbl_editor_title)
        
        self.form_container = QWidget()
        self.form_container.setVisible(False)
        self.setup_form()
        self.editor_layout.addWidget(self.form_container)
        c_layout.addWidget(self.editor_area, 1)
        
        layout.addWidget(content)

    def setup_form(self):
        layout = QVBoxLayout(self.form_container)
        layout.setSpacing(15)
        
        h_row = QHBoxLayout()
        v_name = QVBoxLayout(); v_name.addWidget(QLabel("Profile Tag/Name"))
        self.name_input = QLineEdit(); self.style_input(self.name_input); v_name.addWidget(self.name_input)
        h_row.addLayout(v_name, 1)
        
        v_date = QVBoxLayout(); v_date.addWidget(QLabel("Date"))
        self.date_edit = QDateEdit(); self.date_edit.setDate(QDate.currentDate()); self.date_edit.setDisplayFormat("dd/MM/yyyy"); self.date_edit.setCalendarPopup(True); self.style_input(self.date_edit); v_date.addWidget(self.date_edit)
        h_row.addLayout(v_date)
        layout.addLayout(h_row)
        
        layout.addWidget(QLabel("SKU Configuration (Max 4 Groups)"))
        self.sku_rows_container = QVBoxLayout(); self.sku_rows_container.setSpacing(10)
        self.sku_rows = []
        for i in range(4):
            row_widget = self.create_sku_row(i)
            self.sku_rows_container.addWidget(row_widget)
        layout.addLayout(self.sku_rows_container)
        layout.addStretch()
        
        h_actions = QHBoxLayout()
        btn_del = QPushButton("Delete Profile")
        btn_del.setStyleSheet("background-color: #ffebee; color: #c62828; border-radius: 5px; padding: 10px; font-weight: bold;")
        btn_del.clicked.connect(self.delete_current_profile)
        
        btn_activate = QPushButton("Set as Active")
        self.style_button(btn_activate)
        btn_activate.clicked.connect(self.activate_current_profile)
        
        btn_save = QPushButton("Save Changes")
        self.style_button(btn_save, primary=True)
        btn_save.clicked.connect(self.save_current_profile)
        
        h_actions.addWidget(btn_del); h_actions.addWidget(btn_activate); h_actions.addStretch(); h_actions.addWidget(btn_save)
        layout.addLayout(h_actions)

    def create_sku_row(self, index):
        container = QFrame()
        container.setObjectName("skuRow")
        container.setStyleSheet(f"""
            QFrame#skuRow {{
                background-color: #F8F9FA; 
                border-radius: 12px;
                border: 1px solid #E9ECEF;
            }}
            QLabel {{
                border: none !important;
                background: transparent !important;
            }}
        """)
        container.setFixedHeight(UIScaling.scale(100))
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(15)
        
        indicator = QLabel(); indicator.setFixedSize(10, 80)
        colors = ["#2196F3", "#E91E63", "#9C27B0", "#FF9800"]
        indicator.setStyleSheet(f"background-color: {colors[index % len(colors)]}; border-radius: 5px;")
        layout.addWidget(indicator)
        
        v_sku = QVBoxLayout(); v_sku.setSpacing(5); v_sku.addWidget(QLabel("SKU", styleSheet="font-size: 10px; color: #888; font-weight: bold;"))
        txt_sku = QLineEdit(); txt_sku.setReadOnly(True); txt_sku.setPlaceholderText("None Selected"); txt_sku.setStyleSheet(f"background: transparent; border: none; font-weight: bold; font-size: {UIScaling.scale_font(16)}px; color: {self.theme['text_main']};")
        v_sku.addWidget(txt_sku); layout.addLayout(v_sku, 1)
        
        v_team = QVBoxLayout(); v_team.setSpacing(5); v_team.addWidget(QLabel("Team", styleSheet="font-size: 10px; color: #888; font-weight: bold;"))
        cmb_team = QComboBox(); cmb_team.addItems(["", "Team A", "Team B", "Team C", "Team D"]); self.style_input(cmb_team); cmb_team.setFixedWidth(UIScaling.scale(120))
        v_team.addWidget(cmb_team); layout.addLayout(v_team)
        
        btn_sel = QPushButton("Select SKU"); self.style_button(btn_sel); btn_sel.clicked.connect(lambda _, idx=index: self.select_sku(idx))
        layout.addWidget(btn_sel)
        
        self.sku_rows.append({"sku_val": txt_sku, "team_cmb": cmb_team, "data": None})
        return container

    def style_button(self, btn, primary=False):
        bg = "#007AFF" if primary else "#E8E8ED"
        fg = "white" if primary else "#007AFF"
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; 
                color: {fg}; 
                border-radius: 8px; 
                padding: 12px; 
                font-weight: bold; 
                font-size: {UIScaling.scale_font(14)}px; 
                border: none;
            }}
            QPushButton:hover {{
                background-color: {"#005BB5" if primary else "#D1D1D6"};
            }}
        """)

    def style_input(self, widget):
        # Use class-specific selector to prevent inheritance to child widgets/labels
        cls = widget.__class__.__name__
        widget.setStyleSheet(f"""
            {cls} {{
                border: 1px solid #D1D1D6; 
                border-radius: 8px; 
                padding: 10px; 
                background: white; 
                color: #1C1C1E;
                font-size: {UIScaling.scale_font(14)}px;
            }}
            {cls}:focus {{
                border: 2px solid #007AFF;
                padding: 9px;
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
        """)

    def load_profiles(self):
        self.profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        self.render_list()

    def render_list(self):
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for p in self.profiles:
            btn = QPushButton(f"{p.get('name', 'Shift')}\n{p.get('sub_label', '')}")
            btn.setStyleSheet(f"text-align: left; padding: 10px; background: white; border: 1px solid #E0E0E0; border-radius: 8px; color: {self.theme['text_main']}; font-weight: bold;")
            btn.clicked.connect(lambda _, p=p: self.load_editor(p))
            self.profile_layout.addWidget(btn)
        self.profile_layout.addStretch()

    def create_profile(self):
        new_p = {"id": str(uuid.uuid4()), "name": f"Shift {len(self.profiles)+1}", "sub_label": "Team A", "presets": []}
        self.profiles.append(new_p)
        JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        self.render_list()
        self.load_editor(new_p)

    def load_editor(self, profile):
        self.current_editing = profile
        self.lbl_editor_title.setVisible(False)
        self.form_container.setVisible(True)
        self.name_input.setText(profile.get("name", ""))
        date_str = profile.get("last_updated", "").split(",")[0].strip()
        try:
            d = QDate.fromString(date_str, "dd/MM/yyyy")
            if d.isValid(): self.date_edit.setDate(d)
        except: pass
        selected = profile.get("selected_skus", [])
        for i, row in enumerate(self.sku_rows):
            row["data"] = None; row["sku_val"].setText(""); row["team_cmb"].setCurrentIndex(0)
            if i < len(selected):
                row["data"] = selected[i]; row["sku_val"].setText(str(selected[i].get("code", ""))); row["team_cmb"].setCurrentText(selected[i].get("team", ""))

    def select_sku(self, index):
        self.pending_sku_index = index
        overlay = SkuSelectorOverlay(self.window())
        overlay.sku_selected.connect(self.on_sku_selected)

    def on_sku_selected(self, sku_data):
        row = self.sku_rows[self.pending_sku_index]
        row["data"] = sku_data
        row["sku_val"].setText(str(sku_data.get("code", "")))

    def save_current_profile(self):
        if not self.current_editing: return
        presets, selected_skus = [], []
        team_label, sku_label = "", ""
        for idx, row in enumerate(self.sku_rows):
            if row["data"]:
                data = row["data"].copy(); data["team"] = row["team_cmb"].currentText()
                selected_skus.append(data)
                code = data.get("code", "UNKNOWN")
                if not team_label: team_label = data["team"]
                if not sku_label: sku_label = code
                sizes = ["S", "M", "L", "XL"] if any(x in code.upper() for x in ["S","M","L","XL"]) else ["36","37","38","39","40","41","42","43","44"]
                for s in sizes: presets.append({"sku": code, "size": s, "color_idx": (idx%4)+1, "team": data["team"]})
        
        self.current_editing.update({
            "name": self.name_input.text(),
            "last_updated": f"{self.date_edit.date().toString('dd/MM/yyyy')}, {datetime.now().strftime('%H:%M:%S')}",
            "sub_label": team_label or "No Team",
            "sku_label": sku_label,
            "selected_skus": selected_skus,
            "presets": presets
        })
        JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        self.render_list()
        QMessageBox.information(self, "Success", "Profile saved!")
        
        # Navigate to Live Feed after save
        if self.controller:
            self.controller.go_to_live()

    def activate_current_profile(self):
        if not self.current_editing: return
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = self.current_editing["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)
        QMessageBox.information(self, "Active", f"'{self.current_editing['name']}' is now active.")
        
        # Navigate to Live Feed after activation
        if self.controller:
            self.controller.go_to_live()

    def delete_current_profile(self):
        if not self.current_editing: return
        if QMessageBox.question(self, "Delete", f"Delete '{self.current_editing['name']}'?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.profiles.remove(self.current_editing)
            JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
            self.render_list()
            self.form_container.setVisible(False); self.lbl_editor_title.setVisible(True); self.current_editing = None

    def go_back(self):
        if self.controller:
            self.controller.go_back()

    def refresh_data(self):
        self.load_profiles()
