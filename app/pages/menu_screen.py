from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

class MenuScreen(QWidget):
    def __init__(self, controller):
        super().__init__(controller)
        self.parent = controller

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("QC Sandal Detection System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; margin-bottom: 40px; color: #333333;")

        photo_btn = QPushButton("📸 Measure by Photo")
        photo_btn.setFixedSize(300, 80)
        photo_btn.setStyleSheet("font-size: 18px; background-color: #F5F5F5; color: #333333; border-radius: 12px; font-weight: bold;")
        photo_btn.clicked.connect(self.parent.go_to_photo)

        video_btn = QPushButton("🎥 Measure by Video")
        video_btn.setFixedSize(300, 80)
        video_btn.setStyleSheet("font-size: 18px; background-color: #F5F5F5; color: #333333; border-radius: 12px; font-weight: bold;")
        video_btn.clicked.connect(self.parent.go_to_video)

        live_btn = QPushButton("🔴 Measure by live")
        live_btn.setFixedSize(300, 80)
        live_btn.setStyleSheet("font-size: 18px; background-color: #F5F5F5; color: #333333; border-radius: 12px; font-weight: bold;")
        live_btn.clicked.connect(self.parent.go_to_live)

        dataset_btn = QPushButton("📂 Capture Dataset")
        dataset_btn.setFixedSize(300, 80)
        dataset_btn.setStyleSheet("font-size: 18px; background-color: #F5F5F5; color: #333333; border-radius: 12px; font-weight: bold;")
        dataset_btn.clicked.connect(self.parent.go_to_dataset)

        layout.addWidget(title)
        layout.addWidget(photo_btn, alignment=Qt.AlignCenter)
        layout.addWidget(video_btn, alignment=Qt.AlignCenter)
        layout.addWidget(live_btn, alignment=Qt.AlignCenter)
        layout.addWidget(dataset_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)
