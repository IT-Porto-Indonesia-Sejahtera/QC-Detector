import sys
import os
import numpy as np
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.aruco_utils import detect_aruco_markers, A3_MARKER_LAYOUT
import cv2

class TestArucoHighPrecision(unittest.TestCase):
    def test_layout_logic(self):
        # A3 layout check
        # ID 0 and ID 2 should be (375 - 45) = 330mm apart
        p0 = np.array(A3_MARKER_LAYOUT[0])
        p2 = np.array(A3_MARKER_LAYOUT[2])
        dist = np.linalg.norm(p0 - p2)
        self.assertEqual(dist, 330.0)
        
        # ID 0 and ID 5 should be (252 - 45) = 207mm apart
        p5 = np.array(A3_MARKER_LAYOUT[5])
        dist_v = np.linalg.norm(p0 - p5)
        self.assertEqual(dist_v, 207.0)

    def test_mmpx_calculation(self):
        # Create a dummy frame
        frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
        
        # We can't easily test the whole detect_aruco_markers without real CV2 detection
        # But we can verify the get_physical_distance helper indirectly
        from backend.aruco_utils import get_physical_distance
        
        dist = get_physical_distance(0, 2)
        self.assertEqual(dist, 330.0)
        
        dist = get_physical_distance(0, 1)
        self.assertEqual(dist, 165.0)

if __name__ == '__main__':
    unittest.main()
