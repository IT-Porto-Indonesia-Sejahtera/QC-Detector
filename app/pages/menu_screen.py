from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from app.utils.ui_scaling import UIScaling

class MenuScreen(QWidget):
    def __init__(self, controller):
        super().__init__(controller)
        self.parent = controller

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title_font_size = UIScaling.scale_font(28)
        title = QLabel("QC Sandal Detection System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; margin-bottom: 20px; color: #333333;")

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(UIScaling.scale(20))

        btn_font_size = UIScaling.scale_font(18)
        btn_padding = UIScaling.scale(15)
        btn_radius = UIScaling.scale(12)
        
        button_style = f"""
            QPushButton {{
                font-size: {btn_font_size}px; 
                background-color: #F5F5F5; 
                color: #333333; 
                border-radius: {btn_radius}px; 
                font-weight: bold;
                padding: {btn_padding}px;
            }}
            QPushButton:hover {{
                background-color: #E0E0E0;
            }}
        """

        btn_min_w = UIScaling.scale(300)
        btn_min_h = UIScaling.scale(60)
        btn_max_w = UIScaling.scale(500)

        photo_btn = QPushButton("📸 Measure by Photo")
        photo_btn.setMinimumSize(btn_min_w, btn_min_h)
        photo_btn.setMaximumWidth(btn_max_w)
        photo_btn.setStyleSheet(button_style)
        photo_btn.clicked.connect(self.parent.go_to_photo)

        video_btn = QPushButton("🎥 Measure by Video")
        video_btn.setMinimumSize(btn_min_w, btn_min_h)
        video_btn.setMaximumWidth(btn_max_w)
        video_btn.setStyleSheet(button_style)
        video_btn.clicked.connect(self.parent.go_to_video)

        live_btn = QPushButton("🔴 Measure by live")
        live_btn.setMinimumSize(btn_min_w, btn_min_h)
        live_btn.setMaximumWidth(btn_max_w)
        live_btn.setStyleSheet(button_style)
        live_btn.clicked.connect(self.parent.go_to_live)

        dataset_btn = QPushButton("📂 Capture Dataset")
        dataset_btn.setMinimumSize(btn_min_w, btn_min_h)
        dataset_btn.setMaximumWidth(btn_max_w)
        dataset_btn.setStyleSheet(button_style)
        dataset_btn.clicked.connect(self.parent.go_to_dataset)

        layout.addWidget(photo_btn, alignment=Qt.AlignCenter)
        layout.addWidget(video_btn, alignment=Qt.AlignCenter)
        layout.addWidget(live_btn, alignment=Qt.AlignCenter)
        layout.addWidget(dataset_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.setLayout(layout)
