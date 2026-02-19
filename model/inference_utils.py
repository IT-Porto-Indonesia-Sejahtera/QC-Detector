from __future__ import annotations
"""
Inference Utilities
===================
Utilities for managing AI models, including pre-loading and warmup.
"""

from PySide6.QtCore import QThread, Signal
from project_utilities.logger_config import get_detection_logger
import time

class ModelWarmupWorker(QThread):
    """
    Worker thread to pre-load AI models (YOLO and FastSAM) in the background.
    This eliminates the lag when the user first tries to measure something.
    """
    finished = Signal()
    progress = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_detection_logger()

    def run(self):
        self.logger.info("Starting AI Model Warmup background task...")
        
        # 1. Warmup YOLO if available
        try:
            from .yolo_inference import get_model, is_available as is_yolo_available
            if is_yolo_available():
                self.progress.emit("Loading YOLOv8-seg...")
                start = time.time()
                get_model()
                self.logger.info(f"YOLOv8-seg warmed up in {time.time() - start:.2f}s")
            else:
                self.logger.warning("YOLOv8-seg not available for warmup")
        except Exception as e:
            import traceback
            self.logger.error(f"Failed to warmup YOLO: {e}")
            self.logger.error(traceback.format_exc())


        # 2. Warmup FastSAM if available
        try:
            from .fastsam_inference import get_model as get_sam_model, is_available as is_sam_available
            if is_sam_available():
                self.progress.emit("Loading FastSAM...")
                start = time.time()
                get_sam_model()
                self.logger.info(f"FastSAM warmed up in {time.time() - start:.2f}s")
            else:
                self.logger.warning("FastSAM not available for warmup")
        except Exception as e:
            self.logger.error(f"Failed to warmup FastSAM: {e}")

        # 3. Warmup Advanced Model (YOLOv8-X + SAM)
        try:
            from .advanced_inference import get_yolo_model as get_adv_yolo, get_sam_model as get_adv_sam, is_available as is_adv_available
            if is_adv_available():
                self.progress.emit("Loading Advanced Model (YOLOv8-X + SAM)...")
                start = time.time()
                # Load both components
                get_adv_yolo() 
                get_adv_sam()
                self.logger.info(f"Advanced Model warmed up in {time.time() - start:.2f}s")
            else:
                self.logger.warning("Advanced Model dependencies not available")
        except Exception as e:
            self.logger.error(f"Failed to warmup Advanced Model: {e}")

        self.logger.info("AI Model Warmup complete.")
        self.finished.emit()
