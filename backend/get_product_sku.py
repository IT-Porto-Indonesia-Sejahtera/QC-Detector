"""
Product SKU API
===============
Functions to fetch product SKU data from the database.
"""
import json
import threading
from typing import Optional, List, Dict, Any, Callable
from PySide6.QtCore import QThread, Signal, QObject

from backend.DB import fetch_all, is_connected


def get_product_sku(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch product SKU data from the database (synchronous).
    
    Args:
        limit: Optional limit on number of results
    
    Returns:
        List of product dictionaries with keys: 'Nama Produk', 'Perbesaran Ukuran (Otorisasi)', 
        'List Size Available', 'Kategori', 'GDrive ID'.
        Returns empty list if database is not connected or query fails.
    
    Example:
        products = get_product_sku()
        # [{'Nama Produk': 'Sandal X', 'GDrive ID': '1abc...', ...}, ...]
    """
    if not is_connected():
        return []
    
    # Build query with optional LIMIT
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    
    query = f'''
    SELECT * FROM (
        SELECT DISTINCT ON (pt.id)
            pt.name AS "Nama Produk",
            ptd.normal_size AS "Perbesaran Ukuran (Otorisasi)",
--             (
--                 SELECT string_agg(pav.name, ', ' ORDER BY pav.name)
--                 FROM product_attribute_line pal
--                 JOIN product_attribute_line_product_attribute_value_rel rel ON pal.id = rel.product_attribute_line_id
--                 JOIN product_attribute_value pav ON rel.product_attribute_value_id = pav.id
--                 JOIN product_attribute pa ON pal.attribute_id = pa.id
--                 WHERE pal.product_tmpl_id = pt.id
--                   AND (pa.name ILIKE 'Size' OR pa.name ILIKE 'Ukuran' OR pa.name ILIKE 'Nomor')
--             ) 
            pt.size AS "List Size Available",
            pc.name AS "Kategori",
            ia.gdrive_id AS "GDrive ID"

        FROM 
            product_template pt
        LEFT JOIN 
            product_template_dev ptd ON ptd.product_tmpl_id = pt.id
        JOIN 
            ir_attachment ia ON ia.res_model = 'product.template' AND ia.res_id = pt.id
        LEFT JOIN 
            product_category pc ON pt.categ_id = pc.id
        LEFT JOIN 
            res_users ru_attach ON ia.create_uid = ru_attach.id
        LEFT JOIN 
            res_partner rp_attach_create ON ru_attach.partner_id = rp_attach_create.id
        LEFT JOIN 
            res_users ru_prod ON pt.create_uid = ru_prod.id
        LEFT JOIN 
            res_partner rp_prod_create ON ru_prod.partner_id = rp_prod_create.id

        WHERE 
            pt.active = true 
            AND ia.gdrive_id IS NOT NULL 
            AND ia.gdrive_id != ''
            AND pc.name IN ('Sandal EVA')
        ORDER BY 
            pt.id, ptd.id DESC, ia.id ASC
    ) AS data_produk
    WHERE 
        "List Size Available" IS NOT NULL
    AND "Perbesaran Ukuran (Otorisasi)" IS NOT NULL
    {limit_clause}
    '''
    
    result = fetch_all(query, as_dict=True)
    return result


def get_product_sku_json(
    limit: Optional[int] = None
) -> str:
    """
    Fetch product SKU data and return as JSON string.
    
    Args:
        limit: Optional limit on number of results
    
    Returns:
        JSON string of product data
    """
    data = get_product_sku(limit=limit)
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_product_sku_async(
    callback: Callable[[List[Dict[str, Any]]], None],
    error_callback: Optional[Callable[[Exception], None]] = None,
    limit: Optional[int] = None
) -> threading.Thread:
    """
    Fetch product SKU data asynchronously using a background thread.
    Non-blocking - returns immediately while query runs in background.
    
    Args:
        callback: Function to call with results when complete
        error_callback: Optional function to call if an error occurs
        limit: Optional limit on number of results
    
    Returns:
        The thread object (already started)
    
    Example:
        def on_products_loaded(products):
            print(f"Loaded {len(products)} products")
            for p in products:
                print(p['default_code'])
        
        def on_error(e):
            print(f"Error: {e}")
        
        get_product_sku_async(
            callback=on_products_loaded,
            error_callback=on_error
        )
    """
    def run():
        try:
            result = get_product_sku(limit=limit)
            callback(result)
        except Exception as e:
            if error_callback:
                error_callback(e)
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


class ProductSKUWorker(QThread):
    """
    Qt Worker thread for fetching product SKU data.
    Use this for PySide6/Qt applications to avoid blocking the UI.
    
    Signals:
        finished(list): Emitted with product data when complete
        error(str): Emitted with error message if query fails
    
    Example:
        worker = ProductSKUWorker()
        worker.finished.connect(self.on_products_loaded)
        worker.error.connect(self.on_error)
        worker.start()
        
        def on_products_loaded(self, products):
            for product in products:
                print(product['default_code'])
    """
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(
        self,
        limit: Optional[int] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.limit = limit
    
    def run(self):
        try:
            result = get_product_sku(limit=self.limit)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


def get_product_sku_worker(
    limit: Optional[int] = None,
    parent: Optional[QObject] = None
) -> ProductSKUWorker:
    """
    Create a Qt worker thread for fetching product SKU data.
    Convenience function that returns an unstarted worker.
    
    Args:
        limit: Optional limit on number of results
        parent: Optional Qt parent object
    
    Returns:
        ProductSKUWorker instance (not started - call .start())
    
    Example:
        worker = get_product_sku_worker(limit=100)
        worker.finished.connect(lambda data: print(f"Got {len(data)} products"))
        worker.error.connect(lambda err: print(f"Error: {err}"))
        worker.start()
    """
    return ProductSKUWorker(limit=limit, parent=parent)