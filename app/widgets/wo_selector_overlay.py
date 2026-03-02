
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QLineEdit, QDateEdit, QScroller,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QDate, Signal, QSize, QEvent
from app.utils.ui_scaling import UIScaling
from app.utils.theme_manager import ThemeManager
from app.data.dummy_wo import DUMMY_WORK_ORDERS


class WOSelectorOverlay(QFrame):
    """Overlay for selecting a Work Order. Emits wo_selected(dict) signal."""
    wo_selected = Signal(dict)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = ThemeManager.get_colors()
        self.all_work_orders = list(DUMMY_WORK_ORDERS)
        self.setStyleSheet("background-color: rgba(10, 12, 18, 180);")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(20), UIScaling.scale(20), UIScaling.scale(20))

        # Content box
        self.content_box = QFrame()
        self.content_box.setStyleSheet(f"""
            QFrame {{
                background-color: #F9FAFB;
                border-radius: {UIScaling.scale(18)}px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(Qt.black)
        self.content_box.setGraphicsEffect(shadow)

        self.content_layout = QVBoxLayout(self.content_box)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.main_layout.addWidget(self.content_box)

        self.init_ui()

        if parent:
            self.resize(parent.size())
            self.update_content_size()
            self.show()
            self.raise_()
            parent.installEventFilter(self)

    def init_ui(self):
        # --- HEADER ---
        header = QFrame()
        header.setFixedHeight(UIScaling.scale(70))
        header.setStyleSheet(f"""
            background-color: white;
            border-top-left-radius: {UIScaling.scale(18)}px;
            border-top-right-radius: {UIScaling.scale(18)}px;
            border-bottom: 1.5px solid #E5E7EB;
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(UIScaling.scale(20), 0, UIScaling.scale(20), 0)

        btn_back = QPushButton("✕")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedSize(UIScaling.scale(44), UIScaling.scale(44))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #F3F4F6;
                border: none;
                border-radius: {UIScaling.scale(22)}px;
                font-size: {UIScaling.scale_font(18)}px;
                font-weight: 700;
                color: #6B7280;
            }}
            QPushButton:hover {{ background-color: #E5E7EB; color: #374151; }}
            QPushButton:pressed {{ background-color: #D1D5DB; }}
        """)
        btn_back.clicked.connect(self.close_overlay)
        h_layout.addWidget(btn_back)

        lbl_title = QLabel("📋  Pilih Work Order")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(20)}px; font-weight: 800; color: #111827;")
        lbl_title.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(lbl_title, 1)

        # Spacer
        spacer = QWidget()
        spacer.setFixedWidth(UIScaling.scale(44))
        h_layout.addWidget(spacer)

        self.content_layout.addWidget(header)

        # --- FILTER BAR ---
        filter_bar = QFrame()
        filter_bar.setFixedHeight(UIScaling.scale(65))
        filter_bar.setStyleSheet("background-color: white; border-bottom: 1.5px solid #E5E7EB;")
        f_layout = QHBoxLayout(filter_bar)
        f_layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(10), UIScaling.scale(20), UIScaling.scale(10))
        f_layout.setSpacing(UIScaling.scale(12))

        lbl_date = QLabel("Tanggal")
        lbl_date.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; font-weight: 600; color: #6B7280;")
        f_layout.addWidget(lbl_date)

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setCalendarPopup(True)
        self._style_date_edit(self.date_from)
        f_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.setCalendarPopup(True)
        self._style_date_edit(self.date_to)
        f_layout.addWidget(self.date_to)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search WO...")
        self.search_input.setFixedHeight(UIScaling.scale(42))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #F9FAFB;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(14)}px;
                font-size: {UIScaling.scale_font(14)}px;
                color: #374151;
            }}
            QLineEdit:focus {{ border-color: #2563EB; background-color: white; }}
        """)
        self.search_input.textChanged.connect(self.filter_list)
        f_layout.addWidget(self.search_input, 1)

        self.content_layout.addWidget(filter_bar)

        # --- WO LIST ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(16), UIScaling.scale(20), UIScaling.scale(16))
        self.list_layout.setSpacing(UIScaling.scale(10))

        scroll.setWidget(self.list_widget)
        self.content_layout.addWidget(scroll, 1)

        self.render_list(self.all_work_orders)

    def _style_date_edit(self, widget):
        widget.setFixedHeight(UIScaling.scale(42))
        widget.setFixedWidth(UIScaling.scale(140))
        widget.setStyleSheet(f"""
            QDateEdit {{
                background-color: #F9FAFB;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(10)}px;
                font-size: {UIScaling.scale_font(13)}px;
                color: #374151;
            }}
            QDateEdit:focus {{ border-color: #2563EB; }}
        """)

    def filter_list(self):
        query = self.search_input.text().strip().lower()
        filtered = [
            wo for wo in self.all_work_orders
            if not query or query in wo["wo_number"].lower() or query in wo.get("plant", "").lower()
            or query in wo.get("machine", "").lower()
        ]
        self.render_list(filtered)

    def render_list(self, work_orders):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for wo in work_orders:
            card = self._create_wo_card(wo)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _create_wo_card(self, wo):
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(UIScaling.scale(75))
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-left: {UIScaling.scale(5)}px solid #2563EB;
                border-radius: {UIScaling.scale(12)}px;
            }}
            QFrame:hover {{
                background-color: #EFF6FF;
                border-color: #93C5FD;
                border-left: {UIScaling.scale(5)}px solid #2563EB;
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(10), UIScaling.scale(20), UIScaling.scale(10))
        layout.setSpacing(UIScaling.scale(16))

        # WO number
        lbl_wo = QLabel(wo["wo_number"])
        lbl_wo.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; font-weight: 700; color: #111827; border: none;")
        layout.addWidget(lbl_wo, 1)

        # Machine badge
        machine = wo.get("machine", "")
        if machine:
            lbl_machine = QLabel(f"🏭 {machine}")
            lbl_machine.setStyleSheet(f"""
                font-size: {UIScaling.scale_font(12)}px;
                font-weight: 700;
                color: #4B5563;
                background-color: #F3F4F6;
                padding: {UIScaling.scale(4)}px {UIScaling.scale(10)}px;
                border-radius: {UIScaling.scale(6)}px;
                border: 1px solid #E5E7EB;
            """)
            layout.addWidget(lbl_machine)

        # Info labels
        lbl_plant = QLabel(wo.get("plant", ""))
        lbl_plant.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        layout.addWidget(lbl_plant)

        lbl_shift = QLabel(wo.get("shift", ""))
        lbl_shift.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        layout.addWidget(lbl_shift)

        lbl_date = QLabel(wo.get("production_date", ""))
        lbl_date.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        layout.addWidget(lbl_date)

        card.mousePressEvent = lambda e, w=wo: self._on_wo_clicked(w)
        return card

    def _on_wo_clicked(self, wo):
        self.wo_selected.emit(wo)
        self.close_overlay()

    def update_content_size(self):
        parent = self.parent()
        if not parent:
            return
        self.resize(parent.size())
        max_w = int(parent.size().width() * 0.7)
        max_h = int(parent.size().height() * 0.8)
        self.content_box.setMaximumSize(QSize(max_w, max_h))
        self.content_box.setMinimumSize(QSize(min(550, max_w), min(450, max_h)))

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.update_content_size()
        return super().eventFilter(obj, event)

    def close_overlay(self):
        self.closed.emit()
        self.setParent(None)
        self.deleteLater()
