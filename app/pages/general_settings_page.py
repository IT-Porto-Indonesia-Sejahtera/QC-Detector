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
        self.mm_px = QLineEdit(); self.style_input(self.mm_px); p_layout.addWidget(QLabel("MM per Pixel:")); p_layout.addWidget(self.mm_px)
        self.lay_mode = QComboBox(); self.lay_mode.addItems(["Classic", "Split"]); self.style_input(self.lay_mode); p_layout.addWidget(QLabel("Layout Mode:")); p_layout.addWidget(self.lay_mode)
        right.addWidget(p_card)
        
        hw_card, hw_layout = self.create_card("Hardware Integration")
        self.s_port = QLineEdit(); self.style_input(self.s_port); hw_layout.addWidget(QLabel("Sensor Serial Port:")); hw_layout.addWidget(self.s_port)
        self.p_port = QLineEdit(); self.style_input(self.p_port); hw_layout.addWidget(QLabel("PLC Modbus Port:")); hw_layout.addWidget(self.p_port)
        h_regs = QHBoxLayout(); self.p_tri = QLineEdit(); self.style_input(self.p_tri); self.p_res = QLineEdit(); self.style_input(self.p_res)
        h_regs.addWidget(QLabel("Trig Reg:")); h_regs.addWidget(self.p_tri); h_regs.addWidget(QLabel("Res Reg:")); h_regs.addWidget(self.p_res); hw_layout.addLayout(h_regs)
        right.addWidget(hw_card)
        
        btn_save = QPushButton("Save System Settings"); btn_save.setFixedHeight(UIScaling.scale(50)); self.style_button(btn_save, True); btn_save.clicked.connect(self.save_settings)
        right.addWidget(btn_save); right.addStretch()
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

    def load_settings(self):
        s = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        self.mm_px.setText(str(s.get("mm_per_px", 0.21)))
        self.lay_mode.setCurrentIndex(1 if s.get("layout_mode") == "split" else 0)
        self.s_port.setText(s.get("sensor_port", "")); self.p_port.setText(s.get("plc_port", ""))
        self.p_tri.setText(str(s.get("plc_trigger_reg", 12))); self.p_res.setText(str(s.get("plc_result_reg", 13)))
        self.ip_presets = s.get("ip_camera_presets", [])
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

    def save_settings(self):
        s = JsonUtility.load_from_json(SETTINGS_FILE) or {}
        try: s["mm_per_px"] = float(self.mm_px.text())
        except: pass
        s["layout_mode"] = "split" if self.lay_mode.currentIndex() == 1 else "classic"
        cam_data = self.camera_combo.currentData()
        if isinstance(cam_data, str) and cam_data.isdigit():
            s["camera_index"] = int(cam_data)
        else:
            s["camera_index"] = cam_data
            
        s["sensor_port"] = self.s_port.text(); s["plc_port"] = self.p_port.text()
        s["plc_trigger_reg"] = int(self.p_tri.text() or 12); s["plc_result_reg"] = int(self.p_res.text() or 13)
        if s["camera_index"] == "ip":
            pid = self.ip_preset_combo.currentData()
            p = next((x for x in self.ip_presets if x["id"] == pid), None)
            if p:
                p.update({"address": self.ip_addr.text(), "port": self.port.text(), "path": self.path.text(), "username": self.user.text(), "password": self.passwd.text(), "protocol": self.proto.currentText()})
                s["active_ip_preset_id"] = pid
        s["ip_camera_presets"] = self.ip_presets
        JsonUtility.save_to_json(SETTINGS_FILE, s)
        QMessageBox.information(self, "Success", "Settings saved!")
        
        # Navigate to Live Feed after save
        if self.controller:
            self.controller.go_to_live()

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
        self.cap_thread = VideoCaptureThread(source, is_ip)
        self.cap_thread.frame_ready.connect(self.show_frame); self.cap_thread.start()

    def stop_preview(self):
        if self.cap_thread: self.cap_thread.stop(); self.cap_thread = None

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); h, w, ch = rgb.shape
        pix = QPixmap.fromImage(QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888))
        self.preview_box.setPixmap(pix.scaled(self.preview_box.size(), Qt.KeepAspectRatio))

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

    def refresh_data(self):
        self.load_settings()
