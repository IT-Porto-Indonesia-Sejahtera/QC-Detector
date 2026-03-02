import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy, QScrollArea, QMessageBox, QTextEdit, QScroller
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from app.widgets.sku_selector_overlay import SkuSelectorOverlay
from app.utils.image_loader import NetworkImageLoader
from app.data.record_manager import RecordManager

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
                background-color: #F9FAFB;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(14)}px;
                font-size: {UIScaling.scale_font(15)}px;
                font-weight: 600;
                color: #111827;
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

        self.info_plant.setText(profile.get("plant", ""))
        self.info_shift.setText(profile.get("shift", ""))
        self.info_date.setText(profile.get("production_date", ""))
        self.info_mps.setText(profile.get("mps", ""))
        self.notes_input.setPlainText(profile.get("notes", ""))

        # Button visibility based on status
        is_editable = status in ("draft", "ready")
        self.btn_save.setVisible(is_editable)
        self.btn_delete.setVisible(status != "active")
        self.btn_activate.setVisible(status == "ready")
        self.btn_finish.setVisible(status == "active")
        self.btn_ukur.setVisible(status in ("ready", "active"))

        # Disable editing for done/active
        for field in [self.info_plant, self.info_shift, self.info_date, self.info_mps]:
            field.setReadOnly(not is_editable)
            if not is_editable:
                field.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: #F3F4F6;
                        border: 1.5px solid #E5E7EB;
                        border-radius: {UIScaling.scale(10)}px;
                        padding: 0 {UIScaling.scale(14)}px;
                        font-size: {UIScaling.scale_font(15)}px;
                        font-weight: 600;
                        color: #9CA3AF;
                    }}
                """)
        self.notes_input.setReadOnly(not is_editable)

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

        # SKU Name
        sku_name = QLabel()
        if data:
            display_name = data.get("Nama Produk", data.get("code", "Unknown"))
            sku_name.setText(display_name)
            sku_name.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; font-weight: 700; color: #111827; border: none;")

            gdrive_id = data.get("gdrive_id", "")
            if gdrive_id:
                if gdrive_id not in self.card_labels:
                    self.card_labels[gdrive_id] = []
                self.card_labels[gdrive_id].append(img_label)
                self.image_loader.load_image(gdrive_id)
        else:
            sku_name.setText("Tap to select SKU" if is_editable else "Empty")
            sku_name.setStyleSheet(f"font-size: {UIScaling.scale_font(15)}px; font-weight: 500; color: #9CA3AF; border: none;")

        layout.addWidget(sku_name, 1)

        # Position label
        raw_position = data.get("team", "") if data else ""
        position = self._format_position(raw_position)
        lbl_pos = QLabel(position)

        if "Kiri" in position:
            lbl_pos.setStyleSheet(f"""
                font-size: {UIScaling.scale_font(13)}px;
                font-weight: 700;
                color: #1E40AF;
                background-color: #DBEAFE;
                padding: {UIScaling.scale(6)}px {UIScaling.scale(14)}px;
                border-radius: {UIScaling.scale(8)}px;
                border: 1.5px solid #93C5FD;
            """)
        elif "Kanan" in position:
            lbl_pos.setStyleSheet(f"""
                font-size: {UIScaling.scale_font(13)}px;
                font-weight: 700;
                color: #9A3412;
                background-color: #FFF7ED;
                padding: {UIScaling.scale(6)}px {UIScaling.scale(14)}px;
                border-radius: {UIScaling.scale(8)}px;
                border: 1.5px solid #FDBA74;
            """)
        else:
            lbl_pos.setStyleSheet("border: none;")

        layout.addWidget(lbl_pos)

        row_data = {
            "img": img_label,
            "name": sku_name,
            "pos": lbl_pos,
            "data": data,
        }
        self.sku_rows.append(row_data)

        if is_editable:
            container.mousePressEvent = lambda e, idx=index: self.select_sku(idx)

        return container

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
                selected_skus.append(data)

                sizes = self._parse_sizes(data.get("sizes", ""), code)
                for s in sizes:
                    presets.append({
                        "sku": code,
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
