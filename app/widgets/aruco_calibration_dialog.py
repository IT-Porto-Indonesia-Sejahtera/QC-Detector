from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from app.utils.ui_scaling import UIScaling

class ArucoCalibrationDialog(QDialog):
    def __init__(self, parent, result_data, current_mmpx):
        super().__init__(parent)
        self.setWindowTitle("Auto Calibration Confirmation")
        
        # Scaling
        dialog_w = UIScaling.scale(600)
        dialog_h = UIScaling.scale(550)
        self.setFixedSize(dialog_w, dialog_h)
        
        self.result_data = result_data
        self.new_mmpx = result_data['mm_per_px']
        self.current_mmpx = current_mmpx
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        lbl_title = QLabel("ArUco Detection Successful")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(20)}px; font-weight: bold; color: #4CAF50;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        # Preview Frame
        self.preview_lbl = QLabel()
        self.preview_lbl.setFixedSize(UIScaling.scale(560), UIScaling.scale(320))
        self.preview_lbl.setStyleSheet("background-color: #000; border-radius: 8px;")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_lbl)
        
        # Set the frame
        frame = self.result_data['annotated_frame']
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)
        self.preview_lbl.setPixmap(pixmap.scaled(self.preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Comparison Info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 10px; border: 1px solid #E0E0E0;")
        info_layout = QVBoxLayout(info_frame)
        
        diff = ((self.new_mmpx - self.current_mmpx) / self.current_mmpx) * 100 if self.current_mmpx > 0 else 0
        
        # Tilt Warning
        if self.result_data.get('is_tilted'):
            tilt_lbl = QLabel("⚠️ WARNING: Marker tilt detected. Result may be inaccurate.")
            tilt_lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 11px;")
            tilt_lbl.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(tilt_lbl)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Current Resolution:"))
        val1 = QLabel(f"{self.current_mmpx:.6f} mm/px")
        val1.setStyleSheet("font-weight: bold;")
        row1.addStretch()
        row1.addWidget(val1)
        info_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Detected Resolution:"))
        val2 = QLabel(f"{self.new_mmpx:.6f} mm/px")
        val2.setStyleSheet("font-weight: bold; color: #2196F3;")
        row2.addStretch()
        row2.addWidget(val2)
        info_layout.addLayout(row2)
        
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Difference:"))
        val3 = QLabel(f"{diff:+.2f}%")
        diff_color = "#D32F2F" if abs(diff) > 5 else "#4CAF50"
        val3.setStyleSheet(f"font-weight: bold; color: {diff_color};")
        row3.addStretch()
        row3.addWidget(val3)
        info_layout.addLayout(row3)
        
        layout.addWidget(info_frame)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(UIScaling.scale(40))
        btn_cancel.clicked.connect(self.reject)
        
        btn_apply = QPushButton("Apply & Save")
        btn_apply.setFixedHeight(UIScaling.scale(40))
        btn_apply.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 5px;")
        btn_apply.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_apply)
        layout.addLayout(btn_layout)
        
    def get_result(self):
        return self.new_mmpx
