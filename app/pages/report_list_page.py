import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QScrollArea, QMessageBox, QDateEdit, QScroller
)
from PySide6.QtCore import Qt, QDate, QTimer

from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling
from app.data.record_manager import RecordManager


class ReportListPage(QWidget):
    """Full-screen report list page showing completed preset records."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.records = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #ECEEF2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ═══════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════
        header = QFrame()
        header.setFixedHeight(UIScaling.scale(70))
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #D8D8D8;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(UIScaling.scale(20), 0, UIScaling.scale(20), 0)
        h_layout.setSpacing(UIScaling.scale(14))

        btn_back = QPushButton("❮")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedSize(UIScaling.scale(48), UIScaling.scale(48))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F0F5;
                border: none;
                border-radius: {UIScaling.scale(24)}px;
                font-size: {UIScaling.scale_font(20)}px;
                font-weight: 700;
                color: #333;
            }}
            QPushButton:hover {{ background-color: #E0E0E5; }}
            QPushButton:pressed {{ background-color: #D0D0D5; }}
        """)
        btn_back.clicked.connect(self.go_back)
        h_layout.addWidget(btn_back)

        lbl_title = QLabel("Report")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: 800; color: #1C1C1E;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        layout.addWidget(header)

        # ═══════════════════════════════════════
        # FILTER BAR
        # ═══════════════════════════════════════
        filter_bar = QFrame()
        filter_bar.setFixedHeight(UIScaling.scale(65))
        filter_bar.setStyleSheet("background-color: #ECEEF2;")
        f_layout = QHBoxLayout(filter_bar)
        f_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(10), UIScaling.scale(24), UIScaling.scale(10))
        f_layout.setSpacing(UIScaling.scale(12))

        lbl_tgl = QLabel("Tanggal")
        lbl_tgl.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; font-weight: 600; color: #666;")
        f_layout.addWidget(lbl_tgl)

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setCalendarPopup(True)
        self._style_filter_date(self.date_from)
        f_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.setCalendarPopup(True)
        self._style_filter_date(self.date_to)
        f_layout.addWidget(self.date_to)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search report...")
        self.search_input.setFixedHeight(UIScaling.scale(44))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(16)}px;
                font-size: {UIScaling.scale_font(14)}px;
                color: #333;
            }}
            QLineEdit:focus {{ border-color: #2563EB; background-color: white; }}
        """)
        self.search_input.textChanged.connect(self.filter_list)
        f_layout.addWidget(self.search_input, 1)

        layout.addWidget(filter_bar)

        # ═══════════════════════════════════════
        # SCROLLABLE LIST
        # ═══════════════════════════════════════
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(16), UIScaling.scale(24), UIScaling.scale(24))
        self.list_layout.setSpacing(UIScaling.scale(12))

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll, 1)

        # Toast
        self._toast_label = None
        self._toast_timer = None

    def _style_filter_date(self, widget):
        widget.setFixedHeight(UIScaling.scale(44))
        widget.setFixedWidth(UIScaling.scale(140))
        widget.setStyleSheet(f"""
            QDateEdit {{
                background-color: white;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(10)}px;
                font-size: {UIScaling.scale_font(13)}px;
                color: #333;
            }}
            QDateEdit:focus {{ border-color: #2563EB; }}
        """)

    # ─── DATA ─────────────────────────────────────────────

    def load_records(self):
        self.records = RecordManager.get_all_records()
        self.render_list()

    def refresh_data(self):
        self.load_records()

    # ─── FILTER ───────────────────────────────────────────

    def filter_list(self):
        self.render_list()

    def _matches_filters(self, record):
        query = self.search_input.text().strip().lower()
        if query:
            searchable = (
                record.get("wo_number", "") +
                record.get("machine", "") +
                record.get("plant", "") +
                record.get("shift", "")
            ).lower()
            if query not in searchable:
                return False
        return True

    # ─── RENDER ───────────────────────────────────────────

    def render_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.records:
            lbl_empty = QLabel("Belum ada report")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; color: #9CA3AF; padding: {UIScaling.scale(40)}px;")
            self.list_layout.addWidget(lbl_empty)
        else:
            for record in self.records:
                if not self._matches_filters(record):
                    continue
                card = self._create_record_card(record)
                self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _create_record_card(self, record):
        status = record.get("status", "active")

        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(UIScaling.scale(100))

        # Color based on status
        if status == "done":
            accent = "#10B981"
            bg = "white"
            border = "#E5E7EB"
        else:
            accent = "#2563EB"
            bg = "#EFF6FF"
            border = "#93C5FD"

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-left: {UIScaling.scale(6)}px solid {accent};
                border-radius: {UIScaling.scale(14)}px;
            }}
            QFrame:hover {{
                border-color: {accent};
                border-left: {UIScaling.scale(6)}px solid {accent};
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(12), UIScaling.scale(20), UIScaling.scale(12))
        layout.setSpacing(UIScaling.scale(16))

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(UIScaling.scale(6))

        wo = record.get("wo_number", "Unknown")
        machine = record.get("machine", "")
        title_text = f"{wo} - {machine}" if machine else wo

        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(17)}px; font-weight: 700; color: #111827; border: none;")
        info_layout.addWidget(lbl_title)

        plant = record.get("plant", "")
        shift = record.get("shift", "")
        date = record.get("production_date", "")
        subtitle_parts = [p for p in [plant, shift, date] if p]
        subtitle = "    ·    ".join(subtitle_parts)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        info_layout.addWidget(lbl_sub)

        layout.addLayout(info_layout, 1)

        # Summary counts (compact)
        counts = record.get("counts", {})
        total_good = counts.get("TOTAL GOOD", 0)
        total_bs = counts.get("TOTAL BS", 0)
        oven = counts.get("OVEN 1", 0) + counts.get("OVEN 2", 0)
        total = total_good + total_bs + oven

        if total > 0:
            summary_layout = QHBoxLayout()
            summary_layout.setSpacing(UIScaling.scale(6))

            for val, label, color in [(total_good, "G", "#10B981"), (oven, "O", "#F59E0B"), (total_bs, "BS", "#EF4444")]:
                if val > 0:
                    lbl = QLabel(f"{val}")
                    lbl.setAlignment(Qt.AlignCenter)
                    lbl.setFixedSize(UIScaling.scale(44), UIScaling.scale(36))
                    lbl.setStyleSheet(f"""
                        font-size: {UIScaling.scale_font(14)}px;
                        font-weight: 800;
                        color: white;
                        background-color: {color};
                        border-radius: {UIScaling.scale(8)}px;
                        border: none;
                    """)
                    summary_layout.addWidget(lbl)

            layout.addLayout(summary_layout)

        # Delete button
        btn_del = QPushButton("🗑")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFixedSize(UIScaling.scale(44), UIScaling.scale(44))
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEE2E2;
                border: 1px solid #FECACA;
                font-size: {UIScaling.scale_font(18)}px;
                border-radius: {UIScaling.scale(10)}px;
            }}
            QPushButton:hover {{ background-color: #FECACA; border-color: #F87171; }}
            QPushButton:pressed {{ background-color: #FCA5A5; }}
        """)
        btn_del.clicked.connect(lambda _, r=record: self.delete_record(r))
        layout.addWidget(btn_del)

        card.mousePressEvent = lambda e, r=record: self._on_card_click(r, e)
        return card

    def _on_card_click(self, record, event):
        if self.controller:
            self.controller.go_to_report_detail(record)

    # ─── ACTIONS ──────────────────────────────────────────

    def delete_record(self, record):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Report")
        msg.setText(f"Hapus report '{record.get('wo_number', '')}'?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: white; }
            QMessageBox QLabel { color: #333; font-size: 15px; padding: 12px; }
            QPushButton {
                background-color: #F3F4F6; color: #333;
                border: 1px solid #D1D5DB; border-radius: 8px;
                padding: 8px 24px; font-size: 14px; margin: 5px; font-weight: 600;
            }
            QPushButton:hover { background-color: #E5E7EB; }
        """)
        if msg.exec() == QMessageBox.Yes:
            RecordManager.delete_record(record.get("id"))
            self.load_records()
            self._show_toast("✓ Report dihapus")

    def go_back(self):
        if self.controller:
            self.controller.go_back()

    # ─── TOAST ────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._toast_label and self._toast_label.isVisible():
            toast_w = min(UIScaling.scale(500), self.width() - UIScaling.scale(60))
            self._toast_label.setFixedWidth(toast_w)
            self._toast_label.move((self.width() - toast_w) // 2, UIScaling.scale(145))

    def _show_toast(self, message, is_error=False):
        if not self._toast_label:
            self._toast_label = QLabel(self)
            self._toast_label.setAlignment(Qt.AlignCenter)
            self._toast_label.setFixedHeight(UIScaling.scale(50))
            self._toast_label.hide()
            self._toast_timer = QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(lambda: self._toast_label.hide())

        bg = "#FEF2F2" if is_error else "#F0FDF4"
        border = "#FCA5A5" if is_error else "#86EFAC"
        color = "#DC2626" if is_error else "#16A34A"

        self._toast_label.setText(message)
        self._toast_label.setStyleSheet(f"""
            background-color: {bg}; color: {color};
            border: 2px solid {border}; border-radius: {UIScaling.scale(12)}px;
            font-weight: 700; font-size: {UIScaling.scale_font(15)}px; padding: 0 {UIScaling.scale(24)}px;
        """)
        toast_w = min(UIScaling.scale(500), self.width() - UIScaling.scale(60))
        self._toast_label.setFixedWidth(toast_w)
        self._toast_label.move((self.width() - toast_w) // 2, UIScaling.scale(145))
        self._toast_label.show()
        self._toast_label.raise_()
        self._toast_timer.start(2500)
