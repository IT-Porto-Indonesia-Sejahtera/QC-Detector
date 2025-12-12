
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from project_utilities.json_utility import JsonUtility
from app.widgets.base_overlay import BaseOverlay

from app.utils.theme_manager import ThemeManager

SKUS_FILE = os.path.join("output", "settings", "skus.json")

class SkuSelectorOverlay(BaseOverlay):
    sku_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        self.content_box.setFixedSize(500, 600)
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: 15px;
            }}
        """)
        
        self.all_skus = []
        self.filtered_skus = []
        self.load_skus()
        
        self.init_ui()

    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back.setFixedSize(40, 40)
        btn_back.setStyleSheet(f"border: none; font-size: 24px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Select SKU")
        lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.theme['text_main']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title, stretch=1)
        header.addSpacing(40)
        
        layout.addLayout(header)
        
        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search..")
        self.txt_search.textChanged.connect(self.filter_skus)
        self.txt_search.setStyleSheet(f"""
            padding: 10px;
            border: 1px solid {self.theme['border']};
            border-radius: 8px;
            background-color: {self.theme['input_bg']};
            font-size: 16px;
            color: {self.theme['input_text']};
        """)
        
        layout.addWidget(self.txt_search)
        
        # Grid Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"border: none; background: {self.theme['bg_panel']};")
        
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(15)
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        self.render_grid()

    def load_skus(self):
        loaded = JsonUtility.load_from_json(SKUS_FILE)
        if loaded:
            self.all_skus = loaded
        else:
            self.all_skus = []
            
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
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
                
        row = 0
        col = 0
        max_cols = 2
        
        for sku in self.filtered_skus:
            card = self.create_sku_card(sku)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        self.grid_layout.setRowStretch(row + 1, 1)

    def create_sku_card(self, sku):
        card = QFrame()
        card.setFixedSize(200, 150)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_card']};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        
        code_lbl = QLabel(sku.get("code", "UNKNOWN"))
        code_lbl.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {self.theme['text_main']};")
        code_lbl.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(code_lbl)
        
        original_mousePress = card.mousePressEvent
        def on_click(event):
            self.sku_selected.emit(sku)
            self.close_overlay()
            if original_mousePress: original_mousePress(event)
            
        card.mousePressEvent = on_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card
