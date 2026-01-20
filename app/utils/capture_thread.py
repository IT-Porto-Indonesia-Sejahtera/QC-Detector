import cv2
from PySide6.QtCore import QThread, Signal
from app.utils.camera_utils import open_video_capture

class VideoCaptureThread(QThread):
    """Background thread for camera connection and frame capture"""
    frame_ready = Signal(object)
    connection_failed = Signal(str)
    connection_lost = Signal()

    def __init__(self, source, is_ip=False, crop_params=None):
        super().__init__()
        self.source = source
        self.is_ip = is_ip
        self.running = True
        self.cap = None
        self.last_frame = None  # Store for calibration access
        # Crop params: {"left": 0, "right": 0, "top": 0, "bottom": 0} in percent
        self.crop_params = crop_params or {}

    def apply_crop(self, frame):
        """Apply percentage-based cropping to the frame"""
        if not self.crop_params:
            return frame
        h, w = frame.shape[:2]
        left_pct = max(0, min(self.crop_params.get("left", 0), 49))
        right_pct = max(0, min(self.crop_params.get("right", 0), 49))
        top_pct = max(0, min(self.crop_params.get("top", 0), 49))
        bottom_pct = max(0, min(self.crop_params.get("bottom", 0), 49))
        
        x1 = int(w * left_pct / 100)
        x2 = w - int(w * right_pct / 100)
        y1 = int(h * top_pct / 100)
        y2 = h - int(h * bottom_pct / 100)
        
        if x1 >= x2 or y1 >= y2:
            return frame  # Invalid crop, return original
        return frame[y1:y2, x1:x2]

    def run(self):
        try:
            self.cap = open_video_capture(self.source)
            if not self.cap or not self.cap.isOpened():
                self.connection_failed.emit("Failed to open camera")
                return

            while self.running:
                ret = False
                frame = None
                
                if self.is_ip:
                    if self.cap.grab():
                        ret, frame = self.cap.retrieve()
                else:
                    ret, frame = self.cap.read()

                if not self.running: break

                if ret:
                    frame = self.apply_crop(frame)
                    self.last_frame = frame  # Store for calibration
                    self.frame_ready.emit(frame)
                else:
                    self.connection_lost.emit()
                    break
                
                # Small sleep to prevent maxing CPU
                self.msleep(10 if not self.is_ip else 1)
        except Exception as e:
            print(f"[CaptureThread] Error: {e}")
            self.connection_failed.emit(str(e))
        finally:
            if self.cap:
                self.cap.release()

    def stop(self):
        self.running = False
        self.quit()
        if not self.wait(500):
            print("[CaptureThread] Warning: Thread did not stop gracefully (timeout).")
