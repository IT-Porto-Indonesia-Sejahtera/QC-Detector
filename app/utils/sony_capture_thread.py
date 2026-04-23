"""
Sony A7 Mark III Capture Thread

Provides two modes of operation for the Sony camera:
1. Live Preview: Uses the standard USB video stream (via IEW/gphoto2 loopback)
   for the continuous live view — same as a normal USB camera.
2. Still Capture (Triggered): When a PLC/sensor trigger fires, uses gphoto2
   to command the camera to take a full-resolution still photo (electronic
   shutter) and downloads it for QC analysis.

This thread is ONLY used when camera_type == "sony". IP and USB cameras
are completely unaffected and continue to use VideoCaptureThread.
"""

import cv2
import os
import subprocess
import tempfile
import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from app.utils.camera_utils import open_video_capture


class SonyCaptureThread(QThread):
    """Background thread that provides live preview AND on-demand full-res capture."""
    
    # Emitted every frame for the live preview (low-res video stream)
    frame_ready = Signal(object)
    # Emitted when a full-res still image has been captured and downloaded
    still_captured = Signal(object)  # numpy array (full-res image)
    # Connection errors
    connection_failed = Signal(str)
    connection_lost = Signal()

    def __init__(self, usb_index=0, crop_params=None, distortion_params=None,
                 aspect_ratio_correction=1.0, force_width=0, force_height=0):
        super().__init__()
        self.usb_index = usb_index
        self.running = True
        self.cap = None
        self.last_frame = None
        self.raw_frame = None
        
        # Crop / distortion (same interface as VideoCaptureThread)
        self.crop_params = crop_params or {}
        self.distortion_params = distortion_params or {}
        self.aspect_ratio_correction = aspect_ratio_correction
        self.rotation = self.crop_params.get("rotation", 0)
        self.force_width = force_width
        self.force_height = force_height
        
        # Still capture state
        self._capture_requested = False
        self._capture_lock = __import__('threading').Lock()
        
        # Distortion matrices (pre-calculated)
        self.camera_matrix = None
        self.dist_coeffs = None
        self._prepare_distortion_matrices()
        
        # Check if gphoto2 is available
        self._gphoto2_available = self._check_gphoto2()

    def _check_gphoto2(self):
        """Check if gphoto2 CLI is installed."""
        try:
            result = subprocess.run(
                ["gphoto2", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("[Sony] gphoto2 is available for full-res capture.")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        print("[Sony] gphoto2 not found. Full-res still capture will NOT be available.")
        print("[Sony] Install with: brew install gphoto2 (Mac) or sudo apt install gphoto2 (Linux)")
        return False

    def _prepare_distortion_matrices(self):
        """Parse distortion params into numpy arrays (same as VideoCaptureThread)."""
        dp = self.distortion_params
        if not dp:
            return

        k1 = dp.get("k1", 0.0)
        k2 = dp.get("k2", 0.0)
        p1 = dp.get("p1", 0.0)
        p2 = dp.get("p2", 0.0)
        k3 = dp.get("k3", 0.0)

        if any(v != 0 for v in [k1, k2, p1, p2, k3]):
            self.dist_coeffs = np.array([k1, k2, p1, p2, k3], dtype=np.float64)

            fx = dp.get("fx", 0.0)
            fy = dp.get("fy", 0.0)
            cx = dp.get("cx", 0.0)
            cy = dp.get("cy", 0.0)

            if any(v != 0 for v in [fx, fy, cx, cy]):
                self.camera_matrix = np.array([
                    [fx, 0, cx],
                    [0, fy, cy],
                    [0,  0,  1]
                ], dtype=np.float64)

    # ------------------------------------------------------------------
    # Image Processing (shared with VideoCaptureThread)
    # ------------------------------------------------------------------
    def apply_distortion_correction(self, frame):
        if self.dist_coeffs is None:
            return frame
        h, w = frame.shape[:2]
        cam_mat = self.camera_matrix
        if cam_mat is None:
            fx = w; fy = w; cx = w / 2.0; cy = h / 2.0
            cam_mat = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)
        try:
            return cv2.undistort(frame, cam_mat, self.dist_coeffs, None, cam_mat)
        except Exception as e:
            print(f"[Sony] Distortion error: {e}")
            return frame

    def apply_aspect_ratio_correction(self, frame):
        if abs(self.aspect_ratio_correction - 1.0) < 0.01:
            return frame
        h, w = frame.shape[:2]
        new_w = int(w * self.aspect_ratio_correction)
        if new_w <= 0:
            return frame
        return cv2.resize(frame, (new_w, h), interpolation=cv2.INTER_LINEAR)

    def apply_crop(self, frame):
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
            return frame
        return frame[y1:y2, x1:x2]

    def apply_rotation(self, frame):
        if self.rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def _process_frame(self, frame):
        """Apply the full processing pipeline to a frame."""
        frame = self.apply_distortion_correction(frame)
        frame = self.apply_aspect_ratio_correction(frame)
        self.raw_frame = frame.copy()
        frame = self.apply_crop(frame)
        frame = self.apply_rotation(frame)
        return frame

    # ------------------------------------------------------------------
    # Main Thread Loop (Live Preview via USB video stream)
    # ------------------------------------------------------------------
    def run(self):
        try:
            self.cap = open_video_capture(
                self.usb_index,
                force_width=self.force_width,
                force_height=self.force_height
            )
            if not self.cap or not self.cap.isOpened():
                self.connection_failed.emit("Failed to open Sony camera video stream")
                return

            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            while self.running:
                # Check if a still capture was requested
                with self._capture_lock:
                    do_capture = self._capture_requested
                    self._capture_requested = False

                if do_capture and self._gphoto2_available:
                    self._do_still_capture()

                # Continue reading live preview frames
                ret, frame = self.cap.read()
                if not self.running:
                    break

                if ret:
                    if self.last_frame is None:
                        h, w = frame.shape[:2]
                        print(f"[Sony] Live Preview Resolution: {w}x{h}")

                    processed = self._process_frame(frame)
                    self.last_frame = processed
                    self.frame_ready.emit(processed)
                else:
                    self.connection_lost.emit()
                    break

                self.msleep(1)
        except Exception as e:
            print(f"[Sony] Error: {e}")
            self.connection_failed.emit(str(e))
        finally:
            if self.cap:
                self.cap.release()

    # ------------------------------------------------------------------
    # Still Capture (Full Resolution via gphoto2)
    # ------------------------------------------------------------------
    def request_still_capture(self):
        """
        Request a full-resolution still image capture.
        Called from the main thread when PLC/sensor triggers.
        The actual capture happens in the background thread to avoid blocking UI.
        """
        with self._capture_lock:
            self._capture_requested = True
        print("[Sony] Full-res still capture requested.")

    def _do_still_capture(self):
        """
        Execute a gphoto2 capture-image-and-download command.
        
        IMPORTANT: gphoto2 and OpenCV both need exclusive access to the USB device.
        We must temporarily release the video capture before gphoto2 can communicate
        with the camera, then re-open it for the live preview afterward.
        """
        print("[Sony] Capturing full-resolution still image...")
        print("[Sony] Releasing USB video stream for gphoto2 access...")
        
        # 1. Release the OpenCV video capture to free the USB device
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Small delay to let the OS fully release the USB device
        time.sleep(0.5)
        
        # 2. Kill any Linux background processes that might lock the camera
        try:
            subprocess.run(["killall", "gvfs-gphoto2-volume-monitor"],
                           capture_output=True, timeout=3)
        except Exception:
            pass
        
        # 3. Execute the gphoto2 capture
        capture_dir = os.path.join("output", "sony_captures")
        os.makedirs(capture_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"sony_capture_{timestamp}.jpg"
        filepath = os.path.join(capture_dir, filename)
        
        try:
            result = subprocess.run(
                [
                    "gphoto2",
                    "--capture-image-and-download",
                    "--filename", filepath,
                    "--force-overwrite"
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and os.path.exists(filepath):
                img = cv2.imread(filepath)
                if img is not None:
                    h, w = img.shape[:2]
                    print(f"[Sony] Full-res capture successful: {w}x{h} ({filepath})")
                    processed = self._process_frame(img)
                    self.still_captured.emit(processed)
                else:
                    print(f"[Sony] Failed to read captured image: {filepath}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"[Sony] gphoto2 capture failed: {error_msg}")
                
        except subprocess.TimeoutExpired:
            print("[Sony] gphoto2 capture timed out (15s). Is the camera connected?")
        except Exception as e:
            print(f"[Sony] Capture error: {e}")
        
        # 4. Re-open the video capture for the live preview
        print("[Sony] Re-opening USB video stream for live preview...")
        time.sleep(0.5)  # Brief delay before re-opening
        try:
            self.cap = open_video_capture(
                self.usb_index,
                force_width=self.force_width,
                force_height=self.force_height
            )
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
                print("[Sony] Live preview re-opened successfully.")
            else:
                print("[Sony] WARNING: Could not re-open live preview after capture.")
        except Exception as e:
            print(f"[Sony] Error re-opening video stream: {e}")

    # ------------------------------------------------------------------
    # Parameter Updates (same interface as VideoCaptureThread)
    # ------------------------------------------------------------------
    def update_params(self, crop_params=None, distortion_params=None, aspect_ratio_correction=None):
        """Update crop and distortion parameters dynamically."""
        if crop_params is not None:
            self.crop_params = crop_params
        if distortion_params is not None:
            self.distortion_params = distortion_params
            self._prepare_distortion_matrices()
        if aspect_ratio_correction is not None:
            self.aspect_ratio_correction = aspect_ratio_correction
        if "rotation" in (crop_params or {}):
            new_rot = crop_params["rotation"]
            if new_rot != self.rotation:
                print(f"[Sony] Rotation changed: {self.rotation} -> {new_rot} deg")
                self.rotation = new_rot

    def stop(self):
        self.running = False
        self.quit()
        if not self.wait(500):
            print("[Sony] Warning: Thread did not stop gracefully (timeout).")
