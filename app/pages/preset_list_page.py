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


class PresetListPage(QWidget):
    """Full-screen page showing a list of presets with status badges."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.profiles = []
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

        lbl_title = QLabel("List Preset")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: 800; color: #1C1C1E;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        # Refresh button
        btn_refresh = QPushButton("🔄")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setFixedSize(UIScaling.scale(48), UIScaling.scale(48))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F0F5;
                border: none;
                border-radius: {UIScaling.scale(24)}px;
                font-size: {UIScaling.scale_font(18)}px;
            }}
            QPushButton:hover {{ background-color: #E0E0E5; }}
        """)
        btn_refresh.clicked.connect(self.refresh_data)
        h_layout.addWidget(btn_refresh)

        # Sync SKU button
        self.btn_sync = QPushButton("🔄 Sync SKU")
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

        # Mulai button
        self.btn_mulai = QPushButton("▶  Mulai")
        self.btn_mulai.setCursor(Qt.PointingHandCursor)
        self.btn_mulai.setFixedHeight(UIScaling.scale(48))
        self.btn_mulai.setStyleSheet(f"""
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
        self.btn_mulai.clicked.connect(self.start_active_preset)
        h_layout.addWidget(self.btn_mulai)

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

        # Tambah Preset button (integrated with WO Sync)
        btn_add = QPushButton("＋  Tambah Preset")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(UIScaling.scale(44))
        btn_add.setStyleSheet(f"""
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
        btn_add.clicked.connect(self.add_preset)
        f_layout.addWidget(btn_add)

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
        self.search_input.setPlaceholderText("🔍  Search preset...")
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

    def load_profiles(self):
        try:
            self.profiles = JsonUtility.load_from_json(PROFILES_FILE) or []
        except Exception as e:
            print(f"[PresetListPage] Error loading profiles: {e}")
            self.profiles = []

        # Auto-migrate old profiles that lack WO fields
        migrated = False
        for p in self.profiles:
            if "wo_number" not in p:
                name = p.get("name", "Untitled")
                p.setdefault("wo_number", f"11/EVA1/WO/{name}")
                p.setdefault("plant", "PVC1")
                p.setdefault("shift", "Shift Siang")
                p.setdefault("machine", "Mesin 8")
                p.setdefault("production_date", p.get("last_updated", "").split(",")[0].strip())
                p.setdefault("mps", f"11/PVC1/MPS/26/001")
                p.setdefault("notes", "")
                p.setdefault("status", "ready")
                migrated = True
        if migrated:
            self.save_profiles()

        self.render_list()

    def save_profiles(self):
        try:
            JsonUtility.save_to_json(PROFILES_FILE, self.profiles)
        except Exception as e:
            print(f"[PresetListPage] Error saving profiles: {e}")

    def refresh_data(self):
        self.load_profiles()

    # ─── FILTER ───────────────────────────────────────────

    def filter_list(self):
        self.render_list()

    def _matches_filters(self, profile):
        query = self.search_input.text().strip().lower()
        if query:
            searchable = (
                profile.get("name", "") +
                profile.get("wo_number", "") +
                profile.get("machine", "") +
                profile.get("plant", "") +
                profile.get("shift", "")
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

        for profile in self.profiles:
            if not self._matches_filters(profile):
                continue
            card = self._create_preset_card(profile)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _create_preset_card(self, profile):
        status = profile.get("status", "ready")

        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(UIScaling.scale(105))

        # Status theme
        status_themes = {
            "draft":  {"bg": "#FFFBEB", "border": "#FCD34D", "badge_bg": "#FEF3C7", "badge_text": "#92400E", "badge_border": "#FCD34D", "accent": "#F59E0B"},
            "ready":  {"bg": "white",   "border": "#E5E7EB", "badge_bg": "#ECFDF5", "badge_text": "#065F46", "badge_border": "#A7F3D0", "accent": "#10B981"},
            "active": {"bg": "#EFF6FF", "border": "#93C5FD", "badge_bg": "#DBEAFE", "badge_text": "#1E40AF", "badge_border": "#93C5FD", "accent": "#2563EB"},
            "done":   {"bg": "#F9FAFB", "border": "#D1D5DB", "badge_bg": "#F3F4F6", "badge_text": "#6B7280", "badge_border": "#D1D5DB", "accent": "#9CA3AF"},
        }
        t = status_themes.get(status, status_themes["ready"])

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
        badge_frame.setFixedWidth(UIScaling.scale(90))
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

        badge_label = QLabel(status.upper())
        badge_label.setAlignment(Qt.AlignCenter)
        badge_label.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(12)}px;
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

        if status == "ready":
            btn_pilih = QPushButton("Pilih")
            btn_pilih.setCursor(Qt.PointingHandCursor)
            btn_pilih.setFixedSize(UIScaling.scale(90), UIScaling.scale(44))
            btn_pilih.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2563EB;
                    color: white;
                    border: none;
                    border-radius: {UIScaling.scale(10)}px;
                    font-size: {UIScaling.scale_font(14)}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{ background-color: #1D4ED8; }}
                QPushButton:pressed {{ background-color: #1E40AF; }}
            """)
            btn_pilih.clicked.connect(lambda _, p=profile: self.activate_preset(p))
            action_layout.addWidget(btn_pilih)

        elif status == "active":
            btn_selesai = QPushButton("Selesai")
            btn_selesai.setCursor(Qt.PointingHandCursor)
            btn_selesai.setFixedSize(UIScaling.scale(100), UIScaling.scale(44))
            btn_selesai.setStyleSheet(f"""
                QPushButton {{
                    background-color: #F59E0B;
                    color: white;
                    border: none;
                    border-radius: {UIScaling.scale(10)}px;
                    font-size: {UIScaling.scale_font(14)}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{ background-color: #D97706; }}
                QPushButton:pressed {{ background-color: #B45309; }}
            """)
            btn_selesai.clicked.connect(lambda _, p=profile: self.finish_preset(p))
            action_layout.addWidget(btn_selesai)

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
        action_layout.addWidget(btn_del)

        layout.addLayout(action_layout)

        card.mousePressEvent = lambda e, p=profile: self._on_card_click(p, e)
        return card

    def _on_card_click(self, profile, event):
        if self.controller:
            self.controller.go_to_preset_detail(profile)

    # ─── ACTIONS ──────────────────────────────────────────

    def add_preset(self):
        """Fetch today's WOs and show selector before creating."""
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        plant = settings.get("plant", "EVA1")
        machine = settings.get("machine", "Mesin 08")
        
        # Fetch WO list safely — isolate DB errors from UI
        wo_list = []
        if is_connected():
            try:
                wo_list = fetch_wo_list(plant, machine)
            except Exception as e:
                print(f"[PresetListPage] Error fetching WOs: {e}")
                import traceback
                traceback.print_exc()

        # Create overlay separately so a DB error doesn't prevent it from showing
        try:
            overlay = WOSelectorOverlay(self.window(), wo_list, plant=plant, machine=machine)
            overlay.wo_selected.connect(self._on_wo_selected)
        except Exception as e:
            print(f"[PresetListPage] Error creating WO overlay: {e}")
            import traceback
            traceback.print_exc()

    def _on_wo_selected(self, wo_data):
        if not wo_data: return
        
        # Enrich with SKU data (otorisasi)
        enriched = enrich_wo_with_sku(wo_data)
        
        wo_num = enriched.get('nomor_wo', 'Untitled')
        machine = enriched.get('machine', '')
        shift = enriched.get('shift', '')
        
        prod_date = enriched.get('tanggal_produksi')
        if hasattr(prod_date, 'strftime'): # Handle date/datetime objects
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
        for sku in wo_skus:
            new_profile["selected_skus"].append({
                "code": sku.get("code", sku.get("default_code", "")),
                "Nama Produk": sku.get("Nama Produk", sku.get("name", "")),
                "gdrive_id": sku.get("gdrive_id", ""),
                "otorisasi": sku.get("otorisasi", 0),
                "sizes": sku.get("sizes", "36,37,38,39,40,41,42,43,44"),
                "team": "Kiri", # Default position
            })

        # Generate internal presets list
        presets = []
        for idx, sku in enumerate(new_profile["selected_skus"]):
            code = sku["code"]
            oto = sku["otorisasi"]
            # Helper to parse sizes (assuming it matches the one in ProfilesPage)
            size_list = [s.strip() for s in sku["sizes"].split(',') if s.strip()]
            for s in size_list:
                presets.append({
                    "sku": code,
                    "size": s,
                    "color_idx": (idx % 4) + 1,
                    "team": sku["team"],
                    "otorisasi": oto
                })
        new_profile["presets"] = presets

        self.profiles.append(new_profile)
        self.save_profiles()

        if self.controller:
            self.controller.go_to_preset_detail(new_profile)

    def activate_preset(self, profile):
        for p in self.profiles:
            if p.get("status") == "active":
                p["status"] = "ready"
        profile["status"] = "active"

        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        settings["active_profile_id"] = profile["id"]
        JsonUtility.save_to_json(SETTINGS_FILE, settings)

        self.save_profiles()
        self.render_list()
        self._show_toast(f"✓ Preset aktif: {profile.get('wo_number', profile.get('name', ''))}")

    def finish_preset(self, profile):
        profile["status"] = "done"
        RecordManager.finalize_record(profile.get("id"))
        self.save_profiles()
        self.render_list()
        self._show_toast("✓ Preset selesai")

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

    def start_active_preset(self):
        active = None
        for p in self.profiles:
            if p.get("status") == "active":
                active = p
                break
        if not active:
            self._show_toast("Tidak ada preset aktif. Pilih preset terlebih dahulu.", is_error=True)
            return
        if self.controller:
            self.controller.go_to_live()

    def fetch_sku_data(self):
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("Syncing...")
        add_log("Starting SKU data fetch from Preset List page...")
        
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
        self.btn_sync.setText("🔄 Sync SKU")

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
