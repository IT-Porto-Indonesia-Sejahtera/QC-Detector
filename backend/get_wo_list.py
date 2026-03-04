"""
Work Order Fetching Module
==========================
Functions to fetch and process Work Order data from the database.
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.DB import fetch_all, is_connected
from backend.sku_cache import get_sku_by_code


def fetch_wo_list(plant: str, machine: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch Work Order list for a specific plant and machine.
    
    Args:
        plant: Plant name (e.g., 'EVA1')
        machine: Machine name (e.g., 'Mesin 08')
        target_date: Optional date string in YYYY-MM-DD format. Defaults to CURRENT_DATE.
        
    Returns:
        List of WO dictionaries.
    """
    if not is_connected():
        return []

    date_filter = f"and tanggal_produksi::DATE = '{target_date}'" if target_date else "and tanggal_produksi::DATE = CURRENT_DATE"

    query = f'''
    WITH WO as (
        SELECT 
            mi.date as tanggal_produksi,
            mi.id as id_wo,
            mi.name as nomor_wo,
            mi.state as status_wo,
            pm.name as plant,
            ms.id as id_mps,
            ms.name as nomor_mps,
            ap.code as period_mps,
            mi.shift,
            mm.name as machine,
            pt.id as product_id,
            pt.default_code as product_code,
            pav.name as color,
            mil.target_qty1 as target_qty,
            pu.name as uom
        FROM
            mrp_instructions mi
            left join plant_master pm on mi.plant_id = pm.id
            left join mrp_schedule ms on mi.mps_id = ms.id
            left join account_period ap on mi.period_id = ap.id
            left join mrp_instructions_line mil on mi.id = mil.spk_id
            left join machine_master mm on mil.machine_id = mm.id
            left join product_template pt on mil.product_tmpl_id = pt.id
            left join product_attribute_value pav on mil.warna1_id = pav.id
            left join product_uom pu on pt.uom_id = pu.id
        WHERE
             pm.name not in ('EVA3', 'PORTELAS3')
        
        UNION ALL
        
        SELECT 
            mi.date as tanggal_produksi,
            mi.id as id_wo,
            mi.name as nomor_wo,
            mi.state as status_wo,
            pm.name as plant,
            ms.id as id_mps,
            ms.name as nomor_mps,
            ap.code as period_mps,
            mi.shift,
            mm.name as machine,
            pt.id as product_id,
            pt.default_code as product_code,
            pav.name as color,
            mil.target_qty2 as target_qty,
            pu.name as uom
        FROM
            mrp_instructions mi
            left join plant_master pm on mi.plant_id = pm.id
            left join mrp_schedule ms on mi.mps_id = ms.id
            left join account_period ap on mi.period_id = ap.id
            left join mrp_instructions_line mil on mi.id = mil.spk_id
            left join machine_master mm on mil.machine_id = mm.id
            left join product_template pt on mil.product_tmpl_id = pt.id
            join product_attribute_value pav on mil.warna2_id = pav.id
            left join product_uom pu on pt.uom_id = pu.id
        WHERE
             pm.name not in ('EVA3', 'PORTELAS3')
        
        UNION ALL
        
        SELECT
            mi.date as tanggal_produksi,
            mi.id as id_wo,
            mi.name as nomor_wo,
            mi.state as status_wo,
            pm.name as plant,
            ms.id as id_mps,
            ms.name as nomor_mps,
            ap.code as period_mps,
            
            CAST(mi.shift_planning AS TEXT) AS shift,
            mi.on_machine as machine,
            pt.id as product_id,
            pt.default_code as product_code,
            pav.name as color,
            mi.target_qty,
            pu.name as uom
        FROM
            mrp_instructions mi
            left join plant_master pm on mi.plant_id = pm.id
            left join production_order po on mi.production_order_id = po.id
            left join mrp_schedule ms on po.mps_id = ms.id
            left join account_period ap on ms.period_id = ap.id
            left join product_template pt on mi.product_tmpl_id = pt.id
            left join product_attribute_value pav on mi.color_id = pav.id
            left join product_uom pu on mi.product_uom_id = pu.id
        WHERE
             pm.name = 'EVA3'
            
    )
    SELECT 
        tanggal_produksi,
        nomor_wo,
        status_wo,
        plant,
        shift,
        machine,
        STRING_AGG(CAST(product_id AS TEXT), ', ') AS list_product_id,
        STRING_AGG(CAST(product_code AS TEXT), ', ') AS list_product_code
    FROM WO
    WHERE plant = '{plant}' 
    and machine = '{machine}'
    {date_filter}
    GROUP BY 
        tanggal_produksi,
        nomor_wo,
        status_wo,
        plant,
        shift,
        machine
    ORDER BY 
        tanggal_produksi DESC, 
        nomor_wo;
    '''
    
    return fetch_all(query, as_dict=True)


def get_machine_list() -> List[str]:
    """Fetch all distinct machine names from the master."""
    if not is_connected():
        return ["Mesin 08"]  # Fallback
    
    query = "SELECT DISTINCT name FROM machine_master WHERE name IS NOT NULL ORDER BY name"
    results = fetch_all(query)
    return [row[0] for row in results] or ["Mesin 01", "Mesin 02", "Mesin 03", "Mesin 04", "Mesin 05", "Mesin 06", "Mesin 07", "Mesin 08", "Mesin 09", "Mesin 10"]


def enrich_wo_with_sku(wo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a WO object with SKU magnification (otorisasi) data.
    
    Args:
        wo_data: A single WO dictionary from fetch_wo_list.
        
    Returns:
        The dictionary with an added 'skus' list containing enriched product data.
    """
    codes_str = wo_data.get('list_product_code', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    
    enriched_skus = []
    for code in codes:
        sku_info = get_sku_by_code(code)
        if sku_info:
            enriched_skus.append(sku_info)
        else:
            # Fallback if not in cache
            enriched_skus.append({
                'code': code,
                'Nama Produk': code,
                'otorisasi': 0,
                'sizes': '36,37,38,39,40,41,42,43,44'
            })
            
    wo_data['skus'] = enriched_skus
    return wo_data