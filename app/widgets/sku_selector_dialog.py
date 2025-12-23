
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling

SKUS_FILE = os.path.join("output", "settings", "skus.json")

class SkuSelectorDialog(QDialog):
    sku_selected = Signal(dict) # Emits the selected SKU dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select SKU")
        self.setModal(True)
        self.resize(UIScaling.scale(500), UIScaling.scale(600))
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
            }
            QLabel { color: black; }
            QLineEdit {
                padding: 10px;
                border: 1px solid #CCC;
                border-radius: 8px;
                background-color: #E0E0E0;
                font-size: 16px;
                color: black;
            }
        """)

        # Data
        self.all_skus = []
        self.filtered_skus = []
        self.load_skus()
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back_size = UIScaling.scale(40)
        btn_back_font_size = UIScaling.scale_font(24)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setStyleSheet(f"border: none; font-size: {btn_back_font_size}px; font-weight: bold; color: black;")
        btn_back.clicked.connect(self.reject)
        
        lbl_title = QLabel("Select SKU")
        title_font_size = UIScaling.scale_font(20)
        lbl_title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; color: black;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title, stretch=1)
        header.addSpacing(40) # Balance
        
        layout.addLayout(header)
        
        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search..")
        self.txt_search.textChanged.connect(self.filter_skus)
        # Search Icon could be added via action (mockup shows one), leaving simple for now
        
        layout.addWidget(self.txt_search)
        
        # Grid Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: white;")
        
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(15)
        # self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        self.render_grid()

    def load_skus(self):
        loaded = JsonUtility.load_from_json(SKUS_FILE)
        if loaded:
            self.all_skus = loaded
        else:
            self.all_skus = [] # Or seed defaults? I created file already.
            
        self.filtered_skus = self.all_skus

    def filter_skus(self, text):
        text = text.lower().strip()
        if not text:
            self.filtered_skus = self.all_skus
        else:
            self.filtered_skus = [
                s for s in self.all_skus 
                if text in s.get("code", "").lower() or str(s.get("coeff", "")).lower() in text
            ]
        self.render_grid()

    def render_grid(self):
        # Clear
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
                
        # Render
        row = 0
        col = 0
        max_cols = 2 # 2 columns as per mockup
        
        for sku in self.filtered_skus:
            card = self.create_sku_card(sku)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Push to top
        # The grid layout naturally centers vertically if not pushed? 
        # Add filtering spacer logic if needed, but GridLayout row stretch usually handles it.
        self.grid_layout.setRowStretch(row + 1, 1)


    def create_sku_card(self, sku):
        # Card Frame
        card = QFrame()
        card_w = UIScaling.scale(200)
        card_h = UIScaling.scale(150)
        card.setFixedSize(card_w, card_h) # Approx size from ratio
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #E0E0E0;
                border-radius: {UIScaling.scale(10)}px;
            }}
        """)
        
        # Layout for overlay
        # Since we want text OVER image, we can use a layout stack or just a label with background image.
        # But here image is placeholder gray.
        # Let's just use a vertical layout centering text, as mockup shows simple gray box with text.
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        
        code_lbl = QLabel(sku.get("code", "UNKNOWN"))
        code_font_size = UIScaling.scale_font(24)
        code_lbl.setStyleSheet(f"font-size: {code_font_size}px; font-weight: 900; color: black;")
        code_lbl.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(code_lbl)
        
        # Click handling
        original_mousePress = card.mousePressEvent
        def on_click(event):
            self.sku_selected.emit(sku)
            self.accept()
            if original_mousePress: original_mousePress(event)
            
        card.mousePressEvent = on_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card
