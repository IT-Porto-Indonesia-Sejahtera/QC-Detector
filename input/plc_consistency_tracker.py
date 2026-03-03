import os
import time
import datetime
import xlsxwriter
import cv2
from typing import List, Dict, Any, Optional

class PLCConsistencyTracker:
    """
    Tracks capture events triggered by PLC for consistency analysis.
    Saves images and exports data to Excel.
    """
    
    def __init__(self, base_dir: str = "output/consistency_test"):
        self.base_dir = base_dir
        self.records: List[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.session_dir: Optional[str] = None
        self.is_active = False
        
    def start_session(self):
        """Start a new tracking session"""
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.base_dir, f"session_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "images"), exist_ok=True)
        
        self.records = []
        self.is_active = True
        print(f"[TRACKER] Started session: {self.session_id}")
        
    def stop_session(self) -> str:
        """Stop tracking and export to Excel. Returns path to Excel file."""
        if not self.is_active:
            return ""
            
        self.is_active = False
        excel_path = self.export_to_excel()
        print(f"[TRACKER] Stopped session. Exported to: {excel_path}")
        return excel_path
        
    def add_record(self, 
                   frame,
                   sku: str, 
                   size: str, 
                   px_val: float, 
                   mm_val: float, 
                   plc_input: int, 
                   plc_output: int):
        """Add a new record to the current session"""
        if not self.is_active:
            return
            
        index = len(self.records) + 1
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Save image
        img_filename = f"capture_{index:03d}_{sku}_{size}.jpg"
        img_relative_path = os.path.join("images", img_filename)
        img_absolute_path = os.path.join(self.session_dir, img_relative_path)
        
        cv2.imwrite(img_absolute_path, frame)
        
        record = {
            "index": index,
            "timestamp": timestamp,
            "sku": sku,
            "size": size,
            "pixel": round(px_val, 3),
            "mm": round(mm_val, 3),
            "plc_input": plc_input,
            "plc_output": plc_output,
            "image_path": img_relative_path
        }
        
        self.records.append(record)
        print(f"[TRACKER] Added record #{index}: {sku} {size} -> {mm_val}mm")

    def export_to_excel(self) -> str:
        """Export records to Excel file using xlsxwriter"""
        if not self.session_dir:
            return ""
            
        filename = f"consistency_report_{self.session_id}.xlsx"
        path = os.path.join(self.session_dir, filename)
        
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet("Consistency Data")
        
        # Formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })
        
        # Headers
        headers = ["Index", "Timestamp", "SKU", "Size", "Pixel Value", "MM Value", "PLC Input (D12)", "PLC Output (D100)", "Image Link"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)
            
        # Data
        for row, rec in enumerate(self.records, start=1):
            worksheet.write(row, 0, rec["index"], cell_format)
            worksheet.write(row, 1, rec["timestamp"], cell_format)
            worksheet.write(row, 2, rec["sku"], cell_format)
            worksheet.write(row, 3, rec["size"], cell_format)
            worksheet.write(row, 4, rec["pixel"], cell_format)
            worksheet.write(row, 5, rec["mm"], cell_format)
            worksheet.write(row, 6, rec["plc_input"], cell_format)
            worksheet.write(row, 7, rec["plc_output"], cell_format)
            
            # Link to image
            worksheet.write_url(row, 8, f"external:{rec['image_path']}", cell_format, string="View Image")
            
        workbook.close()
        return path

    def get_count(self) -> int:
        return len(self.records)
