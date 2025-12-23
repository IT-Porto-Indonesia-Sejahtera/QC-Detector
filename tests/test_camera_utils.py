import os
import unittest
from unittest.mock import patch, MagicMock
from app.utils.camera_utils import open_video_capture

class TestCameraUtils(unittest.TestCase):
    
    @patch('cv2.VideoCapture')
    def test_open_preset_camera(self, mock_vc):
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_vc.return_value = mock_instance
        
        preset = {
            "id": "test-id",
            "name": "Test Camera",
            "protocol": "http",
            "address": "192.168.1.100",
            "port": "8080",
            "path": "/video",
            "username": "user",
            "password": "pass"
        }
        
        # Test opening with preset
        cap = open_video_capture(preset)
        
        # Verify
        self.assertEqual(cap, mock_instance)
        # Verify constructed URL
        expected_url = "http://user:pass@192.168.1.100:8080/video"
        mock_vc.assert_called_with(expected_url)
        # Should NOT have RTSP env var for HTTP
        self.assertNotIn("OPENCV_FFMPEG_CAPTURE_OPTIONS", os.environ)

    @patch('cv2.VideoCapture')
    def test_open_rtsp_with_transport(self, mock_vc):
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_vc.return_value = mock_instance
        
        preset = {
            "protocol": "rtsp",
            "address": "192.168.1.64",
            "transport": "udp"
        }
        
        # Test opening
        open_video_capture(preset)
        
        # Verify env var
        self.assertEqual(os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS"), "rtsp_transport;udp")
        
        # Cleanup
        if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ:
            del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]

if __name__ == '__main__':
    unittest.main()
