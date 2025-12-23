import cv2
from PySide6.QtCore import QThread, Signal
from app.utils.camera_utils import open_video_capture

class VideoCaptureThread(QThread):
    """Background thread for camera connection and frame capture"""
    frame_ready = Signal(object)
    connection_failed = Signal(str)
    connection_lost = Signal()

    def __init__(self, source, is_ip=False):
        super().__init__()
        self.source = source
        self.is_ip = is_ip
        self.running = True
        self.cap = None

    def run(self):
        try:
            self.cap = open_video_capture(self.source)
            if not self.cap or not self.cap.isOpened():
                self.connection_failed.emit("Failed to open camera")
                return

            while self.running:
                if self.is_ip:
                    # Catch up for RTSP to minimize latency
                    while self.running:
                        if not self.cap.grab(): break
                        ret, frame = self.cap.retrieve()
                        if ret: break
                else:
                    ret, frame = self.cap.read()

                if not self.running: break

                if ret:
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
        self.wait()
