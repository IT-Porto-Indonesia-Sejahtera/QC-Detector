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

        # Ukur button
        self.btn_ukur = QPushButton("▶  Ukur")
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

        self.btn_activate = self._make_action_btn("⚡ Aktifkan", "#2563EB", "white")
        self.btn_activate.clicked.connect(self.activate_preset)
        a_layout.addWidget(self.btn_activate)

        self.btn_finish = self._make_action_btn("✓  Selesai", "#F59E0B", "white")
        self.btn_finish.clicked.connect(self.finish_preset)
        a_layout.addWidget(self.btn_finish)

        self.btn_resync = self._make_action_btn("🔄  Sync from WO", "white", "#2563EB")
        self.btn_resync.setStyleSheet(self.btn_resync.styleSheet() + f"border: 1.5px solid #2563EB; border-radius: {UIScaling.scale(10)}px;")
        self.btn_resync.clicked.connect(self.re_sync_wo)
        a_layout.addWidget(self.btn_resync)

        a_layout.addStretch()

        # Status badge
        lbl_status_label = QLabel("Status")
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
        self.lbl_wo_header = QLabel("Presets dari WO :")
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
        lbl_qc = QLabel("📊  QC Summary")
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
        sh_layout = QHBoxLayout(sku_header)
        sh_layout.setContentsMargins(UIScaling.scale(20), 0, UIScaling.scale(20), 0)

        lbl_sku_title = QLabel("📦  SKU Configuration")
        lbl_sku_title.setStyleSheet(f"font-size: {UIScaling.scale_font(15)}px; font-weight: 700; color: #1F2937; border: none;")
        sh_layout.addWidget(lbl_sku_title)

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
            return "Meja Kiri"
        elif "Kanan" in t or "Right" in t:
            return "Meja Kanan"
        return t

        return t
    # ─── LOAD DATA ────────────────────────────────────────

    def load_profile(self, profile):
        self.current_profile = profile
        self.card_labels = {}

        status = profile.get("status", "draft")

        # Status badge styling
        status_display = {
            "draft":  ("Draft",  "#92400E", "#FEF3C7", "#FCD34D"),
            "ready":  ("Ready",  "#065F46", "#ECFDF5", "#A7F3D0"),
            "active": ("Active", "#1E40AF", "#DBEAFE", "#93C5FD"),
            "done":   ("Done",   "#6B7280", "#F3F4F6", "#D1D5DB"),
        }
        disp = status_display.get(status, status_display["draft"])
        self.lbl_status.setText(disp[0])
        self.lbl_status.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(14)}px;
            font-weight: 800;
            color: {disp[1]};
            background-color: {disp[2]};
            padding: {UIScaling.scale(6)}px {UIScaling.scale(18)}px;
            border: 2px solid {disp[3]};
            border-radius: {UIScaling.scale(10)}px;
            letter-spacing: 0.5px;
        """)

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

        # Button visibility based on status
        is_editable = status in ("draft", "ready")
        self.btn_save.setVisible(is_editable)
        self.btn_delete.setVisible(status != "active")
        self.btn_activate.setVisible(status == "ready")
        self.btn_finish.setVisible(status == "active")
        self.btn_ukur.setVisible(status in ("ready", "active"))
        self.btn_resync.setVisible(is_editable)

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
                sku_height.setText(f"Master Height: {height} mm")
                sku_height.setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; font-weight: 600; color: #059669; border: none;")
            else:
                sku_height.setText("No Master Height (Default)")
                sku_height.setStyleSheet(f"font-size: {UIScaling.scale_font(11)}px; color: #9CA3AF; border: none;")

            gdrive_id = data.get("gdrive_id") or data.get("GDrive ID") or ""
            if gdrive_id:
                if gdrive_id not in self.card_labels:
                    self.card_labels[gdrive_id] = []
                self.card_labels[gdrive_id].append(img_label)
                self.image_loader.load_image(gdrive_id)
        else:
            sku_name.setText("Tap to select SKU" if is_editable else "Empty")
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

        # Reset button
        btn_reset = QPushButton()
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setFixedSize(UIScaling.scale(42), UIScaling.scale(42))
        btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEE2E2;
                border: 1.5px solid #FECACA;
                border-radius: {UIScaling.scale(8)}px;
                padding: {UIScaling.scale(8)}px;
            }}
            QPushButton:hover {{ background-color: #FECACA; }}
            QPushButton:pressed {{ background-color: #FCA5A5; }}
        """)
        
        # Trash icon (Simple SVG path)
        trash_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>"""
        try:
            from PySide6.QtSvgWidgets import QSvgWidget
            svg_widget = QSvgWidget()
            svg_widget.load(trash_icon.encode('utf-8'))
            svg_widget.setFixedSize(UIScaling.scale(20), UIScaling.scale(20))
            
            btn_reset_layout = QVBoxLayout(btn_reset)
            btn_reset_layout.setContentsMargins(0, 0, 0, 0)
            btn_reset_layout.setAlignment(Qt.AlignCenter)
            btn_reset_layout.addWidget(svg_widget)
        except ImportError:
            btn_reset.setText("R") # Fallback if SvgWidgets not available
            btn_reset.setStyleSheet(btn_reset.styleSheet() + " color: #DC2626; font-weight: bold;")
        
        btn_reset.clicked.connect(lambda _, idx=index: self.reset_sku_report(idx))
        layout.addWidget(btn_reset)

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

    def reset_sku_report(self, index):
        """Reset the measurement counts for a specific SKU in this profile."""
        if index < 0 or index >= len(self.sku_rows):
            return
            
        row = self.sku_rows[index]
        sku_data = row["data"]
        if not sku_data:
            return
            
        sku_code = sku_data.get("code")
        if not sku_code:
            return
            
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Konfirmasi Reset",
            f"Reset laporan/hitung untuk SKU {sku_code}?\nData permanen di RecordManager akan ikut terhapus.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # 1. Load records
        records = RecordManager.get_all_records()
        profile_id = self.current_profile.get("id")
        
        # 2. Find the active record for this profile
        target_record = None
        for r in records:
            if r.get("preset_id") == profile_id:
                target_record = r
                break
                
        if not target_record:
            QMessageBox.information(self, "Info", "Belum ada data rekaman untuk SKU ini.")
            return
            
        # 3. Identify preset indices matching this SKU
        profile_presets = self.current_profile.get("presets", [])
        matching_indices = []
        for i, p in enumerate(profile_presets):
            if p.get("sku") == sku_code:
                matching_indices.append(str(i))
                
        # 4. Clear matching entries in per_sku_counts
        per_sku_counts = target_record.get("per_sku_counts", {})
        cleared_count = 0
        from app.data.record_manager import DEFAULT_COUNTS
        
        for idx_str in matching_indices:
            if idx_str in per_sku_counts:
                per_sku_counts[idx_str] = dict(DEFAULT_COUNTS)
                cleared_count += 1
                
        # 5. Re-calculate aggregate counts
        new_aggregate = dict(DEFAULT_COUNTS)
        for val in per_sku_counts.values():
            for key in new_aggregate:
                new_aggregate[key] += val.get(key, 0)
        
        target_record["counts"] = new_aggregate
        target_record["per_sku_counts"] = per_sku_counts
        
        # 6. Save
        RecordManager._save(records)
        
        QMessageBox.information(self, "Selesai", f"Berhasil reset {cleared_count} preset untuk SKU {sku_code}.")

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

        if "Kiri" in text:
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
        elif "Kanan" in text:
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
            row["height"].setText(f"Master Height: {height} mm")
            row["height"].setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; font-weight: 600; color: #059669; border: none;")
        else:
            row["height"].setText("No Master Height (Default)")
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

    # ─── WO RE-SYNC ───────────────────────────────────────

    def re_sync_wo(self):
        """Allow user to pick a new WO and update this preset's fields."""
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        plant = settings.get("plant", "EVA1")
        machine = self.current_profile.get("machine") or settings.get("machine", "Mesin 08")
        
        try:
            wo_list = fetch_wo_list(plant, machine)
            overlay = WOSelectorOverlay(self.window(), wo_list, plant=plant, machine=machine)
            overlay.wo_selected.connect(self._on_wo_reselected)
        except Exception as e:
            self._show_toast(f"Error fetching WOs: {e}", is_error=True)

    def _on_wo_reselected(self, wo_data):
        if not wo_data or not self.current_profile: return
        
        # Enrich
        enriched = enrich_wo_with_sku(wo_data)
        
        # Update metadata
        self.current_profile["wo_number"] = enriched.get('nomor_wo', 'Untitled')
        self.current_profile["plant"] = enriched.get('plant', '')
        self.current_profile["shift"] = enriched.get('shift', '')
        self.current_profile["mps"] = enriched.get('nomor_mps', '')
        self.current_profile["machine"] = enriched.get('machine', '')
        self.current_profile["notes"] = enriched.get('notes', '')
        
        prod_date = enriched.get('tanggal_produksi')
        if hasattr(prod_date, 'strftime'):
            self.current_profile["production_date"] = prod_date.strftime("%d/%m/%Y")
        else:
            self.current_profile["production_date"] = str(prod_date or datetime.now().strftime("%d/%m/%Y"))

        # Update Name
        wo_num = self.current_profile["wo_number"]
        mac = self.current_profile["machine"]
        self.current_profile["name"] = f"{wo_num} - {mac}" if mac else wo_num

        # Update SKUs
        new_skus = []
        for idx, sku in enumerate(enriched.get("skus", [])):
            # Distribute between Kiri and Kanan if multiple
            team_pos = "Kiri" if idx == 0 else "Kanan"
            
            new_skus.append({
                "code": sku.get("code", sku.get("default_code", "")),
                "Nama Produk": sku.get("Nama Produk", sku.get("name", "")),
                "gdrive_id": sku.get("gdrive_id", ""),
                "otorisasi": sku.get("otorisasi", 0),
                "sizes": sku.get("sizes", "36,37,38,39,40,41,42,43,44"),
                "team": team_pos,
                "Master Height": sku.get("Master Height", 0),
                "id": sku.get("id")
            })
        self.current_profile["selected_skus"] = new_skus

        # Update internal presets
        presets = []
        for idx, sku in enumerate(new_skus):
            code = sku["code"]
            oto = sku["otorisasi"]
            product_id = sku.get("id")
            size_list = self._parse_sizes(sku["sizes"], code)
            for s in size_list:
                presets.append({
                    "sku": code,
                    "product_id": product_id,
                    "size": s,
                    "color_idx": (idx % 4) + 1,
                    "team": sku["team"],
                    "otorisasi": oto
                })
        self.current_profile["presets"] = presets

        # Refresh UI & Auto-Save
        self.load_profile(self.current_profile)
        self.save_preset()
        self._show_toast("✓ Data updated and saved from Work Order")

    # ─── ACTIONS ──────────────────────────────────────────

    def _parse_sizes(self, size_str, code=""):
        if not size_str:
            return ["36", "37", "38", "39", "40", "41", "42", "43", "44"]

        s = str(size_str).strip().upper()

        if "," in s:
            items = [x.strip() for x in s.split(",")]
            result = []
            for item in items:
                if "/" in item and "MM" not in item:
                    parts = item.split("/")
                    result.append(parts[-1].strip())
                else:
                    result.append(item)
            return result

        def resolve_slash(val):
            if "/" in val:
                parts = val.split("/")
                return parts[-1].strip()
            return val

        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2:
                start_s = resolve_slash(parts[0].strip())
                end_s = resolve_slash(parts[1].strip())
                if start_s.isdigit() and end_s.isdigit():
                    start = int(start_s)
                    end = int(end_s)
                    if start < end:
                        return [str(i) for i in range(start, end + 1)]

        if "/" in s:
            return [resolve_slash(s)]

        return [s]

    def save_preset(self):
        if not self.current_profile:
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

        if self.current_profile.get("status") == "draft":
            self.current_profile["status"] = "ready"

        presets = []
        selected_skus = []
        for idx, row in enumerate(self.sku_rows):
            data = row["data"]
            if data:
                data = data.copy()
                code = data.get("code", "UNKNOWN")
                team = data.get("team", "")
                otorisasi = data.get("otorisasi", 0)
                product_id = data.get("id")
                selected_skus.append(data)

                sizes = self._parse_sizes(data.get("sizes", ""), code)
                for s in sizes:
                    presets.append({
                        "sku": code,
                        "product_id": product_id,
                        "size": s,
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
        self._show_toast("✓ Preset tersimpan!")

    def activate_preset(self):
        if not self.current_profile:
            return
        self.save_preset()

        try:
            all_profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except:
            all_profiles = []

        for p in all_profiles:
            if p.get("status") == "active":
                p["status"] = "ready"
            if p.get("id") == self.current_profile.get("id"):
                p["status"] = "active"

        self.current_profile["status"] = "active"
        JsonUtility.save_to_json(PROFILES_FILE, all_profiles)

        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = self.current_profile["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)

        self.load_profile(self.current_profile)
        self._show_toast("✓ Preset diaktifkan!")

    def finish_preset(self):
        if not self.current_profile:
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
        self._show_toast("✓ Preset selesai!")

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
        if self.current_profile.get("status") in ("draft", "ready"):
            self.save_preset()
            self.activate_preset()
        if self.controller:
            self.controller.go_to_live()

    def go_back(self):
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
