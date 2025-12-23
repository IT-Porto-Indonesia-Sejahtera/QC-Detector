
import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDateEdit, QScrollArea, QWidget, QFrame, 
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon
from app.utils.ui_scaling import UIScaling

class ProfileEditorDialog(QDialog):
    def __init__(self, parent=None, profile_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Preset Profile")
        self.setModal(True)
        self.resize(UIScaling.scale(600), UIScaling.scale(700))
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
            }
            QLabel {
                font-weight: bold;
                color: black;
            }
            QLineEdit, QDateEdit, QComboBox {
                padding: 8px;
                border: 1px solid #CCC;
                border-radius: 8px;
                background-color: #F0F0F0;
                color: black; /* Explicit black text */
            }
        """)
        
        self.profile_data = profile_data or {}
        self.sku_rows = [] # To store widgets for each SKU row
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back_size = UIScaling.scale(40)
        btn_back_font_size = UIScaling.scale_font(24)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setStyleSheet(f"border: none; font-size: {btn_back_font_size}px; font-weight: bold;")
        btn_back.clicked.connect(self.reject)
        
        lbl_title = QLabel("Add/Edit Preset Profile")
        title_font_size = UIScaling.scale_font(20)
        lbl_title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        self.btn_save = QPushButton("Save")
        btn_save_w = UIScaling.scale(80)
        btn_save_h = UIScaling.scale(40)
        self.btn_save.setFixedSize(btn_save_w, btn_save_h)
        self.btn_save.setStyleSheet(f"""
            background-color: #E0E0E0;
            border-radius: {UIScaling.scale(8)}px;
            font-weight: bold;
            color: black;
            font-size: {UIScaling.scale_font(14)}px;
        """)
        self.btn_save.clicked.connect(self.on_save)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title, stretch=1)
        header.addWidget(self.btn_save)
        
        main_layout.addLayout(header)
        
        # Form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        # Tag
        hbox_tag = QHBoxLayout()
        lbl_tag = QLabel("Tag")
        lbl_w = UIScaling.scale(50)
        lbl_tag.setFixedWidth(lbl_w)
        lbl_tag.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px;")
        self.txt_tag = QLineEdit()
        self.txt_tag.setPlaceholderText("Shift X")
        hbox_tag.addWidget(lbl_tag)
        hbox_tag.addWidget(self.txt_tag)
        form_layout.addLayout(hbox_tag)
        
        # Date
        hbox_date = QHBoxLayout()
        lbl_date = QLabel("Date")
        lbl_date.setFixedWidth(lbl_w)
        lbl_date.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px;")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        # Fake "Cal" button style logic is built-in to QDateEdit with popup, 
        # but mockup shows a separate button. We can just use standard QDateEdit for now.
        hbox_date.addWidget(lbl_date)
        hbox_date.addWidget(self.date_edit)
        form_layout.addLayout(hbox_date)
        
        main_layout.addLayout(form_layout)
        
        # SKU Rows (Up to 4)
        self.sku_container = QVBoxLayout()
        self.sku_container.setSpacing(15)
        
        for i in range(4):
            row_widget = self.create_sku_row(i)
            self.sku_container.addWidget(row_widget)
            
        main_layout.addLayout(self.sku_container)
        main_layout.addStretch()

    def create_sku_row(self, index):
        container = QFrame()
        container.setFixedHeight(UIScaling.scale(120))
        container.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Image Placeholder
        # Mocking the blank square
        img_placeholder = QLabel()
        img_size = UIScaling.scale(80)
        img_placeholder.setFixedSize(img_size, img_size)
        img_placeholder.setStyleSheet(f"background-color: #E0E0E0; border-radius: {UIScaling.scale(8)}px;")
        layout.addWidget(img_placeholder)
        
        # Info Column
        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        
        # SKU Row
        sku_row = QHBoxLayout()
        lbl_sku = QLabel("SKU")
        sku_lbl_w = UIScaling.scale(40)
        lbl_sku.setFixedWidth(sku_lbl_w)
        lbl_sku.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px;")
        
        # SKU Value Display (Disabled input or Label)
        txt_sku_val = QLineEdit()
        txt_sku_val.setReadOnly(True)
        txt_sku_val.setPlaceholderText("Select SKU first...")
        txt_sku_val.setStyleSheet(f"background-color: #E0E0E0; border: none; padding: {UIScaling.scale(5)}px; color: black; font-size: {UIScaling.scale_font(13)}px;")
        
        btn_select = QPushButton("select")
        btn_sel_w = UIScaling.scale(60)
        btn_sel_h = UIScaling.scale(30)
        btn_select.setFixedSize(btn_sel_w, btn_sel_h)
        btn_select.setStyleSheet(f"background-color: #CCC; border-radius: {UIScaling.scale(5)}px; font-weight: bold; color: black; font-size: {UIScaling.scale_font(13)}px;")
        btn_select.clicked.connect(lambda _, idx=index: self.select_sku(idx))
        
        sku_row.addWidget(lbl_sku)
        sku_row.addWidget(txt_sku_val)
        sku_row.addWidget(btn_select)
        
        # Team Row
        team_row = QHBoxLayout()
        lbl_team = QLabel("Team")
        lbl_team.setFixedWidth(sku_lbl_w)
        lbl_team.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px;")
        
        cmb_team = QComboBox()
        cmb_team.addItems(["", "Team A", "Team B", "Team C", "Team D"])
        
        team_row.addWidget(lbl_team)
        team_row.addWidget(cmb_team)
        
        info_col.addLayout(sku_row)
        info_col.addLayout(team_row)
        
        layout.addLayout(info_col)
        
        # Convert QDate to string or whatever needed? No, store references
        self.sku_rows.append({
            "img": img_placeholder,
            "sku_val": txt_sku_val,
            "team_cmb": cmb_team,
            "data": None # To store selected SKU object
        })
        
        return container

    def load_data(self):
        # Populate if editing
        if not self.profile_data:
            # Shift + Index logic handled by parent or defaults
            return
            
        self.txt_tag.setText(self.profile_data.get("name", ""))
        
        # Date
        date_str = self.profile_data.get("last_updated", "")
        if "," in date_str:
            date_str = date_str.split(",")[0].strip() # "22/05/2025"
            try:
                date = QDate.fromString(date_str, "dd/MM/yyyy")
                if date.isValid():
                    self.date_edit.setDate(date)
            except:
                pass

        # SKU Rows
        # Assuming profile_data might have 'skus' list in future, but structure was:
        # { "name": "Shift 1", "sub_label": "Team A", "sku_label": "SKU E...", "presets": [] }
        # The current data structure in implementation plan didn't explicitly store 4 SKUs separately.
        # It just had "sku_label". 
        # We need to adapt the data structure to store this list of selected SKUs.
        # Let's map "sku_label" to the first slot for now for compatibility, 
        # or check if there's a 'selected_skus' list.
        
        selected = self.profile_data.get("selected_skus", [])
        for i, data in enumerate(selected):
            if i < 4:
                self.sku_rows[i]["data"] = data
                self.sku_rows[i]["sku_val"].setText(data.get("code", str(data.get("coeff", ""))))
                self.sku_rows[i]["team_cmb"].setCurrentText(data.get("team", ""))

    def select_sku(self, index):
        from app.widgets.sku_selector_dialog import SkuSelectorDialog # Lazy import to avoid circular if any
        
        dlg = SkuSelectorDialog(self)
        if dlg.exec():
            # Dialog handles signal, but let's just use signal connection or simple exec result?
            # Start loop, but cleaner to use signal.
            # Actually with exec(), we usually wait for accept(). 
            # But the accepted signal/sku_selected signal needs to be caught.
            # Let's connect signal BEFORE exec.
             pass
        # Wait, I need to capture the data.
        # SkuSelectorDialog emits `sku_selected`.
        
        # Re-implement connection logic:
        self.pending_index = index
        dlg = SkuSelectorDialog(self)
        dlg.sku_selected.connect(self.on_sku_selected)
        dlg.exec()

    def on_sku_selected(self, sku_data):
        index = self.pending_index
        row = self.sku_rows[index]
        
        row["data"] = sku_data
        # Mockup requested showing COEFF (e.g. 0.2123459) in the text box
        row["sku_val"].setText(str(sku_data.get("coeff", "")))
        
        # Update Image (Simulated color change)
        row["img"].setStyleSheet("background-color: #2196F3; border-radius: 8px;") # Blue to indicate selection

    def on_save(self):
        # Validation
        has_sku = False
        selected_skus = []
        
        first_valid_team = ""
        first_valid_sku_label = ""
        
        for row in self.sku_rows:
            data = row["data"]
            team = row["team_cmb"].currentText()
            
            if data:
                has_sku = True
                # Start building payload
                item = data.copy()
                item["team"] = team
                selected_skus.append(item)
                
                if not first_valid_team and team: first_valid_team = team
                if not first_valid_sku_label: first_valid_sku_label = data.get("code", "SKU")
        
        if not has_sku:
            QMessageBox.warning(self, "Validation Error", "Please select at least one SKU.")
            return

        # Prepare Result
        tag = self.txt_tag.text().strip() or "Shift"
        date_str = self.date_edit.date().toString("dd/MM/yyyy")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # We construct the profile dictionary
        # Preserve original ID if editing
        
        self.result_data = {
            "name": tag,
            "last_updated": f"{date_str}, {timestamp}",
            # Derived fields for the list view
            "sub_label": first_valid_team or "No Team", 
            "sku_label": first_valid_sku_label,
            
            "selected_skus": selected_skus, # New field to persist this dialog's state
            
            # Presets? 
            # If we select SKUs here, do we auto-generate presets?
            # User said "select up to 4 SKUs". 
            # Maybe this defines the pool of SKUs for the 24 buttons?
            # For now, we just save this metadata. The 24 presets are separate (or maybe generated from these).
            # We'll preserve existing presets if any.
        }
        
        self.accept()
        
    def get_data(self):
        # Merge with original specific keys to keep ID, presets, etc.
        if self.profile_data:
            merged = self.profile_data.copy()
            merged.update(self.result_data)
            return merged
        return self.result_data
