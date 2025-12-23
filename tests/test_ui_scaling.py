import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
from app.utils.ui_scaling import UIScaling
import sys

# Since we need a QApplication for primaryScreen, we create one if not exists
app = QApplication.instance() or QApplication(sys.argv)

class TestUIScaling(unittest.TestCase):
    def setUp(self):
        # Reset cache for each test
        UIScaling._cached_scale = None

    def test_get_scale_factor_default(self):
        # Default behavior (mocking screen is hard, so we just check it returns a float)
        factor = UIScaling.get_scale_factor()
        self.assertIsInstance(factor, float)
        self.assertGreater(factor, 0.4) # Should be at least the min floor 0.5 or close if not mocked

    def test_scale_calculations(self):
        # Force a specific scale for testing logic
        UIScaling._cached_scale = 1.0
        self.assertEqual(UIScaling.scale(100), 100)
        self.assertEqual(UIScaling.scale_font(18), 18)
        
        UIScaling._cached_scale = 2.0
        self.assertEqual(UIScaling.scale(100), 200)
        self.assertEqual(UIScaling.scale_font(18), 36)
        
        UIScaling._cached_scale = 0.5
        self.assertEqual(UIScaling.scale(100), 50)
        self.assertEqual(UIScaling.scale_font(18), 9)

    def test_screen_size_fallback(self):
        size = UIScaling.get_screen_size()
        self.assertIsInstance(size, QSize)
        self.assertGreater(size.width(), 0)
        self.assertGreater(size.height(), 0)

if __name__ == "__main__":
    unittest.main()
