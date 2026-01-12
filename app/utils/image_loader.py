import requests
import io
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QPixmap, QImage

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
    def __init__(self, gdrive_id: str):
        super().__init__()
        self.gdrive_id = gdrive_id
        self.signals = ImageLoaderSignals()
        
    @Slot()
    def run(self):
        try:
            # Construct Google Drive export URL
            url = f"https://drive.google.com/uc?export=view&id={self.gdrive_id}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            image = QImage()
            if image.loadFromData(image_data):
                pixmap = QPixmap.fromImage(image)
                self.signals.image_loaded.emit(self.gdrive_id, pixmap)
            else:
                self.signals.image_failed.emit(self.gdrive_id, "Failed to decode image data")
                
        except Exception as e:
            self.signals.image_failed.emit(self.gdrive_id, str(e))

class NetworkImageLoader(QObject):
    """
    Manager for loading network images with caching.
    """
    image_loaded = Signal(str, QPixmap)
    image_failed = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4) # Limit concurrent downloads
        self.cache = {} # Memory cache: gdrive_id -> QPixmap
        self.pending = set() # Set of gdrive_ids currently downloading
        
    def load_image(self, gdrive_id: str):
        """
        Request to load an image.
        If cached, emits image_loaded immediately.
        If downloading, waits.
        If new, starts download.
        """
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
        worker = ImageLoaderWorker(gdrive_id)
        worker.signals.image_loaded.connect(self._on_success)
        worker.signals.image_failed.connect(self._on_failure)
        self.thread_pool.start(worker)
        
    def _on_success(self, gdrive_id, pixmap):
        if gdrive_id in self.pending:
            self.pending.remove(gdrive_id)
        self.cache[gdrive_id] = pixmap
        # Scale if huge? For now keep original.
        self.image_loaded.emit(gdrive_id, pixmap)
        
    def _on_failure(self, gdrive_id, error):
        if gdrive_id in self.pending:
            self.pending.remove(gdrive_id)
        self.image_failed.emit(gdrive_id, error)
