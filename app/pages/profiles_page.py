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
from backend.get_product_sku import ProductSKUWorker
from backend.sku_cache import set_sku_data, add_log

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
        self.setStyleSheet("background-color: #F8F9FA; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- HEADER ---
        header = QFrame()
        header.setFixedHeight(UIScaling.scale(80))
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #E0E0E0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_back = QPushButton("❮ Back")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("border: none; font-size: 16px; font-weight: 600; color: #333;")
        btn_back.clicked.connect(self.go_back)
        
        lbl_title = QLabel("Manage Presets")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #1C1C1E; margin-left: 10px;")
        
        header_layout.addWidget(btn_back)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        # Sync Button
        self.btn_sync = QPushButton("🔄 Sync SKU")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #007AFF;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                color: #007AFF;
            }
            QPushButton:hover {
                background-color: #F0F8FF;
            }
        """)
        self.btn_sync.clicked.connect(self.fetch_sku_data)
        header_layout.addWidget(self.btn_sync)
        
        layout.addWidget(header)
        
        # --- MAIN CONTENT ---
        content = QWidget()
        c_layout = QHBoxLayout(content)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(30)
        
        # --- LEFT PANEL: Profile List ---
        left_panel = QFrame()
        left_panel.setFixedWidth(UIScaling.scale(320))
        left_panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        l_layout = QVBoxLayout(left_panel)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(0)
        
        # Panel Header
        lbl_list_header = QLabel("SAVED PROFILES")
        lbl_list_header.setFixedHeight(50)
        lbl_list_header.setStyleSheet("padding-left: 20px; font-size: 12px; font-weight: 700; color: #8E8E93; border-bottom: 1px solid #F0F0F0;")
        l_layout.addWidget(lbl_list_header)
        
        # Scroll Area
        self.profile_list = QScrollArea()
        self.profile_list.setWidgetResizable(True)
        self.profile_list.setFrameShape(QFrame.NoFrame)
        self.profile_list.setStyleSheet("background: transparent; border: none;")
        
        self.profile_content = QWidget()
        self.profile_content.setStyleSheet("background: transparent;")
        self.profile_layout = QVBoxLayout(self.profile_content)
        self.profile_layout.setContentsMargins(10, 10, 10, 10)
        self.profile_layout.setSpacing(10)
        self.profile_layout.addStretch() # Push items to top
        
        self.profile_list.setWidget(self.profile_content)
        l_layout.addWidget(self.profile_list)
        
        # Footer Action
        btn_add = QPushButton("+ Create New Profile")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(50)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                font-weight: 600;
                font-size: 15px;
                border: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
            QPushButton:hover {
                background-color: #005BB5;
            }
        """)
        btn_add.clicked.connect(self.create_profile)
        l_layout.addWidget(btn_add)
        
        c_layout.addWidget(left_panel)
        
        # --- RIGHT PANEL: Editor ---
        self.editor_area = QFrame()
        self.editor_area.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        self.editor_layout = QVBoxLayout(self.editor_area)
        self.editor_layout.setContentsMargins(40, 40, 40, 40)
        
        # Placeholder State
        self.lbl_editor_title = QLabel("Select a profile to edit")
        self.lbl_editor_title.setAlignment(Qt.AlignCenter)
        self.lbl_editor_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #8E8E93; border: none;")
        self.editor_layout.addWidget(self.lbl_editor_title)
        
        # Form Container
        self.form_container = QWidget()
        self.form_container.setVisible(False)
        self.setup_form()
        self.editor_layout.addWidget(self.form_container)
        
        c_layout.addWidget(self.editor_area, 1)
        
        layout.addWidget(content)

    def setup_form(self):
        layout = QVBoxLayout(self.form_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(25)
        
        # Header Row: Name & Date
        h_row = QHBoxLayout()
        h_row.setSpacing(20)
        
        v_name = QVBoxLayout()
        v_name.setSpacing(8)
        v_name.addWidget(QLabel("Profile Name / Shift", styleSheet="font-weight: 600; color: #333; font-size: 13px; border:none;"))
        self.name_input = QLineEdit()
        self.style_input(self.name_input)
        v_name.addWidget(self.name_input)
        h_row.addLayout(v_name, 2)
        
        v_date = QVBoxLayout()
        v_date.setSpacing(8)
        v_date.addWidget(QLabel("Date", styleSheet="font-weight: 600; color: #333; font-size: 13px; border:none;"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setCalendarPopup(True)
        self.style_input(self.date_edit)
        v_date.addWidget(self.date_edit)
        h_row.addLayout(v_date, 1)
        
        layout.addLayout(h_row)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E0E0E0; border: none; background-color: #E0E0E0; max-height: 1px;")
        layout.addWidget(line)
        
        # SKU Configuration
        layout.addWidget(QLabel("SKU Configuration", styleSheet="font-size: 16px; font-weight: 700; color: #1C1C1E; border:none; margin-bottom: 5px;"))
        
        self.sku_rows_container = QVBoxLayout()
        self.sku_rows_container.setSpacing(15)
        self.sku_rows = []
        
        # Create 4 slots
        for i in range(4):
            row_widget = self.create_sku_row(i)
            self.sku_rows_container.addWidget(row_widget)
        layout.addLayout(self.sku_rows_container)
        
        layout.addStretch()
        
        # Actions Footer
        h_actions = QHBoxLayout()
        h_actions.setSpacing(15)
        
        btn_del = QPushButton("Delete Profile")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                color: #D32F2F;
                border: 1px solid #FFCDD2;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        btn_del.clicked.connect(self.delete_current_profile)
        
        btn_activate = QPushButton("Set as Active")
        btn_activate.setCursor(Qt.PointingHandCursor)
        btn_activate.setStyleSheet("""
            QPushButton {
                background-color: #E8EAF6;
                color: #3F51B5;
                border: 1px solid #C5CAE9;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #C5CAE9;
            }
        """)
        btn_activate.clicked.connect(self.activate_current_profile)
        
        btn_save = QPushButton("Save Changes")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 25px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #005BB5;
            }
        """)
        btn_save.clicked.connect(self.save_current_profile)
        
        h_actions.addWidget(btn_del)
        h_actions.addWidget(btn_activate)
        h_actions.addStretch()
        h_actions.addWidget(btn_save)
        
        layout.addLayout(h_actions)

    def create_sku_row(self, index):
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #EEEEEE;
                border-radius: 10px;
            }
        """)
        container.setFixedHeight(90)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # Color Indicator
        colors = ["#2196F3", "#E91E63", "#9C27B0", "#FF9800"]
        indicator = QLabel()
        indicator.setFixedSize(6, 60)
        indicator.setStyleSheet(f"background-color: {colors[index % len(colors)]}; border-radius: 3px; border:none;")
        layout.addWidget(indicator)
        
        # SKU Display (ReadOnly)
        v_sku = QVBoxLayout()
        v_sku.setSpacing(4)
        v_sku.addWidget(QLabel(f"Group {index + 1}", styleSheet="font-size: 11px; font-weight: 700; color: #8E8E93; border:none;"))
        txt_sku = QLineEdit()
        txt_sku.setReadOnly(True)
        txt_sku.setPlaceholderText("No SKU Selected")
        txt_sku.setStyleSheet("background: transparent; border: none; font-size: 16px; font-weight: 600; color: #1C1C1E;")
        v_sku.addWidget(txt_sku)
        layout.addLayout(v_sku, 1)
        
        # Team Selector
        v_team = QVBoxLayout()
        v_team.setSpacing(4)
        v_team.addWidget(QLabel("Team Assignment", styleSheet="font-size: 11px; font-weight: 700; color: #8E8E93; border:none;"))
        cmb_team = QComboBox()
        # Dropdown UI is now handled globally, just set content
        cmb_team.addItems(["", "Team A", "Team B", "Team C", "Team D"])
        cmb_team.setFixedWidth(140)
        v_team.addWidget(cmb_team)
        layout.addLayout(v_team)
        
        # Select Button
        btn_sel = QPushButton("Select SKU")
        btn_sel.setCursor(Qt.PointingHandCursor)
        btn_sel.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #D1D1D6;
                color: #1C1C1E;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F2F2F7;
                border-color: #8E8E93;
            }
        """)
        btn_sel.clicked.connect(lambda _, idx=index: self.select_sku(idx))
        layout.addWidget(btn_sel)
        
        self.sku_rows.append({"sku_val": txt_sku, "team_cmb": cmb_team, "data": None})
        return container

    def style_input(self, widget):
        widget.setStyleSheet("""
            QLineEdit, QDateEdit {
                border: 1px solid #D1D1D6;
                border-radius: 8px;
                padding: 8px 10px;
                background: white;
                color: #1C1C1E;
                font-size: 14px;
            }
            QLineEdit:focus, QDateEdit:focus {
                border: 1px solid #007AFF;
            }
        """)

    def load_profiles(self):
        self.profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        self.render_list()

    def render_list(self):
        # Clear list
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
                
        # Re-populate
        # self.profile_layout.addStretch() is removed from here because we add it once in init, 
        # but we need to ensure items are added BEFORE the stretch.
        # Actually simplest way: remove everything including stretch, add items, then add stretch.
        
        # Since we just cleared everything:
        for p in self.profiles:
            is_selected = (self.current_editing == p)
            
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(is_selected)
            btn.setFixedHeight(70)
            btn.setCursor(Qt.PointingHandCursor)
            
            # Subtitle (Team/Date)
            sub_text = p.get('sub_label', '')
            name_text = p.get('name', 'Untitled')
            
            # Using HTML for rich text in button
            btn.setText(f"{name_text}\n{sub_text}")
            
            # Dynamic Style
            bg = "#E8F0FE" if is_selected else "white"
            border = "#007AFF" if is_selected else "transparent"
            text_col = "#007AFF" if is_selected else "#1C1C1E"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 10px 15px;
                    background-color: {bg};
                    border: 2px solid {border};
                    border-radius: 10px;
                    color: {text_col};
                    font-weight: 600;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: #F5F5F7;
                }}
                QPushButton:checked {{
                    background-color: #E8F0FE;
                    border: 2px solid #007AFF;
                }}
            """)
            
            btn.clicked.connect(lambda _, p=p: self.load_editor(p))
            self.profile_layout.addWidget(btn)
            
        self.profile_layout.addStretch()

    def create_profile(self):
        new_p = {"id": str(uuid.uuid4()), "name": f"Shift {len(self.profiles)+1}", "sub_label": "Team A", "presets": []}
        self.profiles.append(new_p)
        JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        self.load_editor(new_p)

    def load_editor(self, profile):
        self.current_editing = profile
        self.lbl_editor_title.setVisible(False)
        self.form_container.setVisible(True)
        
        # Update List Selection Visually
        self.render_list()
        
        # Populate Form
        self.name_input.setText(profile.get("name", ""))
        date_str = profile.get("last_updated", "").split(",")[0].strip()
        try:
            d = QDate.fromString(date_str, "dd/MM/yyyy")
            if d.isValid(): self.date_edit.setDate(d)
        except: 
            self.date_edit.setDate(QDate.currentDate())
            
        # Reset Rows
        selected = profile.get("selected_skus", [])
        for i, row in enumerate(self.sku_rows):
            row["data"] = None
            row["sku_val"].setText("")
            row["team_cmb"].setCurrentIndex(0)
            
            if i < len(selected):
                data = selected[i]
                row["data"] = data
                row["sku_val"].setText(str(data.get("code", "")))
                row["team_cmb"].setCurrentText(data.get("team", ""))

    def select_sku(self, index):
        self.pending_sku_index = index
        overlay = SkuSelectorOverlay(self.window())
        overlay.sku_selected.connect(self.on_sku_selected)

    def on_sku_selected(self, sku_data):
        row = self.sku_rows[self.pending_sku_index]
        row["data"] = sku_data
        row["sku_val"].setText(str(sku_data.get("code", "")))

    def _parse_sizes(self, size_str, code=""):
        if not size_str:
            if any(x in code.upper() for x in ["S","M","L","XL"]):
                return ["S", "M", "L", "XL"]
            return ["36","37","38","39","40","41","42","43","44"]
            
        s = str(size_str).strip().upper()
        
        if "," in s:
            items = [x.strip() for x in s.split(",")]
            result = []
            for item in items:
                if "/" in item and "MM" not in item:
                    parts = item.split("/")
                    result.append(parts[-1].strip())
                else:
                    result.append(item)
            return result

        if any(x in s for x in ["SMALL", "MEDIUM", "LARGE", "MM"]):
            return [s]

        def resolve_slash(val):
            if "/" in val:
                parts = val.split("/")
                return parts[-1].strip() 
            return val

        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2:
                start_s = resolve_slash(parts[0].strip())
                end_s = resolve_slash(parts[1].strip())
                
                if start_s.isdigit() and end_s.isdigit():
                    start = int(start_s)
                    end = int(end_s)
                    if start < end:
                        return [str(i) for i in range(start, end + 1)]
            
        if "/" in s:
            return [resolve_slash(s)]
            
        return [s]

    def save_current_profile(self):
        if not self.current_editing: return
        from backend.sku_cache import get_sku_by_code
        presets, selected_skus = [], []
        team_label, sku_label = "", ""
        
        for idx, row in enumerate(self.sku_rows):
            if row["data"]:
                data = row["data"].copy()
                data["team"] = row["team_cmb"].currentText()
                code = data.get("code", "UNKNOWN")
                
                if not data.get("sizes") or not data.get("otorisasi"):
                    full_data = get_sku_by_code(code)
                    if full_data:
                        for k, v in full_data.items():
                            if k not in data or not data[k]:
                                data[k] = v
                
                selected_skus.append(data)
                otorisasi = data.get("otorisasi", "0")
                
                if not team_label: team_label = data["team"]
                if not sku_label: sku_label = code
                
                sizes = self._parse_sizes(data.get("sizes", ""), code)
                
                for s in sizes: 
                    presets.append({
                        "sku": code, 
                        "size": s, 
                        "color_idx": (idx%4)+1, 
                        "team": data["team"],
                        "otorisasi": otorisasi
                    })
        
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
        
        if self.controller:
            self.controller.go_to_live()

    def activate_current_profile(self):
        if not self.current_editing: return
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = self.current_editing["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)
        QMessageBox.information(self, "Active", f"'{self.current_editing['name']}' is now active.")
        
        if self.controller:
            self.controller.go_to_live()

    def delete_current_profile(self):
        if not self.current_editing: return
        if QMessageBox.question(self, "Delete", f"Delete '{self.current_editing['name']}'?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.profiles.remove(self.current_editing)
            JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
            self.current_editing = None
            self.form_container.setVisible(False)
            self.lbl_editor_title.setVisible(True)
            self.render_list()

    def go_back(self):
        if self.controller:
            self.controller.go_back()

    def refresh_data(self):
        self.load_profiles()

    def fetch_sku_data(self):
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("Syncing...")
        add_log("Starting SKU data fetch from Profiles page...")
        
        self.sku_worker = ProductSKUWorker()
        self.sku_worker.finished.connect(self._on_sku_fetch_success)
        self.sku_worker.error.connect(self._on_sku_fetch_error)
        self.sku_worker.start()

    def _on_sku_fetch_success(self, data):
        if data:
            set_sku_data(data)
            add_log(f"SUCCESS: Fetched {len(data)} products.")
            QMessageBox.information(self, "Sync Complete", f"Successfully fetched {len(data)} SKU records.")
        else:
            add_log("WARNING: Query returned 0 results.")
        self._reset_sync_button()

    def _on_sku_fetch_error(self, error_msg):
        add_log(f"ERROR: {error_msg}")
        QMessageBox.warning(self, "Sync Failed", f"Error: {error_msg}")
        self._reset_sync_button()

    def _reset_sync_button(self):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 Sync SKU")

