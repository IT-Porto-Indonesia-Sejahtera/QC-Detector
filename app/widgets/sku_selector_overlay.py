
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
import json
from project_utilities.json_utility import JsonUtility
from app.widgets.base_overlay import BaseOverlay

from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling
from app.utils.image_loader import NetworkImageLoader
from backend.sku_cache import get_sku_data

# Performance constants
MAX_VISIBLE_ITEMS = 20  # Only render this many at a time
SEARCH_DEBOUNCE_MS = 300  # Wait before filtering


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
        self.card_labels = {}  # Map gdrive_id -> list of QLabels
        
        # Debounce timer for search
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_filter)
        self._pending_search = ""
        
        self.all_skus = []
        self.filtered_skus = []
        self._visible_count = MAX_VISIBLE_ITEMS  # Start with limited items
        self._selection_made = False  # Prevent double-click
        
        self.load_skus()
        self.init_ui()
    
    def close_overlay(self):
        """Override to cancel pending image downloads before closing."""
        self._search_timer.stop()
        if hasattr(self, 'image_loader'):
            self.image_loader.cancel_all()
        self.card_labels.clear()
        super().close_overlay()

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
        
        # Search Bar with debouncing
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search..")
        self.txt_search.textChanged.connect(self._on_search_text_changed)
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
        
        # Results count label
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color: {self.theme['text_sub']}; font-size: {UIScaling.scale_font(12)}px;")
        layout.addWidget(self.lbl_count)
        
        # Grid Area with infinite scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"border: none; background: {self.theme['bg_panel']};")
        
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(15)
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        # Connect scroll for infinite loading
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._is_loading_more = False  # Prevent multiple triggers
        
        self.render_grid()

    def load_skus(self):
        # Load from the persistent SKU cache (fetched from database)
        try:
            loaded = get_sku_data()
        except Exception as e:
            print(f"[SkuSelector] Error loading SKU data: {e}")
            loaded = None
        
        self.all_skus = []
        if loaded:
            # Deduplicate by 'Nama Produk' (product name from new query)
            seen = set()
            for item in loaded:
                try:
                    # Use new field names from database query
                    code = item.get("Nama Produk") or item.get("default_code")
                    if code and code not in seen:
                        seen.add(code)
                        # Create normalized item with both old and new field mappings
                        norm = {
                            "code": code,
                            "Nama Produk": code, # Added for compatibility
                            "default_code": code,
                            "gdrive_id": item.get("GDrive ID") or item.get("gdrive_id"),
                            "otorisasi": item.get("Perbesaran Ukuran (Otorisasi)") or 0,
                            "kategori": item.get("Kategori"),
                            "sizes": item.get("List Size Available"),
                            "coeff": code
                        }
                        self.all_skus.append(norm)
                except Exception as e:
                    print(f"[SkuSelector] Error normalizing SKU item: {e}")
                    continue
        
        self.filtered_skus = self.all_skus

    def _on_search_text_changed(self, text):
        """Debounced search - waits before actually filtering."""
        self._pending_search = text
        self._search_timer.start(SEARCH_DEBOUNCE_MS)
    
    def _do_filter(self):
        """Actually perform the filter after debounce."""
        text = self._pending_search.lower().strip()
        self._visible_count = MAX_VISIBLE_ITEMS  # Reset pagination
        
        if not text:
            self.filtered_skus = self.all_skus
        else:
            self.filtered_skus = [
                s for s in self.all_skus 
                if text in s.get("code", "").lower()
            ]
        self.render_grid()
    
    def _load_more(self):
        """Load more items (pagination)."""
        if self._is_loading_more:
            return
        self._is_loading_more = True
        self._visible_count += MAX_VISIBLE_ITEMS
        self._append_more_items()  # Don't re-render everything, just append
        self._is_loading_more = False
    
    def _on_scroll(self, value):
        """Infinite scroll - load more when near bottom."""
        scrollbar = self.scroll.verticalScrollBar()
        # Check if near bottom (within 100px)
        if scrollbar.maximum() - value < 100:
            # Only load more if there are more items
            if self._visible_count < len(self.filtered_skus):
                self._load_more()
    
    def _append_more_items(self):
        """Append more items without re-rendering everything."""
        total_count = len(self.filtered_skus)
        current_showing = self.grid_layout.count()
        
        # Calculate grid position to continue from
        max_cols = 2
        row = current_showing // max_cols
        col = current_showing % max_cols
        
        # Add new items up to _visible_count
        new_items = self.filtered_skus[current_showing:self._visible_count]
        
        for sku in new_items:
            card = self.create_sku_card(sku)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        self.grid_layout.setRowStretch(row + 1, 1)
        
        # Update count label
        showing_count = min(self._visible_count, total_count)
        if showing_count < total_count:
            self.lbl_count.setText(f"Showing {showing_count} of {total_count} items (scroll for more)")
        else:
            self.lbl_count.setText(f"{total_count} items")

    def render_grid(self):
        # Clear old widgets efficiently
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        
        # Clear stale image label references
        self.card_labels.clear()
        
        row = 0
        col = 0
        max_cols = 2
        
        # Only render up to _visible_count items
        items_to_show = self.filtered_skus[:self._visible_count]
        total_count = len(self.filtered_skus)
        showing_count = len(items_to_show)
        
        for sku in items_to_show:
            card = self.create_sku_card(sku)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        self.grid_layout.setRowStretch(row + 1, 1)
        
        # Update count label
        if total_count == 0:
            self.lbl_count.setText("No SKU data available — use Sync SKU to fetch")
        elif showing_count < total_count:
            self.lbl_count.setText(f"Showing {showing_count} of {total_count} items (scroll for more)")
        else:
            self.lbl_count.setText(f"{total_count} items")

    def create_sku_card(self, sku):
        card = QFrame()
        card_w = UIScaling.scale(200)
        card_h = UIScaling.scale(180)
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
        
        # Image placeholder (lazy loaded)
        img_label = QLabel()
        img_size = UIScaling.scale(100)
        img_label.setFixedSize(img_size, img_size)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("background-color: #EEEEEE; border-radius: 8px; color: #999;")
        img_label.setText("No Img")
        
        gdrive_id = sku.get("gdrive_id")
        if gdrive_id:
            img_label.setText("...")
            if gdrive_id not in self.card_labels:
                self.card_labels[gdrive_id] = []
            self.card_labels[gdrive_id].append(img_label)
            # Queue image load (image_loader handles caching and limiting)
            self.image_loader.load_image(gdrive_id)
            
        layout.addWidget(img_label)
        
        # Code label
        code_lbl = QLabel(sku.get("code", "UNKNOWN"))
        code_font_size = UIScaling.scale_font(16)
        code_lbl.setStyleSheet(f"font-size: {code_font_size}px; font-weight: bold; color: {self.theme['text_main']};")
        code_lbl.setAlignment(Qt.AlignCenter)
        code_lbl.setWordWrap(True)
        
        layout.addWidget(code_lbl)
        
        # Click handler — prevent double-click
        def on_click(event, s=sku):
            if self._selection_made:
                return
            self._selection_made = True
            self.sku_selected.emit(s)
            self.close_overlay()
            
        card.mousePressEvent = on_click
        card.setCursor(Qt.PointingHandCursor)
        
        return card

    def on_image_loaded(self, gdrive_id, pixmap):
        if gdrive_id in self.card_labels:
            for lbl in self.card_labels[gdrive_id]:
                try:
                    if lbl.isVisible():
                        scaled = pixmap.scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        lbl.setPixmap(scaled)
                        lbl.setText("")
                except (RuntimeError, AttributeError):
                    pass  # Widget was deleted or not accessible
