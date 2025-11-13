import cv2
import os
import threading
import project_utilities as putils
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from model.measurement_video import process_video
from model.preprocessor import ensure_dir


class MeasureVideoScreen(QWidget):
    def __init__(self, controller):
        super().__init__(controller)
        self.parent = controller
        self.setStyleSheet("background-color: #111; color: white;")

        layout = QVBoxLayout(self)

        self.video_label = QLabel("No video loaded.")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background: black; border: 2px dashed #555;")
        layout.addWidget(self.video_label)

        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Video")
        self.start_btn = QPushButton("Start Processing")
        self.back_btn = QPushButton("Back")
        self.start_btn.setEnabled(False)

        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.back_btn)
        layout.addLayout(btn_layout)

        self.load_btn.clicked.connect(self.load_video)
        self.start_btn.clicked.connect(self.start_processing)
        self.back_btn.clicked.connect(lambda: self.parent.go_back())

        self.video_path = None
        self.running = False

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.avi *.mp4)")
        if file_path:
            self.video_path = file_path
            self.video_label.setText(f"Loaded: {os.path.basename(file_path)}")
            self.start_btn.setEnabled(True)

    def start_processing(self):
        if not self.video_path:
            return
        threading.Thread(target=self.process_video_thread, daemon=True).start()

    def process_video_thread(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.video_label.setText("Failed to open video.")
            return

        mm_per_px = None
        self.running = True

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            results, processed = process_video(frame, mm_per_px, draw_output=False)

            rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img).scaled(960, 540, Qt.KeepAspectRatio)
            self.video_label.setPixmap(pixmap)

            cv2.waitKey(10)

        cap.release()
        self.video_label.setText("Video processing complete.")
