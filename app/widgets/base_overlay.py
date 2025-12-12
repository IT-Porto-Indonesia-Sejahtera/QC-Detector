
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QEvent, QRect

class BaseOverlay(QFrame):
    """
    A base widget that acts as an overly covering the entire parent.
    It contains a centered 'content_box' where the actual dialog content goes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(100, 100, 100, 240);") # Darker dimmer for better visibility
        
        # Main Layout to center the content
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # The white box
        self.content_box = QFrame()
        self.content_box.setStyleSheet("""
            QFrame {
                background-color: white; 
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
            self.resize(parent.size())
            self.show()
            self.raise_()
        
        # Install event filter to resize with parent
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.resize(obj.size())
        return super().eventFilter(obj, event)

    def close_overlay(self):
        self.setParent(None)
        self.deleteLater()
