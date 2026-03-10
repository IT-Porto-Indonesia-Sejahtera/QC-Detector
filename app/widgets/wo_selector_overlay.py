from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QFrame, QGridLayout,
    QDateEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate
from app.widgets.base_overlay import BaseOverlay
from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling
from backend.get_wo_list import fetch_wo_list, get_machine_list


class WOSelectorOverlay(BaseOverlay):
    wo_selected = Signal(dict)

    def __init__(self, parent=None, wo_list=None, plant="EVA1", machine="Mesin 08"):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        self.wo_list = wo_list or []
        self.plant = plant
        self.machine = machine
        
        scaled_w = UIScaling.scale(600)
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
        
        self.init_ui()

    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("❮")
        btn_back_size = UIScaling.scale(40)
        btn_back.setFixedSize(btn_back_size, btn_back_size)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                border: none; 
                border-radius: {btn_back_size//2}px;
                font-size: {UIScaling.scale_font(20)}px; 
                font-weight: bold; 
                color: {self.theme['text_main']};
                background-color: {self.theme['bg_card']};
            }}
            QPushButton:hover {{ background-color: {self.theme['border']}; }}
        """)
        btn_back.clicked.connect(self.close_overlay)
        
        lbl_title = QLabel("Select TODAY's Work Order")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(18)}px; font-weight: bold; color: {self.theme['text_main']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        header.addWidget(btn_back)
        header.addStretch()
        header.addWidget(lbl_title)
        header.addStretch()
        header.addSpacing(btn_back_size)
        
        layout.addLayout(header)
        
        # Filters Row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        
        # Machine Dropdown
        self.machine_combo = QComboBox()
        self.machine_combo.setFixedHeight(UIScaling.scale(42))
        self.machine_combo.setStyleSheet(self._get_input_style())
        
        try:
            machines = get_machine_list()
        except Exception as e:
            print(f"[WOSelectorOverlay] Error fetching machine list: {e}")
            machines = ["Mesin 01", "Mesin 02", "Mesin 03", "Mesin 04", "Mesin 05",
                        "Mesin 06", "Mesin 07", "Mesin 08", "Mesin 09", "Mesin 10"]
        self.machine_combo.addItems(machines)
        
        # Set default to "Mesin 08" or previous selection
        default_machine = self.machine
        idx = self.machine_combo.findText(default_machine)
        if idx != -1:
            self.machine_combo.setCurrentIndex(idx)
        else:
            # Try to find "Mesin 08" if current machine not found
            idx_08 = self.machine_combo.findText("Mesin 08")
            if idx_08 != -1: self.machine_combo.setCurrentIndex(idx_08)
            
        filter_row.addWidget(self.machine_combo, 2)
        
        # Date Input
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setFixedHeight(UIScaling.scale(42))
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setStyleSheet(self._get_input_style() + "QDateEdit::drop-down { border:none; width: 30px; }")
        filter_row.addWidget(self.date_input, 1)
        
        # Refresh Button
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setFixedHeight(UIScaling.scale(42))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: {UIScaling.scale(8)}px;
                font-weight: 700;
                padding: 0 {UIScaling.scale(15)}px;
            }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
        """)
        self.btn_refresh.clicked.connect(self.re_fetch)
        filter_row.addWidget(self.btn_refresh)
        
        layout.addLayout(filter_row)
        
        # Search Filter (Existing)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Quick search in results...")
        self.search_input.setFixedHeight(UIScaling.scale(40))
        self.search_input.setStyleSheet(self._get_input_style())
        self.search_input.textChanged.connect(self.render_list)
        layout.addWidget(self.search_input)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.wo_layout = QVBoxLayout(self.scroll_content)
        self.wo_layout.setSpacing(UIScaling.scale(10))
        self.wo_layout.setContentsMargins(5, 5, 5, 5)
        
        self.render_list()
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

    def _get_input_style(self):
        return f"""
            QLineEdit, QDateEdit, QComboBox {{
                background-color: white;
                border: 1.5px solid {self.theme['border']};
                border-radius: {UIScaling.scale(8)}px;
                padding: 0 {UIScaling.scale(12)}px;
                font-size: {UIScaling.scale_font(13)}px;
                color: {self.theme['text_main']};
            }}
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{ border-color: #2563EB; }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 10px;
            }}
        """

    def re_fetch(self):
        """Fetch WOs with current filters."""
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("⌛ Loading...")
        
        machine = self.machine_combo.currentText().strip()
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        
        try:
            # Re-fetch from DB
            new_list = fetch_wo_list(self.plant, machine, target_date=date_str)
            self.wo_list = new_list
            self.render_list()
        except Exception as e:
            print(f"Error re-fetching: {e}")
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("🔄 Refresh")
    def render_list(self, query_text=None):
        # Clear
        while self.wo_layout.count():
            item = self.wo_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        query = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ""
        
        filtered_list = []
        if not query:
            filtered_list = self.wo_list
        else:
            for wo in self.wo_list:
                searchable = (
                    str(wo.get('nomor_wo', '')) + 
                    str(wo.get('shift', '')) + 
                    str(wo.get('machine', '')) + 
                    str(wo.get('list_product_code', ''))
                ).lower()
                if query in searchable:
                    filtered_list.append(wo)

        if not filtered_list:
            msg = "No Work Orders found." if not query else f"No matches for '{query}'"
            lbl = QLabel(msg + "\nAdjust filters or check connection.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #666; font-size: 14px; margin-top: 50px; border:none;")
            self.wo_layout.addWidget(lbl)
            return

        for wo in filtered_list:
            card = self.create_wo_card(wo)
            self.wo_layout.addWidget(card)
            
        self.wo_layout.addStretch()

    def create_wo_card(self, wo):
        card = QFrame()
        card.setFixedHeight(UIScaling.scale(100))
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['bg_card']};
                border-radius: {UIScaling.scale(12)}px;
                border: 1px solid {self.theme['border']};
            }}
            QFrame:hover {{
                border-color: #007AFF;
                background-color: #F0F7FF;
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        
        v_info = QVBoxLayout()
        v_info.setSpacing(2)
        
        wo_num = wo.get('nomor_wo', 'Unknown WO')
        lbl_num = QLabel(wo_num)
        lbl_num.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; font-weight: 800; color: #1C1C1E; border:none;")
        v_info.addWidget(lbl_num)
        
        shift = wo.get('shift', '')
        machine = wo.get('machine', '')
        lbl_sub = QLabel(f"Shift: {shift} | {machine}")
        lbl_sub.setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; color: #666; border:none;")
        v_info.addWidget(lbl_sub)

        # Notes Display
        notes = wo.get('notes', '')
        if notes:
            lbl_notes = QLabel(f"📝 {notes}")
            lbl_notes.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; color: #92400E; font-style: italic; border:none;")
            lbl_notes.setWordWrap(True)
            v_info.addWidget(lbl_notes)
        
        layout.addLayout(v_info, 1)
        
        # Product codes
        sku_codes = wo.get('list_product_code', '')
        lbl_skus = QLabel(sku_codes)
        lbl_skus.setWordWrap(True)
        lbl_skus.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; color: #007AFF; font-weight: 600; border:none;")
        lbl_skus.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(lbl_skus, 1)
        
        def on_click(event, w=wo):
            self.wo_selected.emit(w)
            self.close_overlay()
            
        card.mousePressEvent = on_click
        return card
