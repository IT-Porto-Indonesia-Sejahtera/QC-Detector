from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize

class UIScaling:
    """Utility for scaling UI elements based on screen resolution."""
    
    # Reference resolution used for design pixels
    REFERENCE_WIDTH = 1920
    REFERENCE_HEIGHT = 1080
    
    _cached_scale = None

    @classmethod
    def get_scale_factor(cls) -> float:
        """Calculate the scale factor based on the current primary screen resolution."""
        if cls._cached_scale is not None:
            return cls._cached_scale
            
        app = QApplication.instance()
        if not app:
            return 1.0
            
        screen = app.primaryScreen()
        if not screen:
            return 1.0
            
        size = screen.size()
        # We calculate factors for both dimensions
        factor_w = size.width() / cls.REFERENCE_WIDTH
        factor_h = size.height() / cls.REFERENCE_HEIGHT
        
        # Use the smaller factor to ensure everything fits
        # We also put a floor on the scale to prevent things from becoming too tiny
        cls._cached_scale = max(0.5, min(factor_w, factor_h))
        return cls._cached_scale

    @classmethod
    def scale(cls, px: int) -> int:
        """Scale a pixel value."""
        return int(px * cls.get_scale_factor())

    @classmethod
    def scale_font(cls, size: int) -> int:
        """Scale a font size."""
        # Fonts often need a slightly higher scale than layout to remain readable
        # but for now we'll stick to linear scaling
        return int(size * cls.get_scale_factor())

    @classmethod
    def get_screen_size(cls) -> QSize:
        """Get the current primary screen size."""
        app = QApplication.instance()
        if not app:
            return QSize(cls.REFERENCE_WIDTH, cls.REFERENCE_HEIGHT)
        screen = app.primaryScreen()
        if not screen:
            return QSize(cls.REFERENCE_WIDTH, cls.REFERENCE_HEIGHT)
        return screen.size()
