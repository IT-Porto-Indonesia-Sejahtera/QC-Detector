from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QEvent, QRect, QSize, Signal
from app.utils.ui_scaling import UIScaling

class BaseOverlay(QFrame):
    """
    A base widget that acts as an overly covering the entire parent.
    It contains a centered 'content_box' where the actual dialog content goes.
    """
    closed = Signal()  # Emitted when overlay closes
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(10, 12, 18, 220);")  # Deep industrial dimmer
        
        # Main Layout to center the content
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Dark industrial content box
        self.content_box = QFrame()
        self.content_box.setStyleSheet("""
            QFrame {
                background-color: #1B1F27; 
                border-radius: 15px;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(Qt.black)
        self.content_box.setGraphicsEffect(shadow)
        
        # Content Layout
        self.content_layout = QVBoxLayout(self.content_box)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.main_layout.addWidget(self.content_box)
        
        if parent:
            self.update_content_size()
            self.show()
            self.raise_()
        
        # Install event filter to resize with parent
        if parent:
            parent.installEventFilter(self)

    def update_content_size(self):
        """Update responsiveness based on parent size."""
        parent = self.parent()
        if not parent:
            return
            
        p_size = parent.size()
        self.resize(p_size)
        
        # Adjust content box max size to not exceed parent
        # We can also set a preferred width/height based on scaling
        scaled_w = UIScaling.scale(500)
        scaled_h = UIScaling.scale(600)
        
        # Ensure it doesn't take more than 90% of parent
        max_w = int(p_size.width() * 0.9)
        max_h = int(p_size.height() * 0.9)
        
        final_w = min(scaled_w, max_w)
        final_h = min(scaled_h, max_h)
        
        # Note: If subclasses set context_box size, this might be overridden.
        # So we should provide a method for them to call.
        self.content_box.setMinimumSize(QSize(min(300, max_w), min(300, max_h)))
        self.content_box.setMaximumSize(QSize(final_w, final_h))

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.update_content_size()
        return super().eventFilter(obj, event)

    def show_overlay(self):
        """Show the overlay"""
        self.show()
        self.raise_()

    def close_overlay(self):
        self.closed.emit()  # Emit signal before closing
        self.setParent(None)
        self.deleteLater()
