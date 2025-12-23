
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from project_utilities.json_utility import JsonUtility
from app.widgets.base_overlay import BaseOverlay

from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling

SKUS_FILE = os.path.join("output", "settings", "skus.json")

class SkuSelectorOverlay(BaseOverlay):
    sku_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        
        scaled_w = UIScaling.scale(500)
        scaled_h = UIScaling.scale(600)
        
        # Ensure it doesn't exceed 90% of screen
        screen_size = UIScaling.get_screen_size()
        max_w = int(screen_size.width() * 0.9)
        max_h = int(screen_size.height() * 0.9)
        
        self.content_box.setMinimumSize(UIScaling.scale(300), UIScaling.scale(300))
        self.content_box.setMaximumSize(min(scaled_w, max_w), min(scaled_h, max_h))
        self.content_box.resize(min(scaled_w, max_w), min(scaled_h, max_h))

        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_panel']}; 
                border-radius: {UIScaling.scale(15)}px;
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
        btn_back_size = UIScaling.scale(60)
        btn_back_font_size = UIScaling.scale_font(24)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setStyleSheet(f"border: none; font-size: {btn_back_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Select SKU")
        title_font_size = UIScaling.scale_font(20)
        lbl_title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addWidget(lbl_title, stretch=1)
        header.addSpacing(40)
        
        layout.addLayout(header)
        
        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search..")
        self.txt_search.textChanged.connect(self.filter_skus)
        search_padding = UIScaling.scale(10)
        search_font_size = UIScaling.scale_font(16)
        search_radius = UIScaling.scale(8)
        self.txt_search.setStyleSheet(f"""
            padding: {search_padding}px;
            border: 1px solid {self.theme['border']};
            border-radius: {search_radius}px;
            background-color: {self.theme['input_bg']};
            font-size: {search_font_size}px;
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
        card_w = UIScaling.scale(200)
        card_h = UIScaling.scale(150)
        card.setFixedSize(card_w, card_h)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_card']};
                border-radius: {UIScaling.scale(10)}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        
        code_lbl = QLabel(sku.get("code", "UNKNOWN"))
        code_font_size = UIScaling.scale_font(24)
        code_lbl.setStyleSheet(f"font-size: {code_font_size}px; font-weight: 900; color: {self.theme['text_main']};")
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
