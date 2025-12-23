
import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDateEdit, QComboBox, QFrame, QMessageBox, QWidget, QListView
)
from PySide6.QtCore import Qt, QDate, Signal
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling

class ProfileEditorOverlay(BaseOverlay):
    data_saved = Signal(dict) # Emits the updated profile data

    def __init__(self, parent=None, profile_data=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        # Make content box responsive
        scaled_w = UIScaling.scale(600)
        scaled_h = UIScaling.scale(700)
        
        # Ensure it doesn't exceed 90% of screen
        screen_size = UIScaling.get_screen_size()
        max_w = int(screen_size.width() * 0.9)
        max_h = int(screen_size.height() * 0.9)
        
        self.content_box.setMinimumSize(UIScaling.scale(400), UIScaling.scale(400))
        self.content_box.setMaximumSize(min(scaled_w, max_w), min(scaled_h, max_h))
        self.content_box.resize(min(scaled_w, max_w), min(scaled_h, max_h))

        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: {UIScaling.scale(15)}px;
            }}
        """)
        
        self.profile_data = profile_data or {}
        self.sku_rows = [] 
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back_size = UIScaling.scale(60)
        btn_back_font_size = UIScaling.scale_font(24)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setStyleSheet(f"border: none; font-size: {btn_back_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Add/Edit Preset Profile")
        title_font_size = UIScaling.scale_font(20)
        lbl_title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        self.btn_save = QPushButton("Save")
        btn_save_w = UIScaling.scale(100)
        btn_save_h = UIScaling.scale(50)
        self.btn_save.setFixedSize(btn_save_w, btn_save_h)
        self.btn_save.setStyleSheet(f"""
            background-color: {self.theme['btn_bg']};
            border-radius: {UIScaling.scale(8)}px;
            font-weight: bold;
            color: {self.theme['btn_text']};
            font-size: {UIScaling.scale_font(16)}px;
        """)
        self.btn_save.clicked.connect(self.on_save)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title, stretch=1)
        header.addWidget(self.btn_save)
        
        layout.addLayout(header)
        
        # Form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        # Style Inputs - Enhanced with proper dropdown and calendar styling
        input_padding = UIScaling.scale(8)
        input_radius = UIScaling.scale(8)
        input_font_size = UIScaling.scale_font(14)
        input_style = f"""
            QLineEdit, QDateEdit, QComboBox {{
                padding: {input_padding}px;
                border: 1px solid {self.theme['border']};
                border-radius: {input_radius}px;
                background-color: {self.theme['input_bg']};
                color: {self.theme['input_text']};
                font-size: {input_font_size}px;
            }}
            
            /* Date Picker Button with Calendar Icon */
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: {UIScaling.scale(35)}px;
                border-left: 1px solid {self.theme['border']};
                border-top-right-radius: {input_radius}px;
                border-bottom-right-radius: {input_radius}px;
                background-color: #F5F5F5;
            }}
            
            QDateEdit::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            
            QDateEdit::drop-down::after {{
                content: "📅";
                font-size: {UIScaling.scale_font(16)}px;
            }}
            
            /* ComboBox Dropdown Button */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: {UIScaling.scale(30)}px;
                border-left: 1px solid {self.theme['border']};
                border-top-right-radius: {input_radius}px;
                border-bottom-right-radius: {input_radius}px;
                background-color: #F5F5F5;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            
            /* Fix ComboBox Dropdown Menu - Use QListView for specificity */
            QComboBox QListView {{
                background-color: white !important;
                color: #333333 !important;
                selection-background-color: #2196F3;
                selection-color: white;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                padding: 2px;
                outline: none;
            }}
            
            QComboBox QListView::item {{
                padding: 6px 12px;
                border-radius: 4px;
                color: #333333;
                background-color: transparent;
            }}
            
            QComboBox QListView::item:hover {{
                background-color: #E3F2FD;
                color: #333333;
            }}
            
            QComboBox QListView::item:selected {{
                background-color: #2196F3;
                color: white;
            }}
            
            /* Calendar Widget Popup Styling */
            QCalendarWidget {{
                background-color: white;
            }}
            
            QCalendarWidget QWidget {{
                background-color: white;
                color: #333333;
            }}
            
            QCalendarWidget QAbstractItemView {{
                background-color: white;
                color: #333333;
                selection-background-color: #2196F3;
                selection-color: white;
            }}
            
            QCalendarWidget QToolButton {{
                background-color: #F5F5F5;
                color: #333333;
                border-radius: 4px;
                padding: 4px;
            }}
            
            QCalendarWidget QToolButton:hover {{
                background-color: #E3F2FD;
            }}
            
            QCalendarWidget QMenu {{
                background-color: white;
                color: #333333;
            }}
            
            QCalendarWidget QSpinBox {{
                background-color: white;
                color: #333333;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
            }}
        """
        self.setStyleSheet(input_style)
        
        # Tag
        hbox_tag = QHBoxLayout()
        lbl_tag = QLabel("Tag")
        lbl_w = UIScaling.scale(50)
        lbl_tag.setFixedWidth(lbl_w)
        lbl_tag.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {input_font_size}px;")
        self.txt_tag = QLineEdit()
        self.txt_tag.setPlaceholderText("Shift X")
        hbox_tag.addWidget(lbl_tag)
        hbox_tag.addWidget(self.txt_tag)
        form_layout.addLayout(hbox_tag)
        
        # Date with Calendar Icon - Custom Layout
        hbox_date = QHBoxLayout()
        lbl_date = QLabel("Date")
        lbl_date.setFixedWidth(lbl_w)
        lbl_date.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {input_font_size}px;")
        
        # Create custom date widget with calendar button
        date_container = QWidget()
        date_layout = QHBoxLayout(date_container)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(0)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setButtonSymbols(QDateEdit.NoButtons)
        
        # Set larger calendar widget size
        calendar = self.date_edit.calendarWidget()
        calendar.setMinimumSize(UIScaling.scale(350), UIScaling.scale(300))
        cal_font_size = UIScaling.scale_font(14)
        calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: white;
                font-size: {cal_font_size}px;
            }}
            QCalendarWidget QWidget {{
                background-color: white;
                color: #333333;
            }}
            QCalendarWidget QTableView {{
                background-color: white;
                selection-background-color: #2196F3;
                selection-color: white;
            }}
            QCalendarWidget QToolButton {{
                background-color: #F5F5F5;
                color: #333333;
                border-radius: {UIScaling.scale(4)}px;
                padding: {UIScaling.scale(8)}px;
                font-size: {cal_font_size}px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: #E3F2FD;
            }}
            QCalendarWidget QMenu {{
                background-color: white;
                color: #333333;
            }}
            QCalendarWidget QSpinBox {{
                background-color: white;
                color: #333333;
                border: 1px solid {self.theme['border']};
                border-radius: {UIScaling.scale(4)}px;
                padding: {UIScaling.scale(4)}px;
            }}
        """)
        
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                border: 1px solid {self.theme['border']};
                border-top-left-radius: {input_radius}px;
                border-bottom-left-radius: {input_radius}px;
                border-right: none;
                padding: {input_padding}px;
                background-color: white;
                color: #333333;
            }}
        """)
        
        # Calendar button
        cal_btn = QPushButton("📅")
        cal_btn_w = UIScaling.scale(40)
        cal_btn_h = UIScaling.scale(36)
        cal_btn_font_size = UIScaling.scale_font(18)
        cal_btn.setFixedSize(cal_btn_w, cal_btn_h)
        cal_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F5F5;
                border: 1px solid {self.theme['border']};
                border-left: none;
                border-top-right-radius: {input_radius}px;
                border-bottom-right-radius: {input_radius}px;
                font-size: {cal_btn_font_size}px;
            }}
            QPushButton:hover {{
                background-color: #E8E8E8;
            }}
        """)
        cal_btn.clicked.connect(lambda: self.date_edit.setFocus() or self.date_edit.calendarWidget().show())
        
        date_layout.addWidget(self.date_edit)
        date_layout.addWidget(cal_btn)
        
        hbox_date.addWidget(lbl_date)
        hbox_date.addWidget(date_container)
        form_layout.addLayout(hbox_date)
        
        layout.addLayout(form_layout)
        
        # SKU Rows (Up to 4)
        self.sku_container = QVBoxLayout()
        self.sku_container.setSpacing(15)
        
        for i in range(4):
            row_widget = self.create_sku_row(i)
            self.sku_container.addWidget(row_widget)
            
        layout.addLayout(self.sku_container)
        layout.addStretch()

    def create_sku_row(self, index):
        container = QFrame()
        container.setFixedHeight(UIScaling.scale(140))
        container.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        img_size = UIScaling.scale(100)
        img_placeholder = QLabel()
        img_placeholder.setFixedSize(img_size, img_size)
        img_placeholder.setStyleSheet(f"background-color: {self.theme['bg_card']}; border-radius: {UIScaling.scale(8)}px;")
        layout.addWidget(img_placeholder)
        
        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        
        sku_row = QHBoxLayout()
        lbl_sku = QLabel("SKU")
        sku_lbl_w = UIScaling.scale(40)
        lbl_sku.setFixedWidth(sku_lbl_w)
        lbl_sku.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {UIScaling.scale_font(13)}px;")
        
        txt_sku_val = QLineEdit()
        txt_sku_val.setReadOnly(True)
        txt_sku_val.setPlaceholderText("Select SKU first...")
        txt_sku_val.setStyleSheet(f"background-color: {self.theme['bg_card']}; border: none; padding: {UIScaling.scale(5)}px; color: {self.theme['text_main']};")
        
        btn_select = QPushButton("select")
        btn_sel_w = UIScaling.scale(100)
        btn_sel_h = UIScaling.scale(50)
        btn_select.setFixedSize(btn_sel_w, btn_sel_h)
        btn_select.setStyleSheet(f"background-color: {self.theme['btn_bg']}; border-radius: {UIScaling.scale(5)}px; font-weight: bold; color: {self.theme['btn_text']}; font-size: {UIScaling.scale_font(16)}px;")
        btn_select.clicked.connect(lambda _, idx=index: self.select_sku(idx))
        
        sku_row.addWidget(lbl_sku)
        sku_row.addWidget(txt_sku_val)
        sku_row.addWidget(btn_select)
        
        team_row = QHBoxLayout()
        lbl_team = QLabel("Team")
        lbl_team.setFixedWidth(sku_lbl_w)
        lbl_team.setStyleSheet(f"color: {self.theme['text_main']}; font-size: {UIScaling.scale_font(13)}px;")
        
        cmb_team = QComboBox()
        cmb_team.addItems(["", "Team A", "Team B", "Team C", "Team D"])
        
        # Create and set custom white list view to override black dropdown
        list_view = QListView()
        list_view.setStyleSheet("""
            QListView {
                background-color: white;
                color: #333333;
                padding: 4px;
                outline: none;
                border: none;
            }
            QListView::item {
                padding: 8px 12px;
                border-radius: 4px;
                color: #333333;
                background-color: transparent;
            }
            QListView::item:hover {
                background-color: #E3F2FD;
            }
            QListView::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        cmb_team.setView(list_view)
        
        team_row.addWidget(lbl_team)
        team_row.addWidget(cmb_team)
        
        info_col.addLayout(sku_row)
        info_col.addLayout(team_row)
        
        layout.addLayout(info_col)
        
        self.sku_rows.append({
            "img": img_placeholder,
            "sku_val": txt_sku_val,
            "team_cmb": cmb_team,
            "data": None 
        })
        
        return container

    def load_data(self):
        if not self.profile_data: return
        
        self.txt_tag.setText(self.profile_data.get("name", ""))
        
        date_str = self.profile_data.get("last_updated", "")
        if "," in date_str:
            date_str = date_str.split(",")[0].strip()
            try:
                date = QDate.fromString(date_str, "dd/MM/yyyy")
                if date.isValid():
                    self.date_edit.setDate(date)
            except: pass

        selected = self.profile_data.get("selected_skus", [])
        for i, data in enumerate(selected):
            if i < 4:
                self.sku_rows[i]["data"] = data
                self.sku_rows[i]["sku_val"].setText(str(data.get("coeff", "")))
                self.sku_rows[i]["team_cmb"].setCurrentText(data.get("team", ""))
                self.sku_rows[i]["img"].setStyleSheet("background-color: #2196F3; border-radius: 8px;")

    def select_sku(self, index):
        from app.widgets.sku_selector_overlay import SkuSelectorOverlay
        
        # Parent to self.parent() so it covers everything
        # Store index to know which row updates
        self.pending_index = index
        overlay = SkuSelectorOverlay(self.parent())
        overlay.sku_selected.connect(self.on_sku_selected)
        
    def on_sku_selected(self, sku_data):
        index = self.pending_index
        row = self.sku_rows[index]
        row["data"] = sku_data
        row["sku_val"].setText(str(sku_data.get("coeff", "")))
        row["img"].setStyleSheet("background-color: #2196F3; border-radius: 8px;")

    def on_save(self):
        has_sku = False
        selected_skus = []
        generated_presets = [] # Flattened list for main screen
        
        first_valid_team = ""
        first_valid_sku_label = ""
        
        # Helper to decide sizes based on SKU code
        def get_sizes_for_sku(code):
            c = code.upper()
            if "S" in c or "M" in c or "L" in c or "XL" in c:
               return ["S", "M", "L", "XL"]
            return ["36", "37", "38", "39", "40", "41", "42", "43", "44"]

        for idx, row in enumerate(self.sku_rows):
            data = row["data"]
            team = row["team_cmb"].currentText()
            
            if data:
                has_sku = True
                item = data.copy()
                item["team"] = team
                selected_skus.append(item)
                
                sku_code = data.get("code", "UNKNOWN")
                if not first_valid_team and team: first_valid_team = team
                if not first_valid_sku_label: first_valid_sku_label = sku_code
                
                # Generate Presets for this SKU
                color_index = (idx % 4) + 1 # 1..4 based on row
                sizes = get_sizes_for_sku(sku_code)
                
                for s in sizes:
                    generated_presets.append({
                        "sku": sku_code,
                        "size": s,
                        "color_idx": color_index
                    })
        
        if not has_sku:
            QMessageBox.warning(self, "Validation Error", "Please select at least one SKU.")
            return

        tag = self.txt_tag.text().strip() or "Shift"
        date_str = self.date_edit.date().toString("dd/MM/yyyy")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        result_data = {
            "name": tag,
            "last_updated": f"{date_str}, {timestamp}",
            "sub_label": first_valid_team or "No Team", 
            "sku_label": first_valid_sku_label,
            "selected_skus": selected_skus,
            "presets": generated_presets # CRITICAL: Contains the button definitions
        }
        
        if self.profile_data:
            merged = self.profile_data.copy()
            merged.update(result_data)
            self.data_saved.emit(merged)
        else:
            self.data_saved.emit(result_data)
        
        self.close_overlay()
