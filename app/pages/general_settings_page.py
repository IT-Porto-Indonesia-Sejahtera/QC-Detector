import os
import uuid
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from app.utils.theme_manager import ThemeManager
from project_utilities.json_utility import JsonUtility
from app.utils.capture_thread import VideoCaptureThread
from app.utils.ui_scaling import UIScaling
from backend.aruco_utils import detect_aruco_marker
from app.widgets.aruco_calibration_dialog import ArucoCalibrationDialog
from backend.get_product_sku import ProductSKUWorker
from backend.sku_cache import set_sku_data, get_log_text, add_log

SETTINGS_FILE = os.path.join("output", "settings", "app_settings.json")

class GeneralSettingsPage(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.cap_thread = None
        self.ip_presets = []
        
        self.init_ui()
        self.detect_available_cameras()
        self.load_settings()

    def init_ui(self):
        self.init_complete = False
        self.setStyleSheet("background-color: #F2F2F7;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        
        # Header
        header = QFrame(); header.setFixedHeight(UIScaling.scale(80))
        header.setStyleSheet(f"background-color: {self.theme['bg_panel']}; border-bottom: 1px solid {self.theme['border']};")
        h_layout = QHBoxLayout(header); h_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_back = QPushButton("❮ Back"); btn_back.setFixedHeight(UIScaling.scale(40))
        btn_back.setStyleSheet(f"border: none; font-size: {UIScaling.scale_font(16)}px; font-weight: bold; color: {self.theme['text_main']}; background: transparent;")
        btn_back.clicked.connect(self.go_back)
        
        lbl_title = QLabel("System Settings"); lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: bold; color: {self.theme['text_main']};")
        
        h_layout.addWidget(btn_back); h_layout.addSpacing(20); h_layout.addWidget(lbl_title); h_layout.addStretch()
        layout.addWidget(header)
        
        # Scrollable Content
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget(); scroll_layout = QHBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20); scroll_layout.setSpacing(20)
        
        # --- LEFT: Camera ---
        left = QVBoxLayout(); left.setSpacing(20)
        cam_card, cam_layout = self.create_card("Camera Configuration")
        self.preview_box = QLabel("Test Feed"); self.preview_box.setAlignment(Qt.AlignCenter); self.preview_box.setFixedSize(UIScaling.scale(400), UIScaling.scale(250)); self.preview_box.setStyleSheet("background: #2D2D2D; border-radius: 10px; color: #CCC;")
        cam_layout.addWidget(self.preview_box, 0, Qt.AlignCenter)
        self.btn_preview = QPushButton("Start Test Feed"); self.style_button(self.btn_preview, True); self.btn_preview.clicked.connect(self.toggle_preview); cam_layout.addWidget(self.btn_preview)
        
        cam_layout.addWidget(QLabel("Camera Source:"))
        self.camera_combo = QComboBox(); self.camera_combo.addItem("IP Network Camera", "ip"); self.camera_combo.currentIndexChanged.connect(self.on_camera_change); self.style_input(self.camera_combo); cam_layout.addWidget(self.camera_combo)
        left.addWidget(cam_card)
        
        self.ip_section, ip_layout = self.create_card("IP Camera Details")
        h_preset = QHBoxLayout(); self.ip_preset_combo = QComboBox(); self.ip_preset_combo.currentIndexChanged.connect(self.on_ip_preset_change); self.style_input(self.ip_preset_combo); btn_new = QPushButton("+ New"); self.style_button(btn_new); btn_new.clicked.connect(self.add_new_preset)
        h_preset.addWidget(self.ip_preset_combo, 1); h_preset.addWidget(btn_new); ip_layout.addLayout(h_preset)
        self.ip_addr = QLineEdit(); self.style_input(self.ip_addr); ip_layout.addWidget(QLabel("Address")); ip_layout.addWidget(self.ip_addr)
        h_params = QHBoxLayout(); self.proto = QComboBox(); self.proto.addItems(["rtsp", "http"]); self.style_input(self.proto); self.port = QLineEdit(); self.port.setPlaceholderText("554"); self.style_input(self.port)
        h_params.addWidget(QLabel("Proto:")); h_params.addWidget(self.proto); h_params.addWidget(QLabel("Port:")); h_params.addWidget(self.port); ip_layout.addLayout(h_params)
        self.path = QLineEdit(); self.path.setPlaceholderText("/live/ch1"); self.style_input(self.path); ip_layout.addWidget(QLabel("Path")); ip_layout.addWidget(self.path)
        h_auth = QHBoxLayout(); self.user = QLineEdit(); self.user.setPlaceholderText("User"); self.style_input(self.user); self.passwd = QLineEdit(); self.passwd.setEchoMode(QLineEdit.Password); self.passwd.setPlaceholderText("Pass"); self.style_input(self.passwd)
        h_auth.addWidget(self.user); h_auth.addWidget(self.passwd); ip_layout.addLayout(h_auth)
        left.addWidget(self.ip_section); left.addStretch()
        scroll_layout.addLayout(left, 1)
        
        # --- RIGHT: Params & HW ---
        right = QVBoxLayout(); right.setSpacing(20)
        p_card, p_layout = self.create_card("Application Parameters")
        p_layout.addWidget(self.create_styled_label("Resolution (mm/px):"))
        self.mm_px = QLineEdit(); self.style_input(self.mm_px); p_layout.addWidget(self.mm_px)
        
        p_layout.addWidget(self.create_styled_label("Default Detection Model:"))
        self.det_model = QComboBox(); self.det_model.addItem("Standard (Contour)", "standard"); self.det_model.addItem("SAM (AI)", "sam"); self.style_input(self.det_model); p_layout.addWidget(self.det_model)
        
        p_layout.addWidget(self.create_styled_label("Layout Mode:"))
        self.lay_mode = QComboBox(); self.lay_mode.addItems(["Classic", "Split", "Minimal"]); self.style_input(self.lay_mode); p_layout.addWidget(self.lay_mode)
        right.addWidget(p_card)
        
        # Auto Calibration Card
        aruco_card, aruco_layout = self.create_card("Auto Calibration System")
        aruco_layout.addWidget(self.create_styled_label("ArUco Marker Size (mm):"))
        self.marker_size = QLineEdit("50.0"); self.style_input(self.marker_size); aruco_layout.addWidget(self.marker_size)
        
        # Height Correction Fields
        h_height = QHBoxLayout()
        v_h1 = QVBoxLayout(); v_h1.addWidget(self.create_styled_label("Mounting Height (mm)")); self.mount_h = QLineEdit("1000.0"); self.style_input(self.mount_h); v_h1.addWidget(self.mount_h)
        v_h2 = QVBoxLayout(); v_h2.addWidget(self.create_styled_label("Sandal Thickness (mm)")); self.sandal_t = QLineEdit("15.0"); self.style_input(self.sandal_t); v_h2.addWidget(self.sandal_t)
        h_height.addLayout(v_h1); h_height.addLayout(v_h2)
        aruco_layout.addLayout(h_height)
        
        h_ctrl = QHBoxLayout()
        self.btn_calibrate = QPushButton("Run Auto Calibration"); self.style_button(self.btn_calibrate, True); self.btn_calibrate.clicked.connect(self.run_auto_calibration)
        self.btn_debug_aruco = QPushButton("🔍 Debug Off"); self.style_button(self.btn_debug_aruco); self.btn_debug_aruco.setFixedWidth(UIScaling.scale(120))
        self.btn_debug_aruco.clicked.connect(self.toggle_aruco_debug)
        self.aruco_debug_active = False
        
        h_ctrl.addWidget(self.btn_calibrate, 1); h_ctrl.addWidget(self.btn_debug_aruco)
        aruco_layout.addLayout(h_ctrl)
        
        self.calibration_status = QLabel(""); self.calibration_status.setStyleSheet("color: #666; font-size: 11px; background: transparent; border: none;"); aruco_layout.addWidget(self.calibration_status)
        right.addWidget(aruco_card)
        
        # Camera Crop/Zoom Card
        crop_card, crop_layout = self.create_card("Camera Region of Interest")
        crop_layout.addWidget(self.create_styled_label("Crop Left (%):"))
        self.crop_left = QLineEdit("0"); self.style_input(self.crop_left); crop_layout.addWidget(self.crop_left)
        crop_layout.addWidget(self.create_styled_label("Crop Right (%):"))
        self.crop_right = QLineEdit("0"); self.style_input(self.crop_right); crop_layout.addWidget(self.crop_right)
        crop_layout.addWidget(self.create_styled_label("Crop Top (%):"))
        self.crop_top = QLineEdit("0"); self.style_input(self.crop_top); crop_layout.addWidget(self.crop_top)
        self.crop_bottom = QLineEdit("0"); self.style_input(self.crop_bottom); crop_layout.addWidget(self.crop_bottom)
        
        # Rotation
        crop_layout.addWidget(self.create_styled_label("Image Rotation:"))
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["0°", "90° CW", "180°", "90° CCW"])
        self.rotation_combo.setItemData(0, 0); self.rotation_combo.setItemData(1, 90)
        self.rotation_combo.setItemData(2, 180); self.rotation_combo.setItemData(3, 270)
        self.style_input(self.rotation_combo)
        self.rotation_combo.currentIndexChanged.connect(self.update_live_params)
        crop_layout.addWidget(self.rotation_combo)
        
        # Connect crop inputs
        for inp in [self.crop_left, self.crop_right, self.crop_top, self.crop_bottom]:
            inp.textChanged.connect(self.update_live_params)
        
        # Aspect Ratio Correction
        crop_layout.addWidget(self.create_styled_label("Aspect Ratio Correction (e.g. 1.0, 16:9, 4:3):"))
        self.aspect_ratio = QLineEdit("1.0"); self.style_input(self.aspect_ratio); crop_layout.addWidget(self.aspect_ratio)
        
        # Force Resolution
        crop_layout.addWidget(self.create_styled_label("Force Resolution (0 = Auto):"))
        h_res = QHBoxLayout()
        self.force_w = QLineEdit("0"); self.style_input(self.force_w); self.force_w.setPlaceholderText("Width")
        self.force_h = QLineEdit("0"); self.style_input(self.force_h); self.force_h.setPlaceholderText("Height")
        h_res.addWidget(self.create_styled_label("W:")); h_res.addWidget(self.force_w)
        h_res.addWidget(self.create_styled_label("H:")); h_res.addWidget(self.force_h)
        crop_layout.addLayout(h_res)
        
        right.addWidget(crop_card)

        # Lens Distortion Card
        dist_card, dist_layout = self.create_card("Lens Distortion Correction")
        
        # Preset Combo
        dist_layout.addWidget(self.create_styled_label("Distortion Profile:"))
        self.dist_preset = QComboBox()
        self.dist_preset.addItems(["Custom", "No Distortion (Default)", "Mild Barrel (Standard Webcam)", "Medium Barrel (Wide Lens)", "Strong Barrel (Fisheye)"])
        self.style_input(self.dist_preset)
        self.dist_preset.currentIndexChanged.connect(self.on_dist_preset_change)
        dist_layout.addWidget(self.dist_preset)
        
        # Coefficients
        dist_layout.addWidget(self.create_styled_label("Advanced Parameters:"))
        h_k = QHBoxLayout()
        v_k1 = QVBoxLayout(); v_k1.addWidget(self.create_styled_label("k1 (Main Curvature)")); self.k1 = QLineEdit("0.0"); self.style_input(self.k1); v_k1.addWidget(self.k1)
        v_k2 = QVBoxLayout(); v_k2.addWidget(self.create_styled_label("k2 (Detail)")); self.k2 = QLineEdit("0.0"); self.style_input(self.k2); v_k2.addWidget(self.k2)
        v_p1 = QVBoxLayout(); v_p1.addWidget(self.create_styled_label("p1 (Tangential)")); self.p1 = QLineEdit("0.0"); self.style_input(self.p1); v_p1.addWidget(self.p1)
        h_k.addLayout(v_k1); h_k.addLayout(v_k2); h_k.addLayout(v_p1)
        dist_layout.addLayout(h_k)
        
        h_k2 = QHBoxLayout()
        v_p2 = QVBoxLayout(); v_p2.addWidget(self.create_styled_label("p2 (Tangential)")); self.p2 = QLineEdit("0.0"); self.style_input(self.p2); v_p2.addWidget(self.p2)
        v_k3 = QVBoxLayout(); v_k3.addWidget(self.create_styled_label("k3 (Higher Order)")); self.k3 = QLineEdit("0.0"); self.style_input(self.k3); v_k3.addWidget(self.k3)
        h_k2.addLayout(v_p2); h_k2.addLayout(v_k3); h_k2.addStretch()
        dist_layout.addLayout(h_k2)

        # Camera Matrix
        dist_layout.addWidget(self.create_styled_label("Camera Matrix (Advanced):"))
        hbox_cam = QHBoxLayout()
        self.btn_auto_matrix = QPushButton("Auto-Estimate Matrix: OFF")
        self.btn_auto_matrix.setCheckable(True)
        self.style_button(self.btn_auto_matrix)
        self.btn_auto_matrix.setToolTip("Enable to automatically estimate center and focal length from resolution")
        self.btn_auto_matrix.clicked.connect(self.on_auto_matrix_toggle)
        hbox_cam.addWidget(self.btn_auto_matrix)
        dist_layout.addLayout(hbox_cam)

        h_mat = QHBoxLayout()
        v_fx = QVBoxLayout(); v_fx.addWidget(self.create_styled_label("fx")); self.fx = QLineEdit("0.0"); self.style_input(self.fx); v_fx.addWidget(self.fx)
        v_fy = QVBoxLayout(); v_fy.addWidget(self.create_styled_label("fy")); self.fy = QLineEdit("0.0"); self.style_input(self.fy); v_fy.addWidget(self.fy)
        v_cx = QVBoxLayout(); v_cx.addWidget(self.create_styled_label("cx")); self.cx = QLineEdit("0.0"); self.style_input(self.cx); v_cx.addWidget(self.cx)
        v_cy = QVBoxLayout(); v_cy.addWidget(self.create_styled_label("cy")); self.cy = QLineEdit("0.0"); self.style_input(self.cy); v_cy.addWidget(self.cy)
        h_mat.addLayout(v_fx); h_mat.addLayout(v_fy); h_mat.addLayout(v_cx); h_mat.addLayout(v_cy)
        dist_layout.addLayout(h_mat)
        
        right.addWidget(dist_card)
        
        hw_card, hw_layout = self.create_card("Hardware Integration")
        hw_layout.addWidget(self.create_styled_label("Sensor Serial Port:"))
        self.s_port = QLineEdit(); self.style_input(self.s_port); hw_layout.addWidget(self.s_port)
        hw_layout.addWidget(self.create_styled_label("PLC Modbus Port:"))
        self.p_port = QLineEdit(); self.style_input(self.p_port); hw_layout.addWidget(self.p_port)
        h_regs = QHBoxLayout()
        v_trig = QVBoxLayout(); v_trig.addWidget(self.create_styled_label("Trig Reg:")); self.p_tri = QLineEdit(); self.style_input(self.p_tri); v_trig.addWidget(self.p_tri)
        v_res = QVBoxLayout(); v_res.addWidget(self.create_styled_label("Res Reg:")); self.p_res = QLineEdit(); self.style_input(self.p_res); v_res.addWidget(self.p_res)
        h_regs.addLayout(v_trig); h_regs.addLayout(v_res); hw_layout.addLayout(h_regs)
        right.addWidget(hw_card)
        
        # Developer Tools Card (Hidden Features)
        dev_card, dev_layout = self.create_card("Developer Tools")
        btn_dataset = QPushButton("📷  Capture Dataset"); self.style_button(btn_dataset)
        btn_dataset.clicked.connect(self.go_to_dataset); dev_layout.addWidget(btn_dataset)
        btn_photo = QPushButton("🖼️  Measure by Photo"); self.style_button(btn_photo)
        btn_photo.clicked.connect(self.go_to_photo); dev_layout.addWidget(btn_photo)
        right.addWidget(dev_card)
        
        # Database Sync Card
        sync_card, sync_layout = self.create_card("Database Sync")
        sync_layout.addWidget(self.create_styled_label("Fetch product SKU data from database:"))
        self.btn_fetch_sku = QPushButton("🔄 Fetch SKU Data"); self.style_button(self.btn_fetch_sku, True)
        self.btn_fetch_sku.clicked.connect(self.fetch_sku_data)
        sync_layout.addWidget(self.btn_fetch_sku)
        
        sync_layout.addWidget(self.create_styled_label("Sync Log:"))
        from PySide6.QtWidgets import QTextEdit
        self.log_display = QTextEdit(); self.log_display.setReadOnly(True)
        self.log_display.setFixedHeight(UIScaling.scale(120))
        self.log_display.setStyleSheet(f"background: #1C1C1E; color: #00FF00; font-family: monospace; font-size: {UIScaling.scale_font(11)}px; padding: 8px; border-radius: 8px;")
        sync_layout.addWidget(self.log_display)
        right.addWidget(sync_card)
        
        h_save_btns = QHBoxLayout()
        btn_apply = QPushButton("Quick Apply"); btn_apply.setFixedHeight(UIScaling.scale(50)); self.style_button(btn_apply); btn_apply.clicked.connect(self.apply_quick_settings)
        btn_save = QPushButton("Save & Exit"); btn_save.setFixedHeight(UIScaling.scale(50)); self.style_button(btn_save, True); btn_save.clicked.connect(self.save_settings)
        h_save_btns.addWidget(btn_apply); h_save_btns.addWidget(btn_save)
        right.addLayout(h_save_btns); right.addStretch()
        scroll_layout.addLayout(right, 1)

        
        scroll.setWidget(scroll_content); layout.addWidget(scroll)

    def create_card(self, title):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setStyleSheet("""
            QFrame#cardFrame {
                background: white; 
                border-radius: 12px; 
                border: 1px solid #E0E0E0;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(12)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet("color: #007AFF; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; border: none !important; background: transparent !important;")
        l.addWidget(lbl)
        return card, l

    def create_styled_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #1C1C1E; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        return lbl

    def style_button(self, btn, primary=False):
        bg = "#007AFF" if primary else "#E8E8ED"
        fg = "white" if primary else "#007AFF"
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; 
                color: {fg}; 
                border-radius: 8px; 
                padding: 12px; 
                font-weight: bold; 
                font-size: {UIScaling.scale_font(14)}px; 
                border: none;
            }}
            QPushButton:hover {{
                background-color: {"#005BB5" if primary else "#D1D1D6"};
            }}
        """)

    def style_input(self, widget):
        # Use class-specific selector to prevent inheritance to child widgets/labels
        cls = widget.__class__.__name__
        widget.setStyleSheet(f"""
            {cls} {{
                border: 1px solid #D1D1D6; 
                border-radius: 8px; 
                padding: 10px; 
                background: white; 
                color: #1C1C1E;
                font-size: {UIScaling.scale_font(14)}px;
            }}
            {cls}:focus {{
                border: 2px solid #007AFF;
                padding: 9px;
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
        """)
        # Connect to live update handler if not a combo (combos connected separately)
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self.update_live_params)




    def load_settings(self):
        s = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        self.mm_px.setText(str(s.get("mm_per_px", 0.21)))
        # Layout mode: 0=Classic, 1=Split, 2=Minimal
        layout_mode = s.get("layout_mode", "classic")
        if layout_mode == "split": self.lay_mode.setCurrentIndex(1)
        elif layout_mode == "minimal": self.lay_mode.setCurrentIndex(2)
        else: self.lay_mode.setCurrentIndex(0)
        self.s_port.setText(s.get("sensor_port", "")); self.p_port.setText(s.get("plc_port", ""))
        self.p_tri.setText(str(s.get("plc_trigger_reg", 12))); self.p_res.setText(str(s.get("plc_result_reg", 13)))
        
        det_mode = s.get("detection_model", "standard")
        self.det_model.setCurrentIndex(self.det_model.findData(det_mode))
        
        self.ip_presets = s.get("ip_camera_presets", [])
        self.marker_size.setText(str(s.get("aruco_marker_size", 50.0)))
        self.mount_h.setText(str(s.get("mounting_height", 1000.0)))
        self.sandal_t.setText(str(s.get("sandal_thickness", 15.0)))
        # Load crop settings
        crop = s.get("camera_crop", {})
        self.crop_left.setText(str(crop.get("left", 0)))
        self.crop_right.setText(str(crop.get("right", 0)))
        self.crop_top.setText(str(crop.get("top", 0)))
        self.crop_bottom.setText(str(crop.get("bottom", 0)))
        
        # Load Rotation
        rot_val = crop.get("rotation", 0)
        idx = self.rotation_combo.findData(rot_val)
        if idx != -1: self.rotation_combo.setCurrentIndex(idx)
        
        # Load Aspect Ratio
        self.aspect_ratio.setText(str(s.get("aspect_ratio_correction", 1.0)))
        
        # Load Force Resolution
        self.force_w.setText(str(s.get("force_width", 0)))
        self.force_h.setText(str(s.get("force_height", 0)))

        # Load distortion settings
        dist = s.get("lens_distortion", {})
        self.k1.setText(str(dist.get("k1", 0.0)))
        self.k2.setText(str(dist.get("k2", 0.0)))
        self.p1.setText(str(dist.get("p1", 0.0)))
        self.p2.setText(str(dist.get("p2", 0.0)))
        self.k3.setText(str(dist.get("k3", 0.0)))
        self.fx.setText(str(dist.get("fx", 0.0)))
        self.fy.setText(str(dist.get("fy", 0.0)))
        self.cx.setText(str(dist.get("cx", 0.0)))
        self.cy.setText(str(dist.get("cy", 0.0)))

        # Load Auto-Matrix state
        is_auto = s.get("auto_estimate_matrix", False)
        self.btn_auto_matrix.setChecked(is_auto)
        self.update_auto_matrix_ui(is_auto)

        self.update_preset_combo()
        cam_idx = s.get("camera_index", 0)
        if cam_idx == "ip": 
            self.camera_combo.setCurrentIndex(self.camera_combo.findData("ip"))
        else:
            if self.camera_combo.findData(cam_idx) == -1: 
                self.camera_combo.insertItem(0, f"USB Camera {cam_idx}", cam_idx)
            self.camera_combo.setCurrentIndex(self.camera_combo.findData(cam_idx))
            
        # Select active IP preset
        self.active_ip_preset_id = s.get("active_ip_preset_id")
        if self.active_ip_preset_id:
            idx = self.ip_preset_combo.findData(self.active_ip_preset_id)
            if idx != -1: 
                self.ip_preset_combo.setCurrentIndex(idx)
                self.on_ip_preset_change()

        self.init_complete = True

    def update_live_params(self):
        """Update running capture thread with current UI values"""
        if not self.cap_thread or not self.cap_thread.isRunning():
            return
            
        try:
            # Gather crop params
            crop = {
                "left": int(self.crop_left.text() or 0),
                "right": int(self.crop_right.text() or 0),
                "top": int(self.crop_top.text() or 0),
                "bottom": int(self.crop_bottom.text() or 0),
                "rotation": self.rotation_combo.currentData()
            }
            
            # Gather distortion params
            dist = {
                "k1": float(self.k1.text() or 0),
                "k2": float(self.k2.text() or 0),
                "p1": float(self.p1.text() or 0),
                "p2": float(self.p2.text() or 0),
                "k3": float(self.k3.text() or 0),
                "fx": float(self.fx.text() or 0),
                "fy": float(self.fy.text() or 0),
                "cx": float(self.cx.text() or 0),
                "cy": float(self.cy.text() or 0)
            }
            
            # Gather aspect ratio
            aspect_input = self.aspect_ratio.text() 
            aspect = self.parse_aspect_ratio_input(aspect_input)
            
            self.cap_thread.update_params(crop_params=crop, distortion_params=dist, aspect_ratio_correction=aspect)
        except Exception as e:
            print(f"Error updating live params: {e}")

    def update_preset_combo(self):
        self.ip_preset_combo.clear()
        for p in self.ip_presets: self.ip_preset_combo.addItem(p.get("name"), p.get("id"))

    def on_ip_preset_change(self):
        pid = self.ip_preset_combo.currentData()
        p = next((x for x in self.ip_presets if x["id"] == pid), None)
        if p:
            self.ip_addr.setText(p.get("address", "")); self.port.setText(p.get("port", "")); self.path.setText(p.get("path", ""))
            self.user.setText(p.get("username", "")); self.passwd.setText(p.get("password", ""))
            self.proto.setCurrentText(p.get("protocol", "rtsp"))

    def add_new_preset(self):
        new_p = {"id": str(uuid.uuid4()), "name": f"Camera {len(self.ip_presets)+1}", "protocol": "rtsp", "address": "", "port": "554", "path": "", "username": "", "password": ""}
        self.ip_presets.append(new_p); self.update_preset_combo(); self.ip_preset_combo.setCurrentIndex(len(self.ip_presets)-1)

    def on_camera_change(self):
        self.ip_section.setVisible(self.camera_combo.currentData() == "ip")

    def apply_quick_settings(self):
        """Save settings without leaving the page"""
        try:
            settings_dict = self._gather_settings_dict()
            JsonUtility.save_to_json(SETTINGS_FILE, settings_dict)
            self.calibration_status.setText("Settings applied and saved!")
            self.calibration_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            # Show a temporary message
            QMessageBox.information(self, "Success", "Settings applied successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")

    def save_settings(self):
        """Save settings and return to live feed"""
        try:
            settings_dict = self._gather_settings_dict()
            JsonUtility.save_to_json(SETTINGS_FILE, settings_dict)
            QMessageBox.information(self, "Success", "Settings saved!")
            
            # Navigate to Live Feed after save
            if self.controller:
                self.controller.go_to_live()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def _gather_settings_dict(self):
        """Helper to collect all UI values into a settings dictionary"""
        s = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        try: s["mm_per_px"] = float(self.mm_px.text())
        except: pass
        # Layout mode: 0=Classic, 1=Split, 2=Minimal
        layout_idx = self.lay_mode.currentIndex()
        s["layout_mode"] = ["classic", "split", "minimal"][layout_idx]
        cam_data = self.camera_combo.currentData()
        if isinstance(cam_data, str) and cam_data.isdigit():
            s["camera_index"] = int(cam_data)
        else:
            s["camera_index"] = cam_data
            
        s["sensor_port"] = self.s_port.text(); s["plc_port"] = self.p_port.text()
        s["plc_trigger_reg"] = int(self.p_tri.text() or 12); s["plc_result_reg"] = int(self.p_res.text() or 13)
        s["detection_model"] = self.det_model.currentData()
        if s["camera_index"] == "ip":
            pid = self.ip_preset_combo.currentData()
            p = next((x for x in self.ip_presets if x["id"] == pid), None)
            if p:
                p.update({"address": self.ip_addr.text(), "port": self.port.text(), "path": self.path.text(), "username": self.user.text(), "password": self.passwd.text(), "protocol": self.proto.currentText()})
                s["active_ip_preset_id"] = pid
        s["ip_camera_presets"] = self.ip_presets
        # Save ArUco marker size & Heights
        try: 
            s["aruco_marker_size"] = float(self.marker_size.text())
            s["mounting_height"] = float(self.mount_h.text())
            s["sandal_thickness"] = float(self.sandal_t.text())
        except: pass
        # Save crop settings
        s["camera_crop"] = {
            "left": int(self.crop_left.text() or 0),
            "right": int(self.crop_right.text() or 0),
            "top": int(self.crop_top.text() or 0),
            "bottom": int(self.crop_bottom.text() or 0),
            "rotation": self.rotation_combo.currentData()
        }
        
        # Save aspect ratio
        try: 
            aspect_input = self.aspect_ratio.text()
            s["aspect_ratio_correction"] = self.parse_aspect_ratio_input(aspect_input)
        except: 
            s["aspect_ratio_correction"] = 1.0
            
        # Save Force Resolution
        try:
            s["force_width"] = int(self.force_w.text() or 0)
            s["force_height"] = int(self.force_h.text() or 0)
        except:
            s["force_width"] = 0
            s["force_height"] = 0
        
        # Save distortion settings
        try:
            s["lens_distortion"] = {
                "k1": float(self.k1.text() or 0),
                "k2": float(self.k2.text() or 0),
                "p1": float(self.p1.text() or 0),
                "p2": float(self.p2.text() or 0),
                "k3": float(self.k3.text() or 0),
                "fx": float(self.fx.text() or 0),
                "fy": float(self.fy.text() or 0),
                "cx": float(self.cx.text() or 0),
                "cy": float(self.cy.text() or 0)
            }
        except:
             pass 

        s["auto_estimate_matrix"] = self.btn_auto_matrix.isChecked()
             
        return s

    def toggle_preview(self):
        if self.cap_thread: self.stop_preview(); self.btn_preview.setText("Start Test Feed")
        else: self.start_preview(); self.btn_preview.setText("Stop Test Feed")

    def start_preview(self):
        source = self.camera_combo.currentData()
        is_ip = (source == "ip")
        if is_ip:
            pid = self.ip_preset_combo.currentData()
            source = next((x for x in self.ip_presets if x["id"] == pid), None)
            if not source: return
            
        settings = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        crop = settings.get("camera_crop", {})
        distortion = settings.get("lens_distortion", {})
        
        crop = settings.get("camera_crop", {})
        distortion = settings.get("lens_distortion", {})
        aspect = settings.get("aspect_ratio_correction", 1.0)
        fw = settings.get("force_width", 0)
        fh = settings.get("force_height", 0)
        
        self.cap_thread = VideoCaptureThread(source, is_ip, crop_params=crop, distortion_params=distortion, aspect_ratio_correction=aspect, force_width=fw, force_height=fh)
        self.cap_thread.frame_ready.connect(self.show_frame); self.cap_thread.start()

    def stop_preview(self):
        if self.cap_thread: self.cap_thread.stop(); self.cap_thread = None

    def show_frame(self, frame):
        out_frame = frame
        if hasattr(self, 'aruco_debug_active') and self.aruco_debug_active:
            try:
                ms = float(self.marker_size.text() or 50.0)
                success, res = detect_aruco_marker(frame, ms)
                if success:
                    out_frame = res['annotated_frame']
                    count = res.get('marker_count', 1)
                    tilt_txt = ' (TILTED!)' if res.get('is_tilted') else ''
                    self.calibration_status.setText(f"Live: {res['mm_per_px']:.6f} mm/px | {count} markers{tilt_txt}")
                    self.calibration_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
                else:
                    self.calibration_status.setText(f"Searching: {res['error']}")
                    self.calibration_status.setStyleSheet("color: #666;")
            except Exception as e:
                self.calibration_status.setText(f"Error: {str(e)[:50]}")

        rgb = cv2.cvtColor(out_frame, cv2.COLOR_BGR2RGB); h, w, ch = rgb.shape
        pix = QPixmap.fromImage(QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888))
        self.preview_box.setPixmap(pix.scaled(self.preview_box.size(), Qt.KeepAspectRatio))

    def toggle_aruco_debug(self):
        self.aruco_debug_active = not self.aruco_debug_active
        if self.aruco_debug_active:
            self.btn_debug_aruco.setText("🔍 Debug On")
            self.btn_debug_aruco.setStyleSheet(self.btn_debug_aruco.styleSheet().replace("#E8E8ED", "#FF9800").replace("#007AFF", "white"))
            self.calibration_status.setText("ArUco Debug Mode Active")
        else:
            self.btn_debug_aruco.setText("🔍 Debug Off")
            self.style_button(self.btn_debug_aruco)
            self.calibration_status.setText("")


    def go_back(self):
        self.stop_preview()
        if self.controller:
            self.controller.go_back()

    def detect_available_cameras(self):
        # Scan for USB cameras
        for i in range(5): # Check first 5 indices
             cap = cv2.VideoCapture(i)
             if cap.isOpened():
                 if self.camera_combo.findData(i) == -1:
                     self.camera_combo.insertItem(0, f"USB Camera {i}", i)
                 cap.release()

    def go_to_dataset(self):
        self.stop_preview()
        if self.controller:
            self.controller.go_to_dataset()

    def go_to_photo(self):
        self.stop_preview()
        if self.controller:
            self.controller.go_to_photo()

    def refresh_data(self):
        self.load_settings()

    def run_auto_calibration(self):
        """Run ArUco-based auto calibration for mm/px"""
        if self.cap_thread is None or not self.cap_thread.isRunning():
            self.calibration_status.setText("Error: Start camera first")
            self.calibration_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return
        
        try:
            marker_size_mm = float(self.marker_size.text())
            if marker_size_mm <= 0: raise ValueError
        except ValueError:
            self.calibration_status.setText("Error: Invalid marker size")
            self.calibration_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return
        
        frame = getattr(self.cap_thread, 'last_frame', None)
        if frame is None:
            self.calibration_status.setText("Error: No frame from camera")
            self.calibration_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            return
        
        self.btn_calibrate.setEnabled(False)
        self.btn_calibrate.setText("Detecting...")
        
        success, result = detect_aruco_marker(frame, marker_size_mm)
        
        if not success:
            self.calibration_status.setText(f"Error: {result['error']}")
            self.calibration_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
            self.btn_calibrate.setEnabled(True)
            self.btn_calibrate.setText("Run Auto Calibration")
            return
        
        count = result.get('marker_count', 1)
        stability = result.get('stability', 100)
        self.calibration_status.setText(f"Detected {count} marker(s) | Stability: {stability:.1f}%")
        self.calibration_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

        
        try:
            current_mmpx = float(self.mm_px.text() or 0.21)
        except:
            current_mmpx = 0.21
        
        dialog = ArucoCalibrationDialog(self, result, current_mmpx)
        if dialog.exec():
            new_mmpx = dialog.get_result()
            self.mm_px.setText(f"{new_mmpx:.8f}")
            self.calibration_status.setText(f"Calibrated: {new_mmpx:.6f} mm/px")
            self.calibration_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.calibration_status.setText("Cancelled")
            self.calibration_status.setStyleSheet("color: #666;")
        
        self.btn_calibrate.setEnabled(True)
        self.btn_calibrate.setText("Run Auto Calibration")

    def on_dist_preset_change(self):
        txt = self.dist_preset.currentText()
        if "No Distortion" in txt:
            self.k1.setText("0.0"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Mild Barrel" in txt:
            self.k1.setText("-0.08"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Medium Barrel" in txt:
            self.k1.setText("-0.15"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Strong Barrel" in txt:
            self.k1.setText("-0.35"); self.k2.setText("0.0"); self.p1.setText("0.0"); self.p2.setText("0.0"); self.k3.setText("0.0")
        elif "Custom" in txt:
            pass
            
        if hasattr(self, 'init_complete') and self.init_complete:
            self.update_live_params()

    def parse_aspect_ratio_input(self, text):
        """Parse text input like '16:9', '16/9', '1.77' into a float"""
        if not text: return 1.0
        try:
            # Handle fraction (colon or slash)
            if ':' in text:
                parts = text.split(':')
                if len(parts) == 2:
                    return float(parts[0]) / float(parts[1])
            elif '/' in text:
                parts = text.split('/')
                if len(parts) == 2:
                    return float(parts[0]) / float(parts[1])
            
            # Handle direct float
            return float(text)
        except:
            return 1.0

    def on_auto_matrix_toggle(self, checked):
        if checked:
            # Clear fields and disable
            self.fx.setText("0.0"); self.fy.setText("0.0"); self.cx.setText("0.0"); self.cy.setText("0.0")
        
        self.update_auto_matrix_ui(checked)
        self.update_live_params()

    def update_auto_matrix_ui(self, is_auto):
        if is_auto:
            self.btn_auto_matrix.setText("Auto-Estimate Matrix: ON")
            self.btn_auto_matrix.setStyleSheet(self.btn_auto_matrix.styleSheet().replace("#E8E8ED", "#4CAF50").replace("#007AFF", "white"))
        else:
            self.btn_auto_matrix.setText("Auto-Estimate Matrix: OFF")
            self.style_button(self.btn_auto_matrix)
            
        # Disable/Enable manual fields
        for field in [self.fx, self.fy, self.cx, self.cy]:
            field.setReadOnly(is_auto)
            field.setEnabled(not is_auto)
            if is_auto:
                field.setStyleSheet(field.styleSheet().replace("background: white", f"background: {self.theme['bg_panel']}"))
            else:
                field.setStyleSheet(field.styleSheet().replace(f"background: {self.theme['bg_panel']}", "background: white"))

    def fetch_sku_data(self):
        """Fetch product SKU data from database asynchronously."""
        # Update UI
        self.btn_fetch_sku.setEnabled(False)
        self.btn_fetch_sku.setText("Fetching...")
        add_log("Starting SKU data fetch...")
        self._update_log_display()
        
        # Create worker
        self.sku_worker = ProductSKUWorker()
        self.sku_worker.finished.connect(self._on_sku_fetch_success)
        self.sku_worker.error.connect(self._on_sku_fetch_error)
        self.sku_worker.start()

    def _on_sku_fetch_success(self, data):
        """Handle successful SKU fetch."""
        if data:
            set_sku_data(data)
            add_log(f"SUCCESS: Fetched {len(data)} products from database.")
            
            # Log sample data
            if len(data) > 0:
                sample = data[0]
                add_log(f"Sample: {sample.get('Nama Produk', 'N/A')[:30]}...")
        else:
            add_log("WARNING: Query returned 0 results.")
        
        self._reset_fetch_button()
        self._update_log_display()

    def _on_sku_fetch_error(self, error_msg):
        """Handle SKU fetch error."""
        add_log(f"ERROR: {error_msg}")
        self._reset_fetch_button()
        self._update_log_display()

    def _reset_fetch_button(self):
        """Reset fetch button to default state."""
        self.btn_fetch_sku.setEnabled(True)
        self.btn_fetch_sku.setText("🔄 Fetch SKU Data")

    def _update_log_display(self):
        """Update the log display text area."""
        self.log_display.setText(get_log_text())
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
