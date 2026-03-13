"""
PresetReportPage — Merged tabbed page for Presets and Reports.

Preset tab: shows Draft and On Process presets
Report tab: shows Done presets as reports (via RecordManager)
"""
import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy, QScrollArea, QMessageBox, QDateEdit, QScroller
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.ui_scaling import UIScaling
from app.widgets.wo_selector_overlay import WOSelectorOverlay
from app.data.record_manager import RecordManager
from backend.get_wo_list import fetch_wo_list, enrich_wo_with_sku
from backend.get_product_sku import ProductSKUWorker
from backend.sku_cache import set_sku_data, add_log
from backend.DB import is_connected

PROFILES_FILE = os.path.join("output", "settings", "profiles.json")
SETTINGS_FILE = os.path.join("output", "settings", "app_settings.json")


class PresetReportPage(QWidget):
    """Merged page with two tabs: Preset (Draft/On Process) and Report (Done)."""

    TAB_PRESET = 0
    TAB_REPORT = 1

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.profiles = []
        self.records = []
        self.active_tab = self.TAB_PRESET
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

        # ── TAB BUTTONS ──
        tab_frame = QFrame()
        tab_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F0F0F5;
                border-radius: {UIScaling.scale(12)}px;
                border: none;
            }}
        """)
        tab_frame.setFixedHeight(UIScaling.scale(44))
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(UIScaling.scale(4), UIScaling.scale(4), UIScaling.scale(4), UIScaling.scale(4))
        tab_layout.setSpacing(UIScaling.scale(4))

        self.btn_tab_preset = QPushButton("📋  Preset")
        self.btn_tab_preset.setCursor(Qt.PointingHandCursor)
        self.btn_tab_preset.setFixedHeight(UIScaling.scale(36))
        self.btn_tab_preset.clicked.connect(lambda: self.switch_tab(self.TAB_PRESET))
        tab_layout.addWidget(self.btn_tab_preset)

        self.btn_tab_report = QPushButton("📊  Report")
        self.btn_tab_report.setCursor(Qt.PointingHandCursor)
        self.btn_tab_report.setFixedHeight(UIScaling.scale(36))
        self.btn_tab_report.clicked.connect(lambda: self.switch_tab(self.TAB_REPORT))
        tab_layout.addWidget(self.btn_tab_report)

        h_layout.addWidget(tab_frame)
        h_layout.addStretch()

        # Sync SKU button
        self.btn_sync = QPushButton("🔄 Perbarui Tipe")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setFixedHeight(UIScaling.scale(48))
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 1.5px solid #2563EB;
                border-radius: {UIScaling.scale(12)}px;
                padding: 0 {UIScaling.scale(20)}px;
                font-size: {UIScaling.scale_font(13)}px;
                font-weight: 700;
                color: #2563EB;
            }}
            QPushButton:hover {{ background-color: #EFF6FF; }}
            QPushButton:disabled {{ color: #9CA3AF; border-color: #D1D5DB; }}
        """)
        self.btn_sync.clicked.connect(self.fetch_sku_data)
        h_layout.addWidget(self.btn_sync)

        layout.addWidget(header)

        # ═══════════════════════════════════════
        # FILTER BAR
        # ═══════════════════════════════════════
        self.filter_bar = QFrame()
        self.filter_bar.setFixedHeight(UIScaling.scale(65))
        self.filter_bar.setStyleSheet("background-color: #ECEEF2;")
        f_layout = QHBoxLayout(self.filter_bar)
        f_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(10), UIScaling.scale(24), UIScaling.scale(10))
        f_layout.setSpacing(UIScaling.scale(12))

        # Tambah Preset button (only visible on preset tab)
        self.btn_add = QPushButton("＋  Buat Preset Baru")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFixedHeight(UIScaling.scale(44))
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: {UIScaling.scale(10)}px;
                padding: 0 {UIScaling.scale(20)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #059669; }}
            QPushButton:pressed {{ background-color: #047857; }}
        """)

        self.lbl_tgl = QLabel("Tanggal")
        self.lbl_tgl.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; font-weight: 600; color: #666;")
        f_layout.addWidget(self.lbl_tgl)

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
        self.search_input.setPlaceholderText("🔍  Search...")
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

        layout.addWidget(self.filter_bar)

        # Container for the "Tambah Preset" button (above the list)
        self.add_btn_container = QWidget()
        self.add_btn_layout = QHBoxLayout(self.add_btn_container)
        self.add_btn_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(10), UIScaling.scale(24), 0)
        self.btn_add.clicked.connect(self.add_preset)
        self.add_btn_layout.addWidget(self.btn_add)
        self.add_btn_layout.addStretch()
        layout.addWidget(self.add_btn_container)

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

        # Apply initial tab styling
        self._update_tab_styles()

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

    # ─── TAB SWITCHING ────────────────────────────────────

    def switch_tab(self, tab):
        self.active_tab = tab
        self._update_tab_styles()
        self.render_list()
        
        is_report = (tab == self.TAB_REPORT)
        self.add_btn_container.setVisible(not is_report)
        self.filter_bar.setVisible(is_report)
        self.lbl_tgl.setVisible(is_report)
        self.date_from.setVisible(is_report)
        self.date_to.setVisible(is_report)
        self.search_input.setVisible(is_report)

    def set_initial_tab(self, tab):
        """Set which tab to show when opening the page."""
        self.active_tab = tab
        self._update_tab_styles()
        
        is_report = (tab == self.TAB_REPORT)
        self.add_btn_container.setVisible(not is_report)
        self.filter_bar.setVisible(is_report)
        self.lbl_tgl.setVisible(is_report)
        self.date_from.setVisible(is_report)
        self.date_to.setVisible(is_report)
        self.search_input.setVisible(is_report)

    def _update_tab_styles(self):
        active_style = f"""
            QPushButton {{
                background-color: white;
                color: #1C1C1E;
                border: none;
                border-radius: {UIScaling.scale(8)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 700;
                padding: 0 {UIScaling.scale(20)}px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background-color: transparent;
                color: #6B7280;
                border: none;
                border-radius: {UIScaling.scale(8)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 600;
                padding: 0 {UIScaling.scale(20)}px;
            }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.5); }}
        """
        if self.active_tab == self.TAB_PRESET:
            self.btn_tab_preset.setStyleSheet(active_style)
            self.btn_tab_report.setStyleSheet(inactive_style)
        else:
            self.btn_tab_preset.setStyleSheet(inactive_style)
            self.btn_tab_report.setStyleSheet(active_style)

    # ─── DATA ─────────────────────────────────────────────

    def load_profiles(self):
        try:
            self.profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except Exception as e:
            print(f"[PresetReportPage] Error loading profiles: {e}")
            self.profiles = []

        # Auto-migrate old statuses
        migrated = False
        for p in self.profiles:
            if p.get("status") == "ready":
                p["status"] = "draft"
                migrated = True
            elif p.get("status") == "active":
                p["status"] = "on_process"
                migrated = True
            # Legacy migration for very old profiles
            if "wo_number" not in p:
                name = p.get("name", "Untitled")
                p.setdefault("wo_number", f"11/EVA1/WO/{name}")
                p.setdefault("plant", "PVC1")
                p.setdefault("shift", "Shift Siang")
                p.setdefault("machine", "Mesin 8")
                p.setdefault("production_date", p.get("last_updated", "").split(",")[0].strip())
                p.setdefault("mps", f"11/PVC1/MPS/26/001")
                p.setdefault("notes", "")
                p.setdefault("status", "draft")
                migrated = True
        if migrated:
            self.save_profiles()

        self.records = RecordManager.get_all_records()
        self.render_list()

    def save_profiles(self):
        try:
            JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        except Exception as e:
            print(f"[PresetReportPage] Error saving profiles: {e}")

    def refresh_data(self):
        self.load_profiles()

    # ─── FILTER ───────────────────────────────────────────

    def filter_list(self):
        self.render_list()

    def _matches_filters(self, item):
        query = self.search_input.text().strip().lower()
        if query:
            searchable = (
                item.get("name", "") +
                item.get("wo_number", "") +
                item.get("machine", "") +
                item.get("plant", "") +
                item.get("shift", "")
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

        if self.active_tab == self.TAB_PRESET:
            self._render_preset_tab()
        else:
            self._render_report_tab()

        self.list_layout.addStretch()

    def _render_preset_tab(self):
        """Render Draft and On Process presets."""
        count = 0
        for profile in self.profiles:
            status = profile.get("status", "draft")
            if status == "done":
                continue  # Done presets only show in Report tab
            if not self._matches_filters(profile):
                continue
            card = self._create_preset_card(profile)
            self.list_layout.addWidget(card)
            count += 1

        if count == 0:
            lbl_empty = QLabel("Belum ada preset")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; color: #9CA3AF; padding: {UIScaling.scale(40)}px;")
            self.list_layout.addWidget(lbl_empty)

    def _render_report_tab(self):
        """Render Done presets as report entries."""
        # Combine: done presets + records
        done_profiles = [p for p in self.profiles if p.get("status") == "done"]
        
        count = 0
        for profile in done_profiles:
            if not self._matches_filters(profile):
                continue
            # Find matching record for counts
            record = RecordManager.get_record_by_preset_id(profile.get("id"))
            card = self._create_report_card(profile, record)
            self.list_layout.addWidget(card)
            count += 1

        # Also show any orphan records (records without matching profiles)
        profile_ids = {p.get("id") for p in self.profiles}
        for record in self.records:
            if record.get("preset_id") not in profile_ids:
                if not self._matches_filters(record):
                    continue
                card = self._create_report_card(record, record)
                self.list_layout.addWidget(card)
                count += 1

        if count == 0:
            lbl_empty = QLabel("Belum ada report")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet(f"font-size: {UIScaling.scale_font(16)}px; color: #9CA3AF; padding: {UIScaling.scale(40)}px;")
            self.list_layout.addWidget(lbl_empty)

    def _create_preset_card(self, profile):
        status = profile.get("status", "draft")

        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(UIScaling.scale(105))

        # Status theme (only draft and on_process)
        status_themes = {
            "draft":      {"bg": "#FFFBEB", "border": "#FCD34D", "badge_bg": "#FEF3C7", "badge_text": "#92400E", "badge_border": "#FCD34D", "accent": "#F59E0B"},
            "on_process": {"bg": "#EFF6FF", "border": "#93C5FD", "badge_bg": "#DBEAFE", "badge_text": "#1E40AF", "badge_border": "#93C5FD", "accent": "#2563EB"},
        }
        t = status_themes.get(status, status_themes["draft"])

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg']};
                border: 2px solid {t['border']};
                border-radius: {UIScaling.scale(14)}px;
                border-left: {UIScaling.scale(6)}px solid {t['accent']};
            }}
            QFrame:hover {{
                border-color: {t['accent']};
                border-left: {UIScaling.scale(6)}px solid {t['accent']};
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, UIScaling.scale(20), 0)
        layout.setSpacing(0)

        # Status badge (left side)
        badge_frame = QFrame()
        badge_frame.setFixedWidth(UIScaling.scale(100))
        badge_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['badge_bg']};
                border: none;
                border-top-left-radius: {UIScaling.scale(12)}px;
                border-bottom-left-radius: {UIScaling.scale(12)}px;
                border-right: 1px solid {t['badge_border']};
            }}
        """)
        badge_layout = QVBoxLayout(badge_frame)
        badge_layout.setAlignment(Qt.AlignCenter)
        badge_layout.setContentsMargins(0, 0, 0, 0)

        badge_text = "DRAFT" if status == "draft" else "ON PROCESS"
        badge_label = QLabel(badge_text)
        badge_label.setAlignment(Qt.AlignCenter)
        badge_label.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(11)}px;
            font-weight: 800;
            color: {t['badge_text']};
            border: none;
            letter-spacing: 1px;
        """)
        badge_layout.addWidget(badge_label)
        layout.addWidget(badge_frame)

        # Main content
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(UIScaling.scale(20), UIScaling.scale(12), 0, UIScaling.scale(12))
        info_layout.setSpacing(UIScaling.scale(6))

        wo_number = profile.get("wo_number", profile.get("name", "Untitled"))
        machine = profile.get("machine", "")
        title_text = f"{wo_number} - {machine}" if machine else wo_number

        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(17)}px; font-weight: 700; color: #1C1C1E; border: none;")
        info_layout.addWidget(lbl_title)

        plant = profile.get("plant", "")
        shift = profile.get("shift", "")
        date = profile.get("production_date", profile.get("last_updated", "").split(",")[0].strip())
        subtitle_parts = [p for p in [plant, shift, date] if p]
        subtitle = "    ·    ".join(subtitle_parts)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        info_layout.addWidget(lbl_sub)

        layout.addLayout(info_layout, 1)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(UIScaling.scale(10))

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
        btn_del.clicked.connect(lambda _, p=profile: self.delete_preset(p))
        # Only show delete for draft presets (not on_process)
        btn_del.setVisible(status != "on_process")
        action_layout.addWidget(btn_del)

        layout.addLayout(action_layout)

        card.mousePressEvent = lambda e, p=profile: self._on_preset_click(p, e)
        return card

    def _create_report_card(self, profile_or_record, record):
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(UIScaling.scale(100))

        accent = "#10B981"
        bg = "white"
        border = "#E5E7EB"

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

        wo = profile_or_record.get("wo_number", "Unknown")
        machine = profile_or_record.get("machine", "")
        title_text = f"{wo} - {machine}" if machine else wo

        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(17)}px; font-weight: 700; color: #111827; border: none;")
        info_layout.addWidget(lbl_title)

        plant = profile_or_record.get("plant", "")
        shift = profile_or_record.get("shift", "")
        date = profile_or_record.get("production_date", "")
        subtitle_parts = [p for p in [plant, shift, date] if p]
        subtitle = "    ·    ".join(subtitle_parts)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet(f"font-size: {UIScaling.scale_font(13)}px; color: #6B7280; border: none;")
        info_layout.addWidget(lbl_sub)

        layout.addLayout(info_layout, 1)

        # Summary counts
        if record:
            counts = record.get("counts", {})
            total_good = counts.get("TOTAL GOOD", 0)
            total_bs = counts.get("TOTAL BS", 0)
            oven = counts.get("TOTAL OVEN", counts.get("OVEN 1", 0) + counts.get("OVEN 2", 0))
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

        # Delete button REMOVED as per user request (report cant be deleted)
        # btn_del = QPushButton("🗑")
        # btn_del.setCursor(Qt.PointingHandCursor)
        # ...
        # layout.addWidget(btn_del)

        card.mousePressEvent = lambda e, p=profile_or_record, r=record: self._on_report_click(p, r, e)
        return card

    def _on_preset_click(self, profile, event):
        if self.controller:
            self.controller.go_to_preset_detail(profile)

    def _on_report_click(self, profile, record, event):
        if self.controller:
            if record:
                self.controller.go_to_report_detail(record)
            else:
                # If no record, open preset detail as read-only
                self.controller.go_to_preset_detail(profile)

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
                start_s = resolve_slash(parts[0].strip()); end_s = resolve_slash(parts[1].strip())
                if start_s.isdigit() and end_s.isdigit():
                    start, end = int(start_s), int(end_s)
                    if start < end: return [str(i) for i in range(start, end + 1)]
        if "/" in s: return [resolve_slash(s)]
        return [s]

    def add_preset(self):
        """Fetch today's WOs and show selector before creating."""
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        plant = settings.get("plant", "EVA1")
        machine = settings.get("machine", "Mesin 08")

        # Fetch WO list safely — isolate DB errors from UI
        if not is_connected():
            msg = QMessageBox(self)
            msg.setWindowTitle("Koneksi Database")
            msg.setText("Tidak terhubung ke Database.\nPastikan VPN / Internet aktif dan aplikasi sudah terhubung ke DB.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setIcon(QMessageBox.Warning)
            msg.setStyleSheet("QMessageBox { background-color: white; } QMessageBox QLabel { color: #333; font-size: 14px; }")
            msg.exec()
            return

        wo_list = []
        try:
            wo_list = fetch_wo_list(plant, machine)
        except Exception as e:
            print(f"[PresetReportPage] Error fetching WOs: {e}")
            import traceback
            traceback.print_exc()

        try:
            overlay = WOSelectorOverlay(self.window(), wo_list, plant=plant, machine=machine)
            overlay.wo_selected.connect(self._on_wo_selected)
        except Exception as e:
            print(f"[PresetReportPage] Error creating WO overlay: {e}")
            import traceback
            traceback.print_exc()

    def _on_wo_selected(self, wo_data):
        if not wo_data:
            return

        enriched = enrich_wo_with_sku(wo_data)

        wo_num = enriched.get('nomor_wo', 'Untitled')
        machine = enriched.get('machine', '')
        shift = enriched.get('shift', '')

        prod_date = enriched.get('tanggal_produksi')
        if hasattr(prod_date, 'strftime'):
            prod_date = prod_date.strftime("%d/%m/%Y")
        else:
            prod_date = str(prod_date or datetime.now().strftime("%d/%m/%Y"))

        new_profile = {
            "id": str(uuid.uuid4()),
            "name": f"{wo_num} - {machine}",
            "wo_number": wo_num,
            "plant": enriched.get('plant', ''),
            "shift": shift,
            "production_date": prod_date,
            "mps": enriched.get('nomor_mps', ''),
            "machine": machine,
            "notes": enriched.get('notes', ''),
            "status": "draft",
            "last_updated": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            "selected_skus": [],
            "presets": []
        }

        # Populate selected_skus from the enriched WO
        wo_skus = enriched.get("skus", [])
        for idx, sku in enumerate(wo_skus):
            team_pos = "Kiri" if idx == 0 else "Kanan"
            new_profile["selected_skus"].append({
                "code": sku.get("code", sku.get("default_code", "")),
                "Nama Produk": sku.get("Nama Produk", sku.get("name", "")),
                "gdrive_id": sku.get("gdrive_id", ""),
                "otorisasi": sku.get("otorisasi", 0),
                "sizes": sku.get("sizes", "36,37,38,39,40,41,42,43,44"),
                "team": team_pos,
                "Master Height": sku.get("Master Height", 0),
                "id": sku.get("id")
            })

        # Generate internal presets list
        presets = []
        for idx, sku in enumerate(new_profile["selected_skus"]):
            code = sku.get("code") or sku.get("Nama Produk") or "UNKNOWN"
            oto = sku.get("otorisasi", 0)
            size_list = self._parse_sizes(sku.get("sizes", ""), code)
            for s in size_list:
                presets.append({
                    "sku": code,
                    "product_id": sku.get("id"),
                    "size": s,
                    "color_idx": (idx % 4) + 1,
                    "team": sku.get("team"),
                    "otorisasi": oto
                })
        new_profile["presets"] = presets

        # Don't auto-save — user must manually save from detail page
        # self.profiles.append(new_profile)
        # self.save_profiles()

        if self.controller:
            self.controller.go_to_preset_detail(new_profile)

    def delete_preset(self, profile):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Preset")
        msg.setText(f"Hapus preset '{profile.get('wo_number', profile.get('name', ''))}'?")
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
            if profile in self.profiles:
                self.profiles.remove(profile)
            self.save_profiles()
            self.render_list()

    def delete_report(self, profile, record):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hapus Report")
        msg.setText(f"Hapus report '{profile.get('wo_number', '')}'?")
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
            # Delete both the profile and the record
            if profile in self.profiles:
                self.profiles.remove(profile)
                self.save_profiles()
            if record:
                RecordManager.delete_record(record.get("id"))
                self.records = RecordManager.get_all_records()
            self.render_list()
            self._show_toast("✓ Report dihapus")

    def fetch_sku_data(self):
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("Syncing...")
        add_log("Starting SKU data fetch from Preset/Report page...")

        self.sku_worker = ProductSKUWorker()
        self.sku_worker.finished.connect(self._on_sku_fetch_success)
        self.sku_worker.error.connect(self._on_sku_fetch_error)
        self.sku_worker.start()

    def _on_sku_fetch_success(self, data):
        if data:
            set_sku_data(data)
            self._show_toast(f"✓ Successfully synced {len(data)} SKUs")
        else:
            self._show_toast("No SKU data returned", is_error=True)
        self._reset_sync_button()

    def _on_sku_fetch_error(self, error_msg):
        self._show_toast(f"Sync failed: {error_msg}", is_error=True)
        self._reset_sync_button()

    def _reset_sync_button(self):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 Perbarui Tipe")

    def go_back(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Kembali")
        msg.setText("Apakah Anda yakin ingin ke halaman utama?")
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
