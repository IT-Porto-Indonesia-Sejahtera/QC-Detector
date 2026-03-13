import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy, QScrollArea, QMessageBox, QTextEdit, QScroller,
    QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from app.widgets.sku_selector_overlay import SkuSelectorOverlay
from app.utils.image_loader import NetworkImageLoader
from app.data.record_manager import RecordManager
from backend.get_wo_list import fetch_wo_list, enrich_wo_with_sku
from app.widgets.wo_selector_overlay import WOSelectorOverlay

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")
SETTINGS_FILE = os.path.join("output", "settings", "app_settings.json")


class PresetDetailPage(QWidget):
    """Full-screen preset detail/editor page."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.current_profile = None
        self.sku_rows = []
        self.image_loader = NetworkImageLoader(self)
        self.image_loader.image_loaded.connect(self.on_image_loaded)
        self.card_labels = {}
        self._saved_snapshot = {}  # For unsaved changes detection
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

        lbl_title = QLabel("Detail Preset")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: 800; color: #1C1C1E;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        # Machine indicator
        self.lbl_machine = QLabel("")
        self.lbl_machine.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(13)}px;
            font-weight: 700;
            color: #4B5563;
            background-color: #F3F4F6;
            padding: {UIScaling.scale(6)}px {UIScaling.scale(16)}px;
            border-radius: {UIScaling.scale(8)}px;
            border: 1px solid #E5E7EB;
        """)
        h_layout.addWidget(self.lbl_machine)

        # Mulai QC button (moved from action bar to header)
        self.btn_start = QPushButton("▶  Mulai QC")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setFixedHeight(UIScaling.scale(48))
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: {UIScaling.scale(12)}px;
                padding: 0 {UIScaling.scale(28)}px;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
            QPushButton:pressed {{ background-color: #1E40AF; }}
        """)
        self.btn_start.clicked.connect(self.start_preset)
        h_layout.addWidget(self.btn_start)

        # Ukur button
        self.btn_ukur = QPushButton("▶  Buka Kamera QC")
        self.btn_ukur.setCursor(Qt.PointingHandCursor)
        self.btn_ukur.setFixedHeight(UIScaling.scale(48))
        self.btn_ukur.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: {UIScaling.scale(12)}px;
                padding: 0 {UIScaling.scale(28)}px;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
            QPushButton:pressed {{ background-color: #1E40AF; }}
        """)
        self.btn_ukur.clicked.connect(self.run_preset)
        h_layout.addWidget(self.btn_ukur)

        layout.addWidget(header)

        # ═══════════════════════════════════════
        # ACTION BAR
        # ═══════════════════════════════════════
        action_bar = QFrame()
        action_bar.setFixedHeight(UIScaling.scale(65))
        action_bar.setStyleSheet("background-color: #ECEEF2;")
        a_layout = QHBoxLayout(action_bar)
        a_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(10), UIScaling.scale(24), UIScaling.scale(10))
        a_layout.setSpacing(UIScaling.scale(12))

        # Action buttons with colors
        self.btn_save = self._make_action_btn("💾  Simpan", "#10B981", "white")
        self.btn_save.clicked.connect(self.save_preset)
        a_layout.addWidget(self.btn_save)

        self.btn_delete = self._make_action_btn("🗑  Hapus", "#EF4444", "white")
        self.btn_delete.clicked.connect(self.delete_preset)
        a_layout.addWidget(self.btn_delete)

        self.btn_finish = self._make_action_btn("✓  Validate", "#F59E0B", "white")
        self.btn_finish.clicked.connect(self.finish_preset)
        a_layout.addWidget(self.btn_finish)

        # Sync from WO button removed per user request

        a_layout.addStretch()

        # Status badge
        lbl_status_label = QLabel("Status WO:")
        lbl_status_label.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px; font-weight: 600; color: #6B7280;")
        a_layout.addWidget(lbl_status_label)

        self.lbl_status = QLabel("Draft")
        a_layout.addWidget(self.lbl_status)

        layout.addWidget(action_bar)

        # ═══════════════════════════════════════
        # MAIN CONTENT (Split: Left info + Right SKUs)
        # ═══════════════════════════════════════
        content = QWidget()
        c_layout = QHBoxLayout(content)
        c_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(16), UIScaling.scale(24), UIScaling.scale(24))
        c_layout.setSpacing(UIScaling.scale(20))

        # --- LEFT: WO Info ---
        left_frame = QFrame()
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(16)}px;
            }}
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(UIScaling.scale(28), UIScaling.scale(24), UIScaling.scale(28), UIScaling.scale(24))
        left_layout.setSpacing(UIScaling.scale(14))

        # WO header
        self.lbl_wo_header = QLabel("Informasi Work Order :")
        self.lbl_wo_header.setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; color: #9CA3AF; font-weight: 600; border: none; letter-spacing: 0.5px;")
        left_layout.addWidget(self.lbl_wo_header)

        self.lbl_wo_title = QLabel("")
        self.lbl_wo_title.setStyleSheet(f"font-size: {UIScaling.scale_font(22)}px; font-weight: 800; color: #111827; border: none;")
        self.lbl_wo_title.setWordWrap(True)
        left_layout.addWidget(self.lbl_wo_title)

        # Separator
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #E5E7EB; border: none;")
        left_layout.addWidget(line)

        # Info grid
        info_grid = QVBoxLayout()
        info_grid.setSpacing(10)

        self.info_plant = self._make_info_row("Plant", info_grid)
        self.info_shift = self._make_info_row("Shift", info_grid)
        self.info_date = self._make_info_row("Tanggal produksi", info_grid)
        self.info_mps = self._make_info_row("MPS", info_grid)

        left_layout.addLayout(info_grid)

        # Notes
        left_layout.addSpacing(8)
        lbl_notes = QLabel("Notes")
        lbl_notes.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; font-weight: 700; color: #6B7280; border: none;")
        left_layout.addWidget(lbl_notes)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Tambahkan catatan...")
        self.notes_input.setMinimumHeight(UIScaling.scale(110))
        self.notes_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: #F9FAFB;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(12)}px;
                padding: {UIScaling.scale(12)}px;
                font-size: {UIScaling.scale_font(14)}px;
                color: #374151;
            }}
            QTextEdit:focus {{ border-color: #2563EB; background-color: white; }}
        """)
        left_layout.addWidget(self.notes_input)
        
        # QC Results Section
        left_layout.addSpacing(UIScaling.scale(10))
        lbl_qc = QLabel("📊  Rangkuman Hasil QC")
        lbl_qc.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px; font-weight: 700; color: #1F2937; border: none;")
        left_layout.addWidget(lbl_qc)
        
        qc_frame = QFrame()
        qc_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F3F4F6;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(12)}px;
            }}
        """)
        qc_layout = QVBoxLayout(qc_frame)
        qc_layout.setContentsMargins(UIScaling.scale(16), UIScaling.scale(16), UIScaling.scale(16), UIScaling.scale(16))
        
        self.qc_grid = QGridLayout()
        self.qc_grid.setSpacing(UIScaling.scale(15))
        
        self.lbl_good = self._add_qc_stat("GOOD", "0", 0, 0)
        self.lbl_oven = self._add_qc_stat("OVEN", "0", 0, 1)
        self.lbl_bs = self._add_qc_stat("BS", "0", 1, 0)
        self.lbl_total = self._add_qc_stat("TOTAL", "0", 1, 1)
        
        qc_layout.addLayout(self.qc_grid)
        left_layout.addWidget(qc_frame)
        
        left_layout.addStretch()

        c_layout.addWidget(left_frame, 2)

        # --- RIGHT: SKU List ---
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(16)}px;
            }}
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # SKU Header
        sku_header = QFrame()
        sku_header.setFixedHeight(UIScaling.scale(56))
        sku_header.setStyleSheet(f"""
            background-color: #F9FAFB;
            border-bottom: 1px solid #E5E7EB;
            border-top-left-radius: {UIScaling.scale(16)}px;
            border-top-right-radius: {UIScaling.scale(16)}px;
        """)
        # Header
        right_header = QHBoxLayout()
        right_header.setContentsMargins(UIScaling.scale(20), 0, UIScaling.scale(20), 0)

        lbl_sku = QLabel("📦  Daftar Tipe yang Dikerjakan")
        lbl_sku.setStyleSheet(f"font-size: {UIScaling.scale_font(15)}px; font-weight: 700; color: #1F2937; border: none;")
        right_header.addWidget(lbl_sku)
        right_header.addStretch()
        sku_header.setLayout(right_header) # Set the layout for sku_header

        right_layout.addWidget(sku_header)

        # SKU Scroll Area
        sku_scroll = QScrollArea()
        sku_scroll.setWidgetResizable(True)
        sku_scroll.setFrameShape(QFrame.NoFrame)
        sku_scroll.setStyleSheet("background: transparent; border: none;")
        QScroller.grabGesture(sku_scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self.sku_container = QWidget()
        self.sku_container.setStyleSheet("background: transparent;")
        self.sku_layout = QVBoxLayout(self.sku_container)
        self.sku_layout.setContentsMargins(UIScaling.scale(14), UIScaling.scale(14), UIScaling.scale(14), UIScaling.scale(14))
        self.sku_layout.setSpacing(UIScaling.scale(12))

        sku_scroll.setWidget(self.sku_container)
        right_layout.addWidget(sku_scroll, 1)

        c_layout.addWidget(right_frame, 3)

        layout.addWidget(content, 1)

        # Toast
        self._toast_label = None
        self._toast_timer = None

    def _make_action_btn(self, text, bg_color, text_color):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(UIScaling.scale(44))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(20)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.7; }}
        """)
        return btn

    def _add_qc_stat(self, label, value, row, col):
        """Helper to add a stat box to the QC grid."""
        container = QVBoxLayout()
        container.setSpacing(2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; font-weight: 700; color: #6B7280; border: none;")
        container.addWidget(lbl)
        
        val = QLabel(value)
        val.setStyleSheet(f"font-size: {UIScaling.scale_font(20)}px; font-weight: 800; color: #111827; border: none;")
        container.addWidget(val)
        
        self.qc_grid.addLayout(container, row, col)
        return val

    def _make_info_row(self, label_text, parent_layout):
        row = QHBoxLayout()
        row.setSpacing(UIScaling.scale(16))

        lbl = QLabel(label_text)
        lbl.setFixedWidth(UIScaling.scale(140))
        lbl.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px; font-weight: 600; color: #6B7280; border: none;")
        row.addWidget(lbl)

        val = QLineEdit()
        val.setFixedHeight(UIScaling.scale(42))
        val.setStyleSheet(f"""
            QLineEdit {{
                background-color: #F3F4F6;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(14)}px;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 700;
                color: #111827;
            }}
            QLineEdit:read-only {{
                background-color: #F3F4F6;
                color: #000000;
                border: 2px solid #9CA3AF;
                font-weight: 400;
            }}
            QLineEdit:focus {{ border-color: #2563EB; background-color: white; }}
        """)
        row.addWidget(val, 1)

        parent_layout.addLayout(row)
        return val

    @staticmethod
    def _format_position(team_str):
        """Map team field values to display labels."""
        if not team_str:
            return ""
        t = team_str.strip()
        if "Kiri" in t or "Left" in t:
            return "Jalur Kiri"
        elif "Kanan" in t or "Right" in t:
            return "Jalur Kanan"
        return t

    def _get_status_style(self, color, bg_color):
        return f"""
            font-size: {UIScaling.scale_font(14)}px;
            font-weight: 800;
            color: {color};
            background-color: {bg_color};
            padding: {UIScaling.scale(6)}px {UIScaling.scale(18)}px;
            border: 2px solid {color};
            border-radius: {UIScaling.scale(10)}px;
            letter-spacing: 0.5px;
        """

    # ─── LOAD DATA ────────────────────────────────────────

    def load_profile(self, profile):
        self.current_profile = profile
        self.card_labels = {}

        status = profile.get("status", "draft")
        # Auto-migrate old statuses
        if status == "ready":
            status = "draft"
            profile["status"] = "draft"
        elif status == "active":
            status = "on_process"
            profile["status"] = "on_process"

        # Status badge styling (3 states only)
        # Status badge styling (3 states only)
        if status == "draft":
            self.lbl_status.setText("  Draft  ")
            self.lbl_status.setStyleSheet(self._get_status_style("#F59E0B", "#FEF3C7"))
            self.btn_start.setVisible(True)
            self.btn_finish.setVisible(False)
            self.btn_ukur.setVisible(False)
            self.btn_ukur.setEnabled(False)
        elif status == "on_process":
            self.lbl_status.setText("  On Process  ")
            self.lbl_status.setStyleSheet(self._get_status_style("#2563EB", "#DBEAFE"))
            self.btn_start.setVisible(False)
            self.btn_finish.setVisible(True)
            self.btn_ukur.setVisible(True)
            self.btn_ukur.setEnabled(True)
        else: # status == "done"
            self.lbl_status.setText("  Done  ")
            self.lbl_status.setStyleSheet(self._get_status_style("#6B7280", "#F3F4F6"))
            self.btn_start.setVisible(False)
            self.btn_finish.setVisible(False)
            self.btn_ukur.setVisible(False)
            self.btn_ukur.setEnabled(False)

        # WO info
        wo = profile.get("wo_number", profile.get("name", "Untitled"))
        machine = profile.get("machine", "")
        self.lbl_wo_title.setText(f"{wo} - {machine}" if machine else wo)
        self.lbl_machine.setText(f"🏭 {machine}" if machine else "")
        self.lbl_machine.setVisible(bool(machine))

        self.info_plant.setText(str(profile.get("plant") or ""))
        self.info_shift.setText(str(profile.get("shift") or ""))
        self.info_date.setText(str(profile.get("production_date") or ""))
        self.info_mps.setText(str(profile.get("nomor_mps") or profile.get("mps") or ""))
        self.notes_input.setPlainText(str(profile.get("notes") or ""))

        # Button visibility based on 3-status system
        is_editable = (status in ["draft", "on_process"])
        self.btn_save.setVisible(is_editable)
        self.btn_delete.setVisible(status != "on_process")
        # self.btn_start.setVisible(status == "draft") # Handled by new status logic
        # self.btn_finish.setVisible(status == "on_process") # Handled by new status logic
        # self.btn_ukur.setVisible(status == "on_process") # Handled by new status logic
        # self.btn_resync.setVisible(is_editable)

        # Disable editing for detail fields (always read-only as requested)
        # Use high contrast black color
        readonly_style = f"""
            QLineEdit {{
                background-color: #F3F4F6;
                border: 1.5px solid #D1D5DB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(14)}px;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 400;
                color: #000000;
            }}
        """
        for field in [self.info_plant, self.info_shift, self.info_date, self.info_mps]:
            field.setReadOnly(True)
            field.setStyleSheet(readonly_style)
            
        self.notes_input.setReadOnly(True)
        self.notes_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: #F3F4F6;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(12)}px;
                padding: {UIScaling.scale(12)}px;
                font-size: {UIScaling.scale_font(14)}px;
                color: #000000;
            }}
        """)

        # Load QC counts if available
        from app.data.record_manager import RecordManager
        record = RecordManager.get_record_by_preset_id(profile.get("id"))
        if record and "counts" in record:
            c = record["counts"]
            good = c.get("TOTAL GOOD", 0)
            # Aggregate Oven 1 + Oven 2 or use TOTAL OVEN if exists
            oven = c.get("TOTAL OVEN", c.get("OVEN 1", 0) + c.get("OVEN 2", 0))
            bs = c.get("TOTAL BS", 0)
            total = good + oven + bs
            
            self.lbl_good.setText(str(good))
            self.lbl_oven.setText(str(oven))
            self.lbl_bs.setText(str(bs))
            self.lbl_total.setText(str(total))
        else:
            self.lbl_good.setText("0")
            self.lbl_oven.setText("0")
            self.lbl_bs.setText("0")
            self.lbl_total.setText("0")

        self._render_sku_rows(profile, is_editable)

        # Snapshot for unsaved changes detection
        self._saved_snapshot = self._take_snapshot()

    def _render_sku_rows(self, profile, is_editable):
        while self.sku_layout.count():
            item = self.sku_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.sku_rows = []
        selected_skus = profile.get("selected_skus", [])

        num_rows = max(4, len(selected_skus))
        colors = ["#2563EB", "#DC2626", "#7C3AED", "#F59E0B"]
        for i in range(num_rows):
            data = selected_skus[i] if i < len(selected_skus) else None
            accent = colors[i % len(colors)]
            row = self._create_sku_row(i, data, is_editable, accent)
            self.sku_layout.addWidget(row)

        self.sku_layout.addStretch()

    def _create_sku_row(self, index, data, is_editable, accent_color):
        container = QFrame()
        container.setFixedHeight(UIScaling.scale(82))
        if is_editable:
            container.setCursor(Qt.PointingHandCursor)

        container.setStyleSheet(f"""
            QFrame {{
                background-color: #FAFAFA;
                border: 1.5px solid #E5E7EB;
                border-left: {UIScaling.scale(5)}px solid {accent_color};
                border-radius: {UIScaling.scale(14)}px;
            }}
            QFrame:hover {{
                border-color: {accent_color if is_editable else '#E5E7EB'};
                border-left: {UIScaling.scale(5)}px solid {accent_color};
                background-color: {'#F5F7FF' if is_editable else '#FAFAFA'};
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # SKU Image
        img_label = QLabel()
        img_size = UIScaling.scale(58)
        img_label.setFixedSize(img_size, img_size)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet(f"""
            background-color: #F3F4F6;
            border-radius: {UIScaling.scale(12)}px;
            color: #9CA3AF;
            border: 1.5px solid #E5E7EB;
            font-size: {UIScaling.scale_font(14)}px;
            font-weight: 600;
        """)
        img_label.setText("?")
        layout.addWidget(img_label)

        # SKU Name & Height
        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        
        sku_name = QLabel()
        sku_height = QLabel()
        
        if data:
            code = data.get("code", data.get("product_code", "Unknown"))
            display_name = data.get("Nama Produk", code)
            sku_name.setText(display_name)
            sku_name.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; font-weight: 700; color: #111827; border: none;")

            # Check for height in product data (centralized from get_product_sku)
            height = data.get("Master Height", 0)
            if height:
                sku_height.setText(f"Tinggi Master: {height} mm")
                sku_height.setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; font-weight: 600; color: #059669; border: none;")
            else:
                sku_height.setText("Tinggi Master Belum Diatur (Gunakan Standar)")
                sku_height.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; color: #9CA3AF; border: none;")

            gdrive_id = data.get("gdrive_id") or data.get("GDrive ID") or ""
            if gdrive_id:
                if gdrive_id not in self.card_labels:
                    self.card_labels[gdrive_id] = []
                self.card_labels[gdrive_id].append(img_label)
                self.image_loader.load_image(gdrive_id)
        else:
            sku_name.setText("← Pilih Tipe" if is_editable else "Kosong")
            sku_name.setStyleSheet(f"font-size: {UIScaling.scale_font(15)}px; font-weight: 500; color: #9CA3AF; border: none;")
            sku_height.setText("")

        info_vbox.addWidget(sku_name)
        info_vbox.addWidget(sku_height)
        layout.addLayout(info_vbox, 1)

        # Position button (clickable to toggle)
        raw_position = data.get("team", "") if data else ""
        position = self._format_position(raw_position)
        
        btn_pos = QPushButton(position)
        btn_pos.setCursor(Qt.PointingHandCursor)
        btn_pos.setFixedHeight(UIScaling.scale(42))
        
        update_pos_style = lambda text: self._apply_pos_btn_style(btn_pos, text)
        update_pos_style(position)
        
        if is_editable:
            btn_pos.clicked.connect(lambda _, idx=index: self._toggle_sku_position(idx))
        else:
            btn_pos.setCursor(Qt.ArrowCursor)

        layout.addWidget(btn_pos)

        # Reset button removed per user request

        row_data = {
            "img": img_label,
            "name": sku_name,
            "height": sku_height,
            "pos_btn": btn_pos,
            "data": data,
        }
        self.sku_rows.append(row_data)

        if is_editable:
            container.mousePressEvent = lambda e, idx=index: self.select_sku(idx)

        return container

    # reset_sku_report method removed per user request

    def _toggle_sku_position(self, index):
        """Toggle position between Kiri and Kanan for a selected SKU."""
        if index < 0 or index >= len(self.sku_rows):
            return
            
        row = self.sku_rows[index]
        data = row["data"]
        if not data:
            return
            
        current_team = data.get("team", "").lower()
        if "kiri" in current_team or "left" in current_team:
            new_team = "Kanan"
        else:
            new_team = "Kiri"
            
        data["team"] = new_team
        
        # Update UI
        display_pos = self._format_position(new_team)
        row["pos_btn"].setText(display_pos)
        
        self._apply_pos_btn_style(row["pos_btn"], display_pos)

    def _apply_pos_btn_style(self, btn, text):
        """Apply consistent styling to position buttons."""
        if not text:
            btn.setStyleSheet("border: none; background: transparent;")
            return

        if "Jalur Kiri" in text:
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {UIScaling.scale_font(13)}px;
                    font-weight: 700;
                    color: #1E40AF;
                    background-color: #DBEAFE;
                    padding: 0 {UIScaling.scale(14)}px;
                    border-radius: {UIScaling.scale(8)}px;
                    border: 1.5px solid #93C5FD;
                }}
                QPushButton:hover {{ background-color: #BFDBFE; }}
            """)
        elif "Jalur Kanan" in text:
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {UIScaling.scale_font(13)}px;
                    font-weight: 700;
                    color: #9A3412;
                    background-color: #FFF7ED;
                    padding: 0 {UIScaling.scale(14)}px;
                    border-radius: {UIScaling.scale(8)}px;
                    border: 1.5px solid #FDBA74;
                }}
                QPushButton:hover {{ background-color: #FFEDD5; }}
            """)
        else:
            btn.setStyleSheet("border: none; background: transparent;")

    # ─── SKU SELECTION ────────────────────────────────────

    def select_sku(self, index):
        self.pending_sku_index = index
        overlay = SkuSelectorOverlay(self.window())
        overlay.sku_selected.connect(self.on_sku_selected)

    def on_sku_selected(self, sku_data):
        idx = getattr(self, 'pending_sku_index', -1)
        if idx < 0 or idx >= len(self.sku_rows):
            return
        if not sku_data:
            return

        row = self.sku_rows[idx]
        row["data"] = sku_data

        display_name = sku_data.get("Nama Produk", sku_data.get("code", ""))
        row["name"].setText(display_name)
        row["name"].setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; font-weight: 700; color: #111827; border: none;")

        # Update Position
        if not sku_data.get("team"):
            sku_data["team"] = "Kiri" # Default
        
        display_pos = self._format_position(sku_data["team"])
        row["pos_btn"].setText(display_pos)
        self._apply_pos_btn_style(row["pos_btn"], display_pos)

        # Update Height
        height = sku_data.get("Master Height", 0)
        if height:
            row["height"].setText(f"Tinggi Master: {height} mm")
            row["height"].setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; font-weight: 600; color: #059669; border: none;")
        else:
            row["height"].setText("Tinggi Master Belum Diatur (Gunakan Standar)")
            row["height"].setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; color: #9CA3AF; border: none;")

        gdrive_id = sku_data.get("gdrive_id", "")
        if gdrive_id:
            row["img"].setText("...")
            if gdrive_id not in self.card_labels:
                self.card_labels[gdrive_id] = []
            self.card_labels[gdrive_id].append(row["img"])
            self.image_loader.load_image(gdrive_id)

    def on_image_loaded(self, gdrive_id, pixmap):
        if gdrive_id in self.card_labels:
            for lbl in self.card_labels[gdrive_id]:
                try:
                    scaled = pixmap.scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    lbl.setPixmap(scaled)
                    lbl.setText("")
                except RuntimeError:
                    pass

    # Sync from WO removed per user request

    # ─── ACTIONS ──────────────────────────────────────────

    def _parse_sizes(self, size_str, code=""):
        if not size_str:
            return ["36", "37", "38", "39", "40", "41", "42", "43", "44"]

        s = str(size_str).strip().upper()

        if "," in s:
            raw_items = [x.strip() for x in s.split(",") if x.strip()]
            
            # Identify all integers for context checks
            ints = []
            for item in raw_items:
                if item.isdigit():
                    ints.append(int(item))

            result = []
            for item in raw_items:
                if item.isdigit():
                    val = int(item)
                    # Smart Pairing Rule:
                    # 1. Partner (val-1) is missing
                    # 2. Next Neighbor (val+1) is also missing (not part of a contiguous list)
                    if val % 2 == 0 and (val-1) not in ints and (val+1) not in ints:
                        result.append(f"{val-1}/{val}")
                    else:
                        result.append(item)
                else:
                    # Already slashed or non-numeric
                    result.append(item)
            return result

        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2:
                start_s, end_s = parts[0].strip(), parts[1].strip()
                if start_s.isdigit() and end_s.isdigit():
                    start, end = int(start_s), int(end_s)
                    if start < end:
                        res = []
                        curr = start
                        while curr <= end:
                            if curr % 2 != 0 and curr + 1 <= end:
                                res.append(f"{curr}/{curr+1}")
                                curr += 2
                            else:
                                if curr % 2 == 0:
                                    res.append(f"{curr-1}/{curr}")
                                else:
                                    res.append(str(curr))
                                curr += 1
                        return res

        # Lone even number fallback
        if s.isdigit():
            val = int(s)
            if val % 2 == 0:
                return [f"{val-1}/{val}"]

        return [s]

    def _take_snapshot(self):
        """Capture current UI state for unsaved changes detection."""
        return {
            "notes": self.notes_input.toPlainText().strip(),
            "plant": self.info_plant.text().strip(),
            "shift": self.info_shift.text().strip(),
            "date": self.info_date.text().strip(),
            "mps": self.info_mps.text().strip(),
            "skus": [r["data"].get("code", "") if r["data"] else "" for r in self.sku_rows],
        }

    def _has_unsaved_changes(self):
        """Check if current UI state differs from the last saved snapshot."""
        if not self._saved_snapshot:
            return False
        return self._take_snapshot() != self._saved_snapshot

    def save_preset(self):
        if not self.current_profile:
            return

        # Show confirmation if on_process
        if self.current_profile.get("status") == "on_process":
            confirm = QMessageBox.question(
                self, "Konfirmasi Simpan",
                "Preset sedang berjalan (On Process). Apakah Anda yakin ingin menyimpan perubahan?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.No:
                return

        try:
            all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except:
            all_profiles = []

        self.current_profile["plant"] = self.info_plant.text().strip()
        self.current_profile["shift"] = self.info_shift.text().strip()
        self.current_profile["production_date"] = self.info_date.text().strip()
        self.current_profile["mps"] = self.info_mps.text().strip()
        self.current_profile["notes"] = self.notes_input.toPlainText().strip()
        self.current_profile["last_updated"] = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

        # Draft stays Draft on save — status only changes via Start/Finish

        presets = []
        selected_skus = []
        for idx, row in enumerate(self.sku_rows):
            data = row["data"]
            if data:
                data = data.copy()
                code = data.get("code") or data.get("Nama Produk") or "UNKNOWN"
                team = data.get("team", "")
                otorisasi = data.get("otorisasi", 0)
                product_id = data.get("id")
                selected_skus.append(data)

                sizes = self._parse_sizes(data.get("sizes", ""), code)
                for s in sizes:
                    display_val = str(s).strip()
                    calc_size = display_val # Default
                    
                    if "/" in display_val:
                        parts = display_val.split("/")
                        if len(parts) == 2 and parts[1].strip().isdigit():
                            calc_size = parts[1].strip()
                    
                    presets.append({
                        "sku": code,
                        "product_id": product_id,
                        "size": calc_size,
                        "display_size": display_val,
                        "color_idx": (idx % 4) + 1,
                        "team": team,
                        "otorisasi": otorisasi
                    })

        self.current_profile["presets"] = presets
        self.current_profile["selected_skus"] = selected_skus

        wo = self.current_profile.get("wo_number", "")
        machine = self.current_profile.get("machine", "")
        if wo:
            self.current_profile["name"] = f"{wo} - {machine}" if machine else wo

        found = False
        for i, p in enumerate(all_profiles):
            if p.get("id") == self.current_profile.get("id"):
                all_profiles[i] = self.current_profile
                found = True
                break
        if not found:
            all_profiles.append(self.current_profile)

        JsonUtility.save_to_json(PROFILES_FILE, all_profiles)
        self.load_profile(self.current_profile)
        self._saved_snapshot = self._take_snapshot()  # Reset snapshot after save
        self._show_toast("✓ Preset tersimpan!")

    def start_preset(self):
        """Start this preset — enforces single on_process rule."""
        if not self.current_profile:
            return

        try:
            all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except:
            all_profiles = []

        # Check if another preset is already on_process
        for p in all_profiles:
            if p.get("status") in ("on_process", "active") and p.get("id") != self.current_profile.get("id"):
                wo = p.get("wo_number", p.get("name", ""))
                msg = QMessageBox(self)
                msg.setWindowTitle("Preset Sedang Berjalan")
                msg.setText(f"Preset '{wo}' masih berjalan.\nSelesaikan preset tersebut terlebih dahulu.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet("""
                    QMessageBox { background-color: white; }
                    QMessageBox QLabel { color: #333; font-size: 15px; padding: 12px; }
                    QPushButton {
                        background-color: #2563EB; color: white;
                        border: none; border-radius: 8px;
                        padding: 8px 24px; font-size: 14px; margin: 5px; font-weight: 600;
                    }
                    QPushButton:hover { background-color: #1D4ED8; }
                """)
                msg.exec()
                return

        # Save first, then set to on_process
        self.save_preset()

        try:
            all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except:
            all_profiles = []

        for p in all_profiles:
            if p.get("id") == self.current_profile.get("id"):
                p["status"] = "on_process"

        self.current_profile["status"] = "on_process"
        JsonUtility.save_to_json(PROFILES_FILE, all_profiles)

        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = self.current_profile["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)

        self.load_profile(self.current_profile)
        
        # Directly open camera after starting
        self.run_preset()

    def finish_preset(self):
        if not self.current_profile:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Selesaikan Preset")
        msg.setText("Selesaikan preset ini?\nPreset akan dipindahkan ke Report.")
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
        if msg.exec() != QMessageBox.Yes:
            return

        self.current_profile["status"] = "done"

        # Finalize the record (set finished_at)
        RecordManager.finalize_record(self.current_profile.get("id"))

        try:
            all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
            for i, p in enumerate(all_profiles):
                if p.get("id") == self.current_profile.get("id"):
                    all_profiles[i]["status"] = "done"
                    break
            JsonUtility.save_to_json(PROFILES_FILE, all_profiles)
        except:
            pass

        self.load_profile(self.current_profile)
        self._show_toast("✓ Preset selesai! Dipindahkan ke Report.")

        # Navigate back to list after a short delay
        QTimer.singleShot(1000, self.go_back)

    def delete_preset(self):
        if not self.current_profile:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Preset")
        wo = self.current_profile.get("wo_number", self.current_profile.get("name", ""))
        msg.setText(f"Hapus preset '{wo}'?")
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
            try:
                all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
                all_profiles = [p for p in all_profiles if p.get("id") != self.current_profile.get("id")]
                JsonUtility.save_to_json(PROFILES_FILE, all_profiles)
            except:
                pass
            self.go_back()

    def run_preset(self):
        """Run measurement — only works if preset is on_process."""
        if self.current_profile.get("status") != "on_process":
            self._show_toast("Preset harus dalam status 'On Process' untuk diukur.", is_error=True)
            return
        if self.controller:
            self.controller.go_to_live()

    def go_back(self):
        # Check for unsaved changes
        if self.current_profile and self.current_profile.get("status") == "draft" and self._has_unsaved_changes():
            msg = QMessageBox(self)
            msg.setWindowTitle("Perubahan Belum Disimpan")
            msg.setText("Ada perubahan yang belum disimpan.\nIngin menyimpan perubahan ini sebelum kembali?")
            msg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            msg.button(QMessageBox.Save).setText("Simpan")
            msg.button(QMessageBox.Discard).setText("Jangan Simpan")
            msg.button(QMessageBox.Cancel).setText("Batal")
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
            result = msg.exec()
            if result == QMessageBox.Save:
                self.save_preset()
            elif result == QMessageBox.Cancel:
                return
            # Discard → just navigate back without saving
            # Since we removed the initial save in preset_list_page, 
            # navigating back here will naturally discard the new profile.

        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Kembali")
            msg.setText("Apakah Anda yakin ingin ke halaman sebelumnya?")
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
            if msg.exec() != QMessageBox.Yes:
                return

        if self.controller:
            self.controller.go_to_profiles()

    # ─── TOAST ────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._toast_label and self._toast_label.isVisible():
            toast_w = min(UIScaling.scale(400), self.width() - UIScaling.scale(60))
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
        toast_w = min(UIScaling.scale(400), self.width() - UIScaling.scale(60))
        self._toast_label.setFixedWidth(toast_w)
        self._toast_label.move((self.width() - toast_w) // 2, UIScaling.scale(145))
        self._toast_label.show()
        self._toast_label.raise_()
        self._toast_timer.start(2500)
