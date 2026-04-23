"""
Sony A7 Mark III Capture Thread (Capture-Only Mode)

Instead of a live video feed, this thread shows a standby indicator and
waits for a PLC/sensor trigger. When triggered, it uses gphoto2 to command
the camera to take a full-resolution still photo (electronic shutter),
downloads the image, and displays it on screen for QC analysis.

This thread is ONLY used when camera_type == "sony". IP and USB cameras
are completely unaffected and continue to use VideoCaptureThread.

No IEW, v4l2loopback, or ffmpeg required — just gphoto2 + USB-C.
"""

import cv2
import os
import subprocess
import time
import numpy as np
from PySide6.QtCore import QThread, Signal


class SonyCaptureThread(QThread):
    """
    Background thread for Sony camera in capture-only mode.
    
    - No live video feed (avoids USB conflict entirely).
    - Shows a standby indicator until a trigger fires.
    - On trigger: captures full-res still via gphoto2 and emits the image.
    """
    
    # Emitted with a "standby" placeholder frame for the preview area
    frame_ready = Signal(object)
    # Emitted when a full-res still image has been captured and downloaded
    still_captured = Signal(object)  # numpy array (full-res image)
    # Connection status
    connection_failed = Signal(str)
    connection_lost = Signal()
    # Status message for the UI
    status_update = Signal(str)

    def __init__(self, usb_index=0, crop_params=None, distortion_params=None,
                 aspect_ratio_correction=1.0, force_width=0, force_height=0):
        super().__init__()
        self.usb_index = usb_index  # Not used for video, kept for compatibility
        self.running = True
        self.cap = None  # No video capture in this mode
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
        
        # Track capture count
        self._capture_count = 0
        
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
        print("[Sony] gphoto2 not found. Install with: brew install gphoto2 (Mac) or sudo apt install gphoto2 (Linux)")
        return False

    def _check_camera_connected(self):
        """Check if a Sony camera is detected via gphoto2."""
        if not self._gphoto2_available:
            return False
        try:
            result = subprocess.run(
                ["gphoto2", "--auto-detect"],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout.lower()
            return "sony" in output or "usb" in output
        except Exception:
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
    # Standby Frame Generator
    # ------------------------------------------------------------------
    def _create_standby_frame(self, message="SONY A7 III — SIAP", sub_message="Menunggu trigger...", color=(40, 40, 40)):
        """Create a dark standby frame with status text."""
        w, h = 1024, 680
        frame = np.full((h, w, 3), color, dtype=np.uint8)
        
        # Main text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(message, font, 1.2, 2)[0]
        tx = (w - text_size[0]) // 2
        ty = (h // 2) - 20
        cv2.putText(frame, message, (tx, ty), font, 1.2, (0, 200, 100), 2, cv2.LINE_AA)
        
        # Sub text
        sub_size = cv2.getTextSize(sub_message, font, 0.7, 1)[0]
        sx = (w - sub_size[0]) // 2
        sy = ty + 50
        cv2.putText(frame, sub_message, (sx, sy), font, 0.7, (150, 150, 150), 1, cv2.LINE_AA)
        
        # Capture count
        count_text = f"Foto: {self._capture_count}"
        cv2.putText(frame, count_text, (w - 200, h - 30), font, 0.6, (100, 100, 100), 1, cv2.LINE_AA)
        
        return frame

    # ------------------------------------------------------------------
    # Main Thread Loop (Standby + Capture on Demand)
    # ------------------------------------------------------------------
    def run(self):
        try:
            if not self._gphoto2_available:
                self.connection_failed.emit(
                    "gphoto2 tidak ditemukan. Install dengan:\n"
                    "Mac: brew install gphoto2\n"
                    "Linux: sudo apt install gphoto2"
                )
                return
            
            # Kill any Linux background processes that lock the camera
            try:
                subprocess.run(["killall", "gvfs-gphoto2-volume-monitor"],
                               capture_output=True, timeout=3)
            except Exception:
                pass
            
            # Check if camera is connected
            if self._check_camera_connected():
                print("[Sony] Camera detected via gphoto2. Standing by for triggers.")
            else:
                print("[Sony] WARNING: Camera not detected. Make sure USB is connected and set to PC Remote.")
            
            # Emit initial standby frame
            standby = self._create_standby_frame()
            self.last_frame = standby
            self.frame_ready.emit(standby)
            
            while self.running:
                # Check if a still capture was requested
                with self._capture_lock:
                    do_capture = self._capture_requested
                    self._capture_requested = False

                if do_capture:
                    # Show "capturing" indicator
                    capturing_frame = self._create_standby_frame(
                        "📸 MENGAMBIL FOTO...", 
                        "Harap tunggu (full resolution)",
                        color=(30, 30, 60)
                    )
                    self.frame_ready.emit(capturing_frame)
                    
                    # Execute the capture
                    # After capture, the captured image stays on screen
                    # (emitted via frame_ready inside _do_still_capture)
                    # It will remain visible until the next trigger fires
                    self._do_still_capture()
                
                # Sleep to avoid busy-waiting (check for triggers every 100ms)
                self.msleep(100)
                
        except Exception as e:
            print(f"[Sony] Error: {e}")
            self.connection_failed.emit(str(e))

    # ------------------------------------------------------------------
    # Still Capture (Full Resolution via gphoto2)
    # ------------------------------------------------------------------
    def request_still_capture(self):
        """
        Request a full-resolution still image capture.
        Called from the main thread when PLC/sensor triggers.
        """
        with self._capture_lock:
            self._capture_requested = True
        print("[Sony] Full-res still capture requested.")

    def _do_still_capture(self):
        """
        Execute a gphoto2 capture-image-and-download command.
        No USB conflict because there is no live video stream to fight with.
        """
        print("[Sony] Capturing full-resolution still image...")
        
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
                    self._capture_count += 1
                    print(f"[Sony] Full-res capture #{self._capture_count}: {w}x{h} ({filepath})")
                    
                    # Apply the processing pipeline
                    processed = self._process_frame(img)
                    
                    # Update the preview with the captured image
                    self.last_frame = processed
                    self.frame_ready.emit(processed)
                    
                    # Also emit still_captured for the QC measurement pipeline
                    self.still_captured.emit(processed)
                else:
                    print(f"[Sony] Failed to read captured image: {filepath}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"[Sony] gphoto2 capture failed: {error_msg}")
                
                # Show error on the standby frame
                err_frame = self._create_standby_frame(
                    "GAGAL MENGAMBIL FOTO",
                    error_msg[:60],
                    color=(60, 20, 20)
                )
                self.frame_ready.emit(err_frame)
                
        except subprocess.TimeoutExpired:
            print("[Sony] gphoto2 capture timed out (15s). Is the camera connected?")
        except Exception as e:
            print(f"[Sony] Capture error: {e}")

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
