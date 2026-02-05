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
    WITH base_data AS (
    SELECT
        ptd.product_code,
        ptd.revisi,
        pm.name AS divisi,
        ptd.size,
        ptd.code_cetakan,
        ptd.normal_size AS perbesar_ukuran,
--         ptd.hardness,
        ptd.state,
        MAX(
            CASE
                WHEN ir.is_cover = true
                THEN concat('https://lh3.googleusercontent.com/d/', ir.gdrive_id, '=s600')
            END
        ) AS cover_image
    FROM product_template_dev ptd
        LEFT JOIN product_template pt ON pt.id = ptd.product_tmpl_id
        LEFT JOIN product_product pp ON pp.product_tmpl_id = pt.id
        LEFT JOIN product_dev_plant_rel pdp ON pdp.product_dev_id = ptd.id
        LEFT JOIN plant_master pm ON pm.id = pdp.plant_id
        LEFT JOIN crm_team ct ON ct.id = ptd.team_id
        LEFT JOIN product_attribute_value_product_product_rel rel_warna
            ON rel_warna.product_product_id = pp.id
        LEFT JOIN product_attribute_value pav
            ON pav.id = rel_warna.product_attribute_value_id
        LEFT JOIN product_template_dev_line ptdl ON ptdl.product_dev_id = ptd.id
        LEFT JOIN ir_attachment ir
            ON ptd.id = ir.res_id
           AND ir.res_model::text = 'product.template.dev'
    WHERE
        pav.attribute_id = 2
        AND ptd.state <> 'cancel'
        AND ptd.active = true
        AND ptd.size IS NOT NULL
        AND pm.name = 'EVA1'
        AND lower(COALESCE(ptd.product_code, '')) NOT LIKE '%label%'
        AND lower(COALESCE(ptd.product_code, '')) NOT LIKE '%aksesoris%'
    GROUP BY
        ptd.id, ptd.name, ptd.otorisasi_type, ptd.is_portolady,
        pt.id, ptd.product_code, ptd.document_code, ptd.revisi,
        pm.name, ptd.size, ptd.release_date, ptd.otorisasi_date,
        ptd.is_registered_haki, ptd.haki_submit_date, ptd.code_cetakan,
        ptd.normal_size, ptd.is_release_exdig, ct.name, ptd.is_no_brand,
        ptd.notes_tali, ptd.notes_accessories, ptd.hardness,
        ptd.notes_packing, ptd.is_alternative_acc, ptd.state
)
, ranked_data AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_code
            ORDER BY revisi DESC
        ) AS rn
    FROM base_data
)
SELECT *
FROM ranked_data
WHERE rn = 1
    {limit_clause}
    '''
    
    result = fetch_all(query, as_dict=True)
    
    # Process and clean data
    cleaned_result = []
    if result:
        for row in result:
            # Parse Otorisasi (Perbesaran Ukuran)
            # Format examples: "+1.0", "+0.5", "pas", "Pas", "0"
            raw_oto = str(row.get('perbesaran_ukuran', '')).lower().strip()
            oto_val = 0.0
            if raw_oto and raw_oto not in ['pas', 'none', 'null']:
                try:
                    oto_val = float(raw_oto.replace('+', ''))
                except ValueError:
                    pass
            
            # Map to clean dictionary
            cleaned_result.append({
                'Nama Produk': row.get('product_code', 'Unknown'),
                'Perbesaran Ukuran (Otorisasi)': oto_val,  # Now a float
                'Raw Otorisasi': row.get('perbesaran_ukuran'), # Keep original just in case
                'List Size Available': row.get('size', ''),
                'Kategori': row.get('divisi', 'Unknown'),
                'Cover Image': row.get('cover_image'), # Direct URL
                'GDrive ID': row.get('cover_image') # Legacy support (aliased to URL)
            })
            
    return cleaned_result



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