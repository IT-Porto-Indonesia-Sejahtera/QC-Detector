from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QPoint, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPalette, QBrush, QPen
from app.widgets.base_overlay import BaseOverlay
from app.utils.ui_scaling import UIScaling

class SlideArrows(QLabel):
    """Animated arrows for the slider."""
    def __init__(self, parent=None):
        super().__init__(">>", parent)
        self.setStyleSheet(f"color: #D97706; font-weight: 800; font-size: {UIScaling.scale_font(18)}px; background: transparent; border: none;")
        self.setFixedWidth(UIScaling.scale(40))
        self.setAlignment(Qt.AlignCenter)
        
        # Pulse Animation
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(1200)
        self.anim.setStartValue(160) # Opacity start (slightly darker for light mode)
        self.anim.setEndValue(255)   # Opacity end
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.valueChanged.connect(self.update_opacity)
        self.anim.start()

    def update_opacity(self, value):
        self.setStyleSheet(f"color: rgba(217, 119, 6, {value}); font-weight: 800; font-size: {UIScaling.scale_font(18)}px; background: transparent; border: none;")

class SlideSwitch(QFrame):
    """Custom slider-to-confirm widget with ultra-premium feel."""
    confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(UIScaling.scale(74))
        self.setFixedWidth(UIScaling.scale(360))
        
        # Transparent background, custom paintEvent handles the track
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        
        # Container for labels/arrows to keep them centered in the track
        self.inner_container = QWidget(self)
        self.inner_container.setGeometry(UIScaling.scale(4), UIScaling.scale(4), self.width() - UIScaling.scale(8), self.height() - UIScaling.scale(8))
        self.inner_container.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        inner_layout = QHBoxLayout(self.inner_container)
        inner_layout.setContentsMargins(UIScaling.scale(80), 0, 0, 0)
        inner_layout.setSpacing(UIScaling.scale(10))
        
        self.arrows = SlideArrows()
        inner_layout.addWidget(self.arrows)
        
        self.lbl_text = QLabel("Geser untuk Konfirmasi")
        self.lbl_text.setStyleSheet(f"color: #4B5563; font-weight: 700; font-size: {UIScaling.scale_font(15)}px; background: transparent; border: none;")
        inner_layout.addWidget(self.lbl_text)
        inner_layout.addStretch()
        
        # Handle
        self.handle = QFrame(self)
        self.handle_size = UIScaling.scale(64)
        self.handle.setFixedSize(self.handle_size, self.handle_size)
        self.handle_radius = self.handle_size // 2
        
        self.update_handle_style("#F59E0B", "#D97706")
        
        # Handle Icon
        self.handle_icon = QLabel("✓", self.handle)
        self.handle_icon.setAlignment(Qt.AlignCenter)
        self.handle_icon.setStyleSheet(f"color: white; font-weight: 900; font-size: {UIScaling.scale_font(26)}px; background: transparent;")
        self.handle_icon.setGeometry(0, 0, self.handle_size, self.handle_size)
        
        # Position handle
        self.padding = UIScaling.scale(5)
        self.handle_pos_x = self.padding
        self.handle.move(self.handle_pos_x, self.padding)
        
        # Handle Shadow (More intense for premium look)
        self.h_shadow = QGraphicsDropShadowEffect(self.handle)
        self.h_shadow.setBlurRadius(20)
        self.h_shadow.setXOffset(0)
        self.h_shadow.setYOffset(4)
        self.h_shadow.setColor(QColor(0, 0, 0, 180))
        self.handle.setGraphicsEffect(self.h_shadow)
        
        self.is_dragging = False
        self.drag_start_x = 0
        self.max_x = self.width() - self.handle_size - self.padding
        self.is_confirmed = False

    def update_handle_style(self, color_top, color_bottom):
        self.handle.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color_top}, stop:1 {color_bottom});
                border-radius: {self.handle_radius}px;
                border: 2px solid rgba(255, 255, 255, 0.4);
            }}
        """)

    def paintEvent(self, event):
        """Draw the recessed track for light mode."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        radius = rect.height() / 2
        
        # 1. Outer track border (Soft gray)
        painter.setPen(QPen(QColor(229, 231, 235), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)
        
        # 2. Main track background (Recessed gray)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(243, 244, 246))) # Light gray recessed
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)
        
        # 3. Inner shadow (Darker at top for depth)
        painter.setPen(QPen(QColor(0, 0, 0, 15), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -1, -1), radius, radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.handle.geometry().contains(event.pos()):
            self.is_dragging = True
            self.drag_start_x = event.pos().x() - self.handle.pos().x()

    def mouseMoveEvent(self, event):
        if self.is_dragging and not self.is_confirmed:
            new_x = event.pos().x() - self.drag_start_x
            new_x = max(self.padding, min(new_x, self.max_x))
            self.handle.move(new_x, self.padding)
            
            # Hide text/arrows as we slide
            progress = (new_x - self.padding) / (self.max_x - self.padding)
            opacity = int(255 * (1.0 - progress * 1.5)) # Fade out faster
            opacity = max(0, opacity)
            self.lbl_text.setStyleSheet(f"color: rgba(75, 85, 99, {opacity}); font-weight: 700; font-size: {UIScaling.scale_font(15)}px; border: none; background: transparent;")
            self.arrows.anim.stop()
            self.arrows.setStyleSheet(f"color: rgba(217, 119, 6, {opacity}); font-weight: 800; font-size: {UIScaling.scale_font(18)}px; background: transparent; border: none;")

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            if self.handle.pos().x() >= self.max_x - UIScaling.scale(10):
                # Success Logic
                self.is_confirmed = True
                self.handle.move(self.max_x, self.padding)
                self.update_handle_style("#10B981", "#059669")
                self.handle_icon.setText("✓")
                self.confirmed.emit()
            else:
                # Spring back
                self.anim = QPropertyAnimation(self.handle, b"pos")
                self.anim.setDuration(400)
                self.anim.setStartValue(self.handle.pos())
                self.anim.setEndValue(QPoint(self.padding, self.padding))
                self.anim.setEasingCurve(QEasingCurve.OutElastic)
                self.anim.start()
                
                # Reset visuals
                self.lbl_text.setStyleSheet(f"color: rgba(75, 85, 99, 255); font-weight: 700; font-size: {UIScaling.scale_font(15)}px; border: none; background: transparent;")
                self.arrows.anim.start()

class SlideConfirmOverlay(BaseOverlay):
    """Overlay with a slide-to-confirm interaction."""
    confirmed = Signal()

    def __init__(self, parent=None, title="Selesaikan Pekerjaan?", subtitle="Sesi ini akan divalidasi dan dipindahkan ke Laporan."):
        super().__init__(parent)
        self.content_box.setFixedWidth(UIScaling.scale(460))
        self.content_box.setFixedHeight(UIScaling.scale(320))
        self.content_box.setStyleSheet(f"""
            QFrame {{ 
                background-color: #FFFFFF; 
                border-radius: 24px; 
                border: 1px solid #E5E7EB; 
            }}
        """)
        
        # Inner lighting/highlight for the box
        inner_highlight = QFrame(self.content_box)
        inner_highlight.setGeometry(1, 1, self.content_box.width() - 2, self.content_box.height() - 2)
        inner_highlight.setStyleSheet("background: transparent; border-radius: 23px; border-top: 1px solid rgba(255, 255, 255, 0.5);")
        inner_highlight.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Close Button (X)
        self.btn_close = QPushButton("✕", self.content_box)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(UIScaling.scale(44), UIScaling.scale(44))
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                color: #9CA3AF;
                background: transparent;
                font-size: {UIScaling.scale_font(20)}px;
                border: none;
            }}
            QPushButton:hover {{ color: #111827; }}
        """)
        self.btn_close.move(self.content_box.width() - UIScaling.scale(45), UIScaling.scale(5))
        self.btn_close.clicked.connect(self.close_overlay)

        # Clear default content layout margins
        self.content_layout.setContentsMargins(UIScaling.scale(30), UIScaling.scale(40), UIScaling.scale(30), UIScaling.scale(30))
        self.content_layout.setSpacing(UIScaling.scale(15))
        
        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: #111827; font-size: {UIScaling.scale_font(22)}px; font-weight: 800; border: none; background: transparent;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.lbl_title)
        
        # Subtitle
        self.lbl_sub = QLabel("Sesi ini akan divalidasi dan dipindahkan ke Laporan.")
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(f"color: #4B5563; font-size: {UIScaling.scale_font(14)}px; font-weight: 500; border: none; background: transparent;")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.lbl_sub)
        
        self.content_layout.addStretch()
        
        # Slide Switch
        self.slide_switch = SlideSwitch()
        self.slide_switch.confirmed.connect(self.on_confirmed)
        self.content_layout.addWidget(self.slide_switch, alignment=Qt.AlignCenter)
        
        self.content_layout.addStretch()
        
        # Cancel Link
        self.btn_cancel = QPushButton("Batal, tetap kerjakan Preset ini")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #6B7280;
                font-weight: 500;
                font-size: {UIScaling.scale_font(13)}px;
                border: none;
                padding: 5px;
            }}
            QPushButton:hover {{ color: #111827; text-decoration: underline; }}
        """)
        self.btn_cancel.clicked.connect(self.close_overlay)
        self.content_layout.addWidget(self.btn_cancel, alignment=Qt.AlignCenter)

    def on_confirmed(self):
        # Small delay to let the user see the success state
        QTimer.singleShot(500, self.finish_confirmed)

    def finish_confirmed(self):
        self.confirmed.emit()
        self.close_overlay()
