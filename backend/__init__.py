"""
QC Backend Module
==================
Backend API module for QC-Detector application.

Usage:
    import backend as qc_backend
    
    # Synchronous call
    products = qc_backend.get_product_sku()
    
    # Async call with callback (non-blocking)
    qc_backend.get_product_sku_async(callback=lambda data: print(data))
    
    # Using Qt signals (for PySide6)
    worker = qc_backend.get_product_sku_worker()
    worker.finished.connect(my_handler)
    worker.start()
"""

from backend.DB import (
    init_db,
    close_pool,
    fetch_all,
    fetch_one,
    is_connected,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
)

from backend.get_product_sku import (
    get_product_sku,
    get_product_sku_async,
    get_product_sku_worker,
    ProductSKUWorker,
)

__all__ = [
    # Database functions
    'init_db',
    'close_pool',
    'fetch_all',
    'fetch_one',
    'is_connected',
    # Database exceptions
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseQueryError',
    # Product SKU functions
    'get_product_sku',
    'get_product_sku_async',
    'get_product_sku_worker',
    'ProductSKUWorker',
]
