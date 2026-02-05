import requests
import io
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QPixmap, QImage
import shiboken6

class ImageLoaderSignals(QObject):
    """
    Signals for the ImageLoaderWorker.
    Must be a QObject to support signals.
    """
    image_loaded = Signal(str, QPixmap)  # gdrive_id, pixmap
    image_failed = Signal(str, str)      # gdrive_id, error_message

class ImageLoaderWorker(QRunnable):
    """
    Worker thread to download an image from a URL.
    """
    def __init__(self, gdrive_id: str, cancelled_flag: list):
        super().__init__()
        self.gdrive_id = gdrive_id
        self.signals = ImageLoaderSignals()
        self._cancelled = cancelled_flag  # Shared reference to check cancellation
        
    def _safe_emit_loaded(self, gdrive_id, pixmap):
        """Safely emit signal only if not cancelled and signals object is valid"""
        try:
            if self._cancelled[0]:
                return
            if shiboken6.isValid(self.signals):
                self.signals.image_loaded.emit(gdrive_id, pixmap)
        except RuntimeError:
            pass  # Signal source was deleted, ignore
    
    def _safe_emit_failed(self, gdrive_id, error):
        """Safely emit signal only if not cancelled and signals object is valid"""
        try:
            if self._cancelled[0]:
                return
            if shiboken6.isValid(self.signals):
                self.signals.image_failed.emit(gdrive_id, error)
        except RuntimeError:
            pass  # Signal source was deleted, ignore
        
    @Slot()
    def run(self):
        # Check cancellation before starting
        if self._cancelled[0]:
            return
            
        try:
            # Construct URL
            url = self.gdrive_id
            if not url.startswith("http"):
                url = f"https://drive.google.com/uc?export=view&id={self.gdrive_id}"
            
            # Check cancellation before network request
            if self._cancelled[0]:
                return
                
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Check cancellation after network request
            if self._cancelled[0]:
                return
            
            image_data = response.content
            image = QImage()
            if image.loadFromData(image_data):
                pixmap = QPixmap.fromImage(image)
                self._safe_emit_loaded(self.gdrive_id, pixmap)
            else:
                self._safe_emit_failed(self.gdrive_id, "Failed to decode image data")
                
        except Exception as e:
            self._safe_emit_failed(self.gdrive_id, str(e))

class NetworkImageLoader(QObject):
    """
    Manager for loading network images with caching.
    """
    image_loaded = Signal(str, QPixmap)
    image_failed = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # Limit concurrent downloads
        self.cache = {}  # Memory cache: gdrive_id -> QPixmap
        self.pending = set()  # Set of gdrive_ids currently downloading
        self._cancelled = [False]  # Shared mutable flag for all workers
        self._workers = []  # Keep references to workers for cleanup
        
    def load_image(self, gdrive_id: str):
        """
        Request to load an image.
        If cached, emits image_loaded immediately.
        If downloading, waits.
        If new, starts download.
        """
        # Don't start new downloads if cancelled
        if self._cancelled[0]:
            return
            
        if not gdrive_id:
            self.image_failed.emit("", "Empty ID")
            return
            
        # Check cache
        if gdrive_id in self.cache:
            self.image_loaded.emit(gdrive_id, self.cache[gdrive_id])
            return
            
        # Check if already pending
        if gdrive_id in self.pending:
            return
            
        # Start download
        self.pending.add(gdrive_id)
        worker = ImageLoaderWorker(gdrive_id, self._cancelled)
        worker.signals.image_loaded.connect(self._on_success)
        worker.signals.image_failed.connect(self._on_failure)
        self._workers.append(worker)
        self.thread_pool.start(worker)
        
    def _on_success(self, gdrive_id, pixmap):
        # Don't process if cancelled
        if self._cancelled[0]:
            return
        if gdrive_id in self.pending:
            self.pending.remove(gdrive_id)
        self.cache[gdrive_id] = pixmap
        # Emit safely
        try:
            if shiboken6.isValid(self):
                self.image_loaded.emit(gdrive_id, pixmap)
        except RuntimeError:
            pass
        
    def _on_failure(self, gdrive_id, error):
        # Don't process if cancelled
        if self._cancelled[0]:
            return
        if gdrive_id in self.pending:
            self.pending.remove(gdrive_id)
        try:
            if shiboken6.isValid(self):
                self.image_failed.emit(gdrive_id, error)
        except RuntimeError:
            pass
    
    def cancel_all(self):
        """Cancel all pending downloads. Call before destroying the loader."""
        self._cancelled[0] = True
        self.pending.clear()
        # Clear thread pool - this prevents queued workers from starting
        self.thread_pool.clear()
