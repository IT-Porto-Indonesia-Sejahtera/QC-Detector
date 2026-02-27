import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QMessageBox, QDateEdit,
    QMenu
)
from PySide6.QtCore import Qt, QDate, QTimer, QPoint
from PySide6.QtGui import QImage, QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from app.widgets.sku_selector_overlay import SkuSelectorOverlay
from app.utils.image_loader import NetworkImageLoader
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
        
        # Image loader for SKU images
        self.image_loader = NetworkImageLoader(self)
        self.image_loader.image_loaded.connect(self.on_image_loaded)
        self.card_labels = {} # Map gdrive_id -> list of QLabels
        
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
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 1.5px solid #007AFF;
                border-radius: {UIScaling.scale(10)}px;
                padding: {UIScaling.scale(8)}px {UIScaling.scale(20)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 700;
                color: #007AFF;
            }}
            QPushButton:hover {{
                background-color: #F2F7FF;
                border-color: #0063CC;
                color: #0063CC;
            }}
            QPushButton:pressed {{
                background-color: #E5EFFF;
            }}
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
        
        # SKU Configuration Header with Copy Button
        sku_header = QHBoxLayout()
        sku_header.setContentsMargins(0, 5, 0, 5)
        lbl_sku_conf = QLabel("SKU Configuration")
        lbl_sku_conf.setStyleSheet(f"font-size: {UIScaling.scale_font(18)}px; font-weight: 800; color: #1C1C1E; border:none;")
        sku_header.addWidget(lbl_sku_conf)
        sku_header.addStretch()
        
        self.btn_copy = QPushButton("📋 Copy From...")
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setFixedHeight(UIScaling.scale(36))
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F0F5;
                color: #007AFF;
                border: 1px solid #D1D1D6;
                border-radius: {UIScaling.scale(8)}px;
                padding: 0 {UIScaling.scale(12)}px;
                font-size: {UIScaling.scale_font(13)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #E5E5EA;
                border-color: #007AFF;
            }}
            QPushButton:pressed {{
                background-color: #D1D1D6;
            }}
        """)
        self.btn_copy.clicked.connect(self.show_copy_menu)
        sku_header.addWidget(self.btn_copy)
        layout.addLayout(sku_header)
        
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
        
        btn_run = QPushButton("▶ Run Selection")
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1976D2;
                border: 1px solid #BBDEFB;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        btn_run.clicked.connect(self.run_current_profile)

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
        h_actions.addWidget(btn_run)
        h_actions.addWidget(btn_save)
        
        layout.addLayout(h_actions)

    def create_sku_row(self, index):
        container = QFrame()
        container.setCursor(Qt.PointingHandCursor)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #F0F0F0;
                border-radius: {UIScaling.scale(12)}px;
            }}
            QFrame:hover {{
                background-color: #FAFAFA;
                border-color: #007AFF;
            }}
        """)
        container.setFixedHeight(UIScaling.scale(100))
        
        # Add subtle shadow effect if needed, but border is cleaner for now
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)
        
        # Color Indicator & Image
        colors = ["#007AFF", "#FF2D55", "#AF52DE", "#FF9500"]
        indicator = QLabel()
        indicator.setFixedSize(UIScaling.scale(5), UIScaling.scale(70))
        indicator.setStyleSheet(f"background-color: {colors[index % len(colors)]}; border-radius: 2px; border:none;")
        layout.addWidget(indicator)
        
        # SKU Image
        img_label = QLabel()
        img_size = UIScaling.scale(70)
        img_label.setFixedSize(img_size, img_size)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet(f"background-color: #F2F2F7; border-radius: {UIScaling.scale(10)}px; color: #8E8E93; border: 1px solid #E5E5EA;")
        img_label.setText("?")
        layout.addWidget(img_label)
        
        # SKU Display (Text)
        v_sku = QVBoxLayout()
        v_sku.setSpacing(UIScaling.scale(4))
        lbl_grp = QLabel(f"GROUP {index + 1}")
        lbl_grp.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; font-weight: 800; color: #8E8E93; border:none; letter-spacing: 0.5px;")
        v_sku.addWidget(lbl_grp)
        
        txt_sku = QLabel("Empty / Tap to Select")
        txt_sku.setStyleSheet(f"background: transparent; border: none; font-size: {UIScaling.scale_font(18)}px; font-weight: 700; color: #1C1C1E;")
        v_sku.addWidget(txt_sku)
        layout.addLayout(v_sku, 1)
        
        # Position Selector
        v_p = QVBoxLayout()
        v_p.setSpacing(UIScaling.scale(4))
        lbl_p = QLabel("POSITION")
        lbl_p.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; font-weight: 800; color: #8E8E93; border:none; letter-spacing: 0.5px;")
        v_p.addWidget(lbl_p)
        
        cmb_team = QComboBox()
        cmb_team.addItem("", "")
        cmb_team.addItem("Left (Kiri)", "Left")
        cmb_team.addItem("Right (Kanan)", "Right")
        cmb_team.setFixedWidth(UIScaling.scale(160))
        cmb_team.setFixedHeight(UIScaling.scale(38))
        cmb_team.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #D1D1D6;
                border-radius: {UIScaling.scale(8)}px;
                padding: 0 {UIScaling.scale(10)}px;
                font-size: {UIScaling.scale_font(14)}px;
                color: #1C1C1E;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox:hover {{
                border-color: #007AFF;
            }}
        """)
        v_p.addWidget(cmb_team)
        layout.addLayout(v_p)
        
        # Click handling for the whole row (except combo box area)
        def on_row_click(event, idx=index):
            if not cmb_team.underMouse():
                self.select_sku(idx)
        
        container.mousePressEvent = on_row_click
        
        self.sku_rows.append({
            "sku_val": txt_sku,
            "img": img_label, 
            "team_cmb": cmb_team, 
            "data": None
        })
        return container

    def style_input(self, widget):
        widget.setStyleSheet(f"""
            QLineEdit, QDateEdit {{
                border: 1.5px solid #E5E5EA;
                border-radius: {UIScaling.scale(10)}px;
                padding: {UIScaling.scale(10)}px {UIScaling.scale(15)}px;
                background: white;
                color: #1C1C1E;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 500;
            }}
            QLineEdit:focus, QDateEdit:focus {{
                border-color: #007AFF;
                background-color: #FFFFFF;
            }}
            QLineEdit:hover, QDateEdit:hover {{
                border-color: #C7C7CC;
            }}
        """)

    def load_profiles(self):
        try:
            self.profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except Exception as e:
            print(f"[ProfilesPage] Error loading profiles: {e}")
            self.profiles = []
        
        # Re-link current_editing to the matching profile in the new list
        # so that save_current_profile() writes to the correct dict
        if self.current_editing:
            editing_id = self.current_editing.get("id")
            self.current_editing = None
            if editing_id:
                for p in self.profiles:
                    if p.get("id") == editing_id:
                        self.current_editing = p
                        break
            # Re-populate editor form with fresh data from disk
            if self.current_editing:
                self.load_editor(self.current_editing)
                return  # load_editor already calls render_list
        
        self.render_list()

    def render_list(self):
        # Clear list
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
                
        # Re-populate
        for p in self.profiles:
            is_selected = (self.current_editing == p)
            
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(is_selected)
            btn.setFixedHeight(UIScaling.scale(70))
            btn.setCursor(Qt.PointingHandCursor)
            
            # Subtitle (Date) - Remove time if present
            sub_text = p.get('last_updated', '')
            if ',' in sub_text:
                sub_text = sub_text.split(',')[0].strip()
            
            name_text = p.get('name', 'Untitled')
            
            btn.setText(f"{name_text}\n{sub_text}")
            
            # Dynamic Style
            bg = "#E8F0FE" if is_selected else "white"
            border = "#007AFF" if is_selected else "transparent"
            text_col = "#007AFF" if is_selected else "#1C1C1E"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: {UIScaling.scale(10)}px {UIScaling.scale(20)}px;
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 12px;
                    color: {text_col};
                    font-weight: 600;
                    font-size: {UIScaling.scale_font(15)}px;
                }}
                QPushButton:hover {{
                    background-color: #F8F9FA;
                    border-color: #D1D1D6;
                }}
                QPushButton:checked {{
                    background-color: #E8F0FE;
                    border: 1px solid #007AFF;
                    border-left: {UIScaling.scale(6)}px solid #007AFF;
                }}
            """)
            
            btn.clicked.connect(lambda _=False, p=p: self.load_editor(p))
            self.profile_layout.addWidget(btn)
            
        self.profile_layout.addStretch()

    def create_profile(self):
        new_p = {
            "id": str(uuid.uuid4()), 
            "name": f"Shift {len(self.profiles)+1}", 
            "sub_label": "Left (Kiri)", 
            "presets": []
        }
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
            
        # Reset Rows & Labels
        self.card_labels = {}
        selected = profile.get("selected_skus", [])
        for i, row in enumerate(self.sku_rows):
            row["data"] = None
            row["sku_val"].setText("No SKU Selected") # Reset to placeholder text
            row["img"].setPixmap(QPixmap()) # Clear pixmap
            row["img"].setText("?")
            row["team_cmb"].blockSignals(True)
            row["team_cmb"].setCurrentIndex(0)
            row["team_cmb"].blockSignals(False)
            
            if i < len(selected):
                data = selected[i]
                row["data"] = data
                row["sku_val"].setText(str(data.get("code", "")))
                row["team_cmb"].setCurrentText(data.get("team", ""))
                
                # Load image
                gdrive_id = data.get("gdrive_id")
                if gdrive_id:
                    if gdrive_id not in self.card_labels:
                        self.card_labels[gdrive_id] = []
                    self.card_labels[gdrive_id].append(row["img"])
                    self.image_loader.load_image(gdrive_id)

    def show_copy_menu(self):
        if not self.current_editing:
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #D1D1D6;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 4px;
                color: #333;
            }
            QMenu::item:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        others = [p for p in self.profiles if p.get("id") != self.current_editing.get("id")]
        
        if not others:
            act = menu.addAction("No other profiles found")
            act.setEnabled(False)
        else:
            for p in others:
                name = p.get("name", "Untitled")
                action = menu.addAction(name)
                action.triggered.connect(lambda _=False, src=p: self.copy_from_profile(src))
        
        menu.exec(self.btn_copy.mapToGlobal(QPoint(0, self.btn_copy.height())))

    def copy_from_profile(self, source_profile):
        if not self.current_editing:
            return
            
        # Confirm
        reply = QMessageBox.question(
            self, "Copy Configuration", 
            f"Copy SKU configuration from '{source_profile.get('name')}' to '{self.current_editing.get('name')}'?\n\nCurrent SKU choices will be replaced.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Copy relevant data
            self.current_editing["selected_skus"] = [s.copy() for s in source_profile.get("selected_skus", [])]
            self.current_editing["presets"] = [p.copy() for p in source_profile.get("presets", [])]
            
            # Reload editor to show changes
            self.load_editor(self.current_editing)
            self._show_toast("✓ Configuration copied!")

    def select_sku(self, index):
        self.pending_sku_index = index
        overlay = SkuSelectorOverlay(self.window())
        overlay.sku_selected.connect(self.on_sku_selected)

    def on_sku_selected(self, sku_data):
        idx = getattr(self, 'pending_sku_index', -1)
        if idx < 0 or idx >= len(self.sku_rows):
            print(f"[ProfilesPage] Invalid pending_sku_index: {idx}")
            return
        if not sku_data:
            return
        row = self.sku_rows[idx]
        row["data"] = sku_data
        row["sku_val"].setText(str(sku_data.get("code", "")))
        
        # Load image
        gdrive_id = sku_data.get("gdrive_id")
        if gdrive_id:
            row["img"].setText("...")
            if gdrive_id not in self.card_labels:
                self.card_labels[gdrive_id] = []
            self.card_labels[gdrive_id].append(row["img"])
            self.image_loader.load_image(gdrive_id)

    def on_image_loaded(self, gdrive_id, pixmap):
        if gdrive_id in self.card_labels:
            for lbl in self.card_labels[gdrive_id]:
                try:
                    scaled = pixmap.scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    lbl.setPixmap(scaled)
                    lbl.setText("")
                except RuntimeError:
                    pass

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
        if not self.current_editing:
            return
        
        # Validate name
        name = self.name_input.text().strip()
        if not name:
            self._show_toast("Please enter a profile name", is_error=True)
            return
        
        from backend.sku_cache import get_sku_by_code
        presets, selected_skus = [], []
        team_label, sku_label = "", ""
        
        for idx, row in enumerate(self.sku_rows):
            data = row["data"]
            team = row["team_cmb"].currentText()
            
            if data:
                # Validation: Check if position is selected
                if not team:
                    sku_code = data.get("code", "this SKU")
                    self._show_toast(f"Error: Please select Position (Left/Right) for {sku_code}", is_error=True)
                    return
                
                data = data.copy()
                data["team"] = team
                code = data.get("code", "UNKNOWN")
                
                try:
                    if not data.get("sizes") or not data.get("otorisasi"):
                        full_data = get_sku_by_code(code)
                        if full_data:
                            for k, v in full_data.items():
                                if k not in data or not data[k]:
                                    data[k] = v
                except Exception as e:
                    print(f"[ProfilesPage] Error enriching SKU {code}: {e}")
                
                selected_skus.append(data)
                otorisasi = data.get("otorisasi", "0")
                
                if not team_label: team_label = data.get("team", "")
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
            "name": name,
            "last_updated": f"{self.date_edit.date().toString('dd/MM/yyyy')}, {datetime.now().strftime('%H:%M:%S')}",
            "sub_label": team_label or "No Position",
            "sku_label": sku_label,
            "selected_skus": selected_skus,
            "presets": presets
        })
        JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        self.render_list()
        self._show_toast("✓ Profile saved!")

    def activate_current_profile(self):
        if not self.current_editing:
            return
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = self.current_editing["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)
        self._show_toast(f"✓ '{self.current_editing['name']}' is now active.")

    def run_current_profile(self):
        # Save first to ensure latest changes are used
        self.save_current_profile()
        # Activate it
        self.activate_current_profile()
        # Navigate to live
        if self.controller:
            # We want 'Back' from live to go to Menu, not here.
            # In MainWindow.go_to_live(), self.from_live is set to False.
            # So if we call it, it will achieve exactly what's requested.
            self.controller.go_to_live()

    def delete_current_profile(self):
        if not self.current_editing: return
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete")
        msg.setText(f"Delete '{self.current_editing['name']}'?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1B1F27; }
            QMessageBox QLabel { 
                color: #FFFFFF; 
                font-size: 14px; 
                background-color: transparent;
                padding: 10px;
            }
            QPushButton { 
                background-color: #2A2E38; color: #FFFFFF; 
                border: 1px solid #3A3E48; border-radius: 6px;
                padding: 6px 20px; font-size: 13px;
                margin: 5px;
            }
            QPushButton:hover { background-color: #3A3E48; }
        """)
        if msg.exec() == QMessageBox.Yes:
            self.profiles.remove(self.current_editing)
            JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
            self.current_editing = None
            self.form_container.setVisible(False) # Only hide the form
            self.lbl_editor_title.setVisible(True) # Show placeholder
            self.render_list()

    def _show_toast(self, message, is_error=False):
        """Show an inline toast notification that auto-dismisses after 2.5 seconds."""
        if not hasattr(self, '_toast_label'):
            self._toast_label = QLabel(self)
            self._toast_label.setAlignment(Qt.AlignCenter)
            self._toast_label.setFixedHeight(44)
            self._toast_label.hide()
            self._toast_timer = QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(lambda: self._toast_label.hide())
        
        if is_error:
            bg = "#FFEBEE"
            border = "#EF9A9A"
            color = "#C62828"
        else:
            bg = "#E8F5E9"
            border = "#A5D6A7"
            color = "#2E7D32"
        
        self._toast_label.setText(message)
        self._toast_label.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            padding: 0 20px;
        """)
        
        # Position at top center of editor area
        editor_rect = self.editor_area.geometry()
        toast_w = min(400, editor_rect.width() - 40)
        self._toast_label.setFixedWidth(toast_w)
        self._toast_label.move(
            editor_rect.x() + (editor_rect.width() - toast_w) // 2,
            editor_rect.y() + 10
        )
        self._toast_label.show()
        self._toast_label.raise_()
        self._toast_timer.start(2500)

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
            self._show_toast(f"✓ Successfully fetched {len(data)} SKU records.")
        else:
            add_log("WARNING: Query returned 0 results.")
        self._reset_sync_button()

    def _on_sku_fetch_error(self, error_msg):
        add_log(f"ERROR: {error_msg}")
        self._show_toast(f"Sync failed: {error_msg}", is_error=True)
        self._reset_sync_button()

    def _reset_sync_button(self):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 Sync SKU")

