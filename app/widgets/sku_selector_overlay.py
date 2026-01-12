
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
import json
from project_utilities.json_utility import JsonUtility
from app.widgets.base_overlay import BaseOverlay

from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling
from app.utils.image_loader import NetworkImageLoader

SKUS_FILE = os.path.join("output", "settings", "result.json")

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
        
        self.image_loader = NetworkImageLoader(self)
        self.image_loader.image_loaded.connect(self.on_image_loaded)
        self.card_labels = {} # Map gdrive_id -> list of QLabels
        
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
        self.all_skus = []
        if loaded:
            # Deduplicate by 'default_code'
            seen = set()
            for item in loaded:
                code = item.get("default_code")
                if code and code not in seen:
                    seen.add(code)
                    # Create normalized item
                    norm = {
                        "code": code, # Alias for compatibility
                        "default_code": code,
                        "gdrive_id": item.get("gdrive_id"),
                        # We don't care about size here, as we are selecting the SKU model
                        "coeff": code # For compatibility if needed
                    }
                    self.all_skus.append(norm)
        
        self.filtered_skus = self.all_skus

    def filter_skus(self, text):
        text = text.lower().strip()
        if not text:
            self.filtered_skus = self.all_skus
        else:
            self.filtered_skus = [
                s for s in self.all_skus 
                if text in s.get("code", "").lower()
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
        card_h = UIScaling.scale(180) # Increased height for image
        card.setFixedSize(card_w, card_h)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_card']};
                border-radius: {UIScaling.scale(10)}px;
            }}
            QFrame:hover {{
                background-color: #E0E0E0;
                border: 2px solid #2196F3;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(5)
        
        # Image
        img_label = QLabel()
        img_size = UIScaling.scale(100)
        img_label.setFixedSize(img_size, img_size)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("background-color: #EEEEEE; border-radius: 8px; color: #999;")
        img_label.setText("No Img")
        
        gdrive_id = sku.get("gdrive_id")
        if gdrive_id:
            img_label.setText("Loading...")
            if gdrive_id not in self.card_labels:
                self.card_labels[gdrive_id] = []
            self.card_labels[gdrive_id].append(img_label)
            self.image_loader.load_image(gdrive_id)
            
        layout.addWidget(img_label)
        
        # Code
        code_lbl = QLabel(sku.get("code", "UNKNOWN"))
        code_font_size = UIScaling.scale_font(18)
        code_lbl.setStyleSheet(f"font-size: {code_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        code_lbl.setAlignment(Qt.AlignCenter)
        code_lbl.setWordWrap(True)
        
        layout.addWidget(code_lbl)
        
        original_mousePress = card.mousePressEvent
        def on_click(event):
            self.sku_selected.emit(sku)
            self.close_overlay()
            if original_mousePress: original_mousePress(event)
            
        card.mousePressEvent = on_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card

    def on_image_loaded(self, gdrive_id, pixmap):
        if gdrive_id in self.card_labels:
            for lbl in self.card_labels[gdrive_id]:
                try:
                    scaled = pixmap.scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    lbl.setPixmap(scaled)
                    lbl.setText("")
                except RuntimeError:
                    pass
