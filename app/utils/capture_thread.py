import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from app.utils.camera_utils import open_video_capture

class VideoCaptureThread(QThread):
    """Background thread for camera connection and frame capture"""
    frame_ready = Signal(object)
    connection_failed = Signal(str)
    connection_lost = Signal()

    def __init__(self, source, is_ip=False, crop_params=None, distortion_params=None):
        super().__init__()
        self.source = source
        self.is_ip = is_ip
        self.running = True
        self.cap = None
        self.last_frame = None  # Store for calibration access
        # Crop params: {"left": 0, "right": 0, "top": 0, "bottom": 0} in percent
        self.crop_params = crop_params or {}
        # Distortion params: {k1, k2, p1, p2, k3, fx, fy, cx, cy}
        self.distortion_params = distortion_params or {}
        
        # Pre-calculate camera matrix and dist coeffs if possible
        self.camera_matrix = None
        self.dist_coeffs = None
        self._prepare_distortion_matrices()

    def _prepare_distortion_matrices(self):
        """Parse distortion params into numpy arrays"""
        dp = self.distortion_params
        if not dp: return

        # Coefficients
        k1 = dp.get("k1", 0.0)
        k2 = dp.get("k2", 0.0)
        p1 = dp.get("p1", 0.0)
        p2 = dp.get("p2", 0.0)
        k3 = dp.get("k3", 0.0)
        
        # Only create if there's any non-zero distortion
        if any(v != 0 for v in [k1, k2, p1, p2, k3]):
            self.dist_coeffs = np.array([k1, k2, p1, p2, k3], dtype=np.float64)
            
            # Camera Matrix
            fx = dp.get("fx", 0.0)
            fy = dp.get("fy", 0.0)
            cx = dp.get("cx", 0.0)
            cy = dp.get("cy", 0.0)
            
            # If any matrix param is provided, use it. Else it will be estimated in runtime.
            if any(v != 0 for v in [fx, fy, cx, cy]):
                self.camera_matrix = np.array([
                    [fx, 0, cx],
                    [0, fy, cy],
                    [0,  0,  1]
                ], dtype=np.float64)

    def apply_distortion_correction(self, frame):
        """Apply Lens Distortion Correction (undistort)"""
        if self.dist_coeffs is None:
            return frame
            
        h, w = frame.shape[:2]
        
        # If camera matrix wasn't fully provided, estimate it now
        cam_mat = self.camera_matrix
        if cam_mat is None:
            # Estimate: Ref: OpenCV docs usually suggest fx=fy=w or similar for estimation if unknown
            # But strictly, cx,cy should be center.
            # Let's approximate focal length as width.
            fx = w
            fy = w # Square pixels usually
            cx = w / 2.0
            cy = h / 2.0
            cam_mat = np.array([
                [fx, 0, cx],
                [0, fy, cy],
                [0,  0,  1]
            ], dtype=np.float64)
            
        # Undistort
        try:
            # We can use getOptimalNewCameraMatrix to crop valid area, 
            # but usually users just want straighten lines.
            # alpha=0: crop unwanted pixels. alpha=1: keep all pixels (some black).
            # Let's default to just regular undistort which is equivalent to alpha=0 simplified?
            # actually cv2.undistort simply applies it.
            # For better results we usually do:
            # newcameramtx, roi = cv2.getOptimalNewCameraMatrix(cam_mat, self.dist_coeffs, (w,h), 1, (w,h))
             # dst = cv2.undistort(frame, cam_mat, self.dist_coeffs, None, newcameramtx)
             # x, y, w, h = roi
             # dst = dst[y:y+h, x:x+w]
             # return dst
             
            # Simple undistort
            dst = cv2.undistort(frame, cam_mat, self.dist_coeffs, None, cam_mat)
            return dst
        except Exception as e:
            print(f"[CaptureThread] Distortion Error: {e}")
            return frame

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
                    # 1. Distortion Correction first (on full frame)
                    frame = self.apply_distortion_correction(frame)
                    
                    # 2. Crop/Zoom
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

    def update_params(self, crop_params=None, distortion_params=None):
        """Update crop and distortion parameters dynamically"""
        if crop_params is not None:
            self.crop_params = crop_params
        
        if distortion_params is not None:
            self.distortion_params = distortion_params
            self._prepare_distortion_matrices()
            
    def stop(self):
        self.running = False
        self.quit()
        if not self.wait(500):
            print("[CaptureThread] Warning: Thread did not stop gracefully (timeout).")
