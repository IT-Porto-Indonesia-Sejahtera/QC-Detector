import cv2
import csv
import math
import datetime
import os
import xlsxwriter
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
        self.csv_path: Optional[str] = None
        self.is_active = False
        
    def start_session(self):
        """Start a new tracking session"""
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.base_dir, f"session_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "images"), exist_ok=True)
        
        self.csv_path = os.path.join(self.session_dir, "consistency_log.csv")
        self.records = []
        self.is_active = True
        print(f"[TRACKER] Session started: {self.session_id} (Active: {self.is_active})")
        
        # Initialize CSV with headers
        try:
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Index", "Timestamp", "SKU", "Size", "Result", 
                    "Length (px)", "Width (px)", "Length (mm)", "Width (mm)", 
                    "Target (mm)", "Deviation (mm)",
                    "Pre-Cap Delay (ms)", "Post-Res Delay (ms)",
                    "PLC Input (D12)", "PLC Output (D100)"
                ])
        except Exception as e:
            print(f"[TRACKER] Error initializing CSV: {e}")
            
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
                   result_category: str,
                   px_len: float, 
                   px_wid: float,
                   mm_len: float, 
                   mm_wid: float,
                   target_mm: float,
                   deviation_mm: float,
                   plc_input: int, 
                   plc_output: int,
                   pre_delay: int = 0,
                   post_delay: int = 0):
        """Add a new record to the current session"""
        print(f"[TRACKER] Attempting to add record... (Active: {self.is_active}, CSV: {self.csv_path})")
        if not self.is_active:
            return
            
        try:
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
                "result": result_category,
                "px_len": round(px_len, 3),
                "px_wid": round(px_wid, 3),
                "mm_len": round(mm_len, 3),
                "mm_wid": round(mm_wid, 3),
                "target_mm": round(target_mm, 3),
                "deviation_mm": round(deviation_mm, 3),
                "plc_input": plc_input,
                "plc_output": plc_output,
                "pre_delay": pre_delay,
                "post_delay": post_delay,
                "image_path": img_relative_path
            }
            
            self.records.append(record)
            
            # Real-time CSV Logging
            if self.csv_path:
                with open(self.csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        record["index"], record["timestamp"], record["sku"], record["size"], record["result"],
                        record["px_len"], record["px_wid"], record["mm_len"], record["mm_wid"],
                        record["target_mm"], record["deviation_mm"], record["pre_delay"], record["post_delay"],
                        record["plc_input"], record["plc_output"]
                    ])
                
            print(f"[TRACKER] SUCCESS: Added record #{index}: {sku} {size} -> {mm_len}mm ({result_category})")
        except Exception as e:
            print(f"[TRACKER] ERROR adding record: {e}")
            import traceback
            traceback.print_exc()

    def export_to_excel(self) -> str:
        """Export records and automated statistics to Excel file using xlsxwriter"""
        if not self.session_dir or not self.records:
            return ""
            
        filename = f"consistency_report_{self.session_id}.xlsx"
        path = os.path.join(self.session_dir, filename)
        
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet("Consistency Data")
        
        # Formatting
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'
        })
        cell_format = workbook.add_format({
            'border': 1, 'align': 'center'
        })
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'font_color': '#2E75B6'
        })
        stat_lbl_format = workbook.add_format({
            'bold': True, 'bg_color': '#F2F2F2', 'border': 1
        })
        stat_val_format = workbook.add_format({
            'border': 1, 'align': 'right', 'num_format': '#,##0.0000'
        })

        # --- Statistics Calculation ---
        mm_values = [r["mm_len"] for r in self.records if r["mm_len"] > 0]
        count = len(mm_values)
        
        if count > 0:
            avg = sum(mm_values) / count
            variance = sum((x - avg) ** 2 for x in mm_values) / count
            std_dev = math.sqrt(variance)
            min_val = min(mm_values)
            max_val = max(mm_values)
            val_range = max_val - min_val
            
            # 95% Confidence Interval for mean (using simplified Z=1.96)
            # CI = mean +/- (1.96 * sigma / sqrt(n))
            ci_margin = 1.96 * (std_dev / math.sqrt(count))
            ci_lower = avg - ci_margin
            ci_upper = avg + ci_margin
            
            # Repeatability (6-sigma)
            repeatability_6s = 6 * std_dev
        else:
            avg = std_dev = min_val = max_val = val_range = ci_lower = ci_upper = repeatability_6s = 0

        # --- Write Statistics Summary ---
        worksheet.write(1, 1, "STATISTICAL SUMMARY (Repeatability Analysis)", title_format)
        
        summary_data = [
            ("Measurement Count", count, ""),
            ("Mean (Average)", avg, "mm"),
            ("Std Deviation (σ)", std_dev, "mm"),
            ("Range (Max-Min)", val_range, "mm"),
            ("Min Value", min_val, "mm"),
            ("Max Value", max_val, "mm"),
            ("Confidence Interval (95%)", f"{ci_lower:.4f} - {ci_upper:.4f}", "mm"),
            ("Repeatability (6-Sigma)", repeatability_6s, "mm")
        ]
        
        start_row = 3
        for i, (label, val, unit) in enumerate(summary_data):
            worksheet.write(start_row + i, 1, label, stat_lbl_format)
            worksheet.write(start_row + i, 2, val, stat_val_format)
            worksheet.write(start_row + i, 3, unit, cell_format)
        
        # --- Write Data Table ---
        data_start_row = start_row + len(summary_data) + 2
        headers = ["Index", "Timestamp", "SKU", "Size", "Result", 
                   "Length (px)", "Width (px)", "Length (mm)", "Width (mm)", 
                   "Target (mm)", "Deviation (mm)",
                   "Pre-Cap Delay (ms)", "Post-Res Delay (ms)",
                   "PLC Input", "PLC Output", "Detection Image"]
        
        for col, header in enumerate(headers):
            worksheet.write(data_start_row, col, header, header_format)
            worksheet.set_column(col, col, 14)
        
        # Image column wider to fit thumbnails
        worksheet.set_column(15, 15, 25)
        
        # Result cell formats (create once, reuse)
        good_fmt = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#C6EFCE', 'font_color': '#006100'})
        reject_fmt = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        oven_fmt = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
            
        for row_idx, rec in enumerate(self.records):
            row = data_start_row + 1 + row_idx
            worksheet.write(row, 0, rec["index"], cell_format)
            worksheet.write(row, 1, rec["timestamp"], cell_format)
            worksheet.write(row, 2, rec["sku"], cell_format)
            worksheet.write(row, 3, rec["size"], cell_format)
            
            # Format Result cell with color
            res = rec["result"]
            if "GOOD" in res or res == "OK":
                res_c = good_fmt
            elif "REJECT" in res or "BS" in res:
                res_c = reject_fmt
            elif "OVEN" in res:
                res_c = oven_fmt
            else:
                res_c = cell_format
            worksheet.write(row, 4, res, res_c)
            
            worksheet.write(row, 5, rec["px_len"], cell_format)
            worksheet.write(row, 6, rec["px_wid"], cell_format)
            worksheet.write(row, 7, rec["mm_len"], cell_format)
            worksheet.write(row, 8, rec["mm_wid"], cell_format)
            worksheet.write(row, 9, rec["target_mm"], cell_format)
            worksheet.write(row, 10, rec["deviation_mm"], cell_format)
            worksheet.write(row, 11, rec.get("pre_delay", 0), cell_format)
            worksheet.write(row, 12, rec.get("post_delay", 0), cell_format)
            worksheet.write(row, 13, rec["plc_input"], cell_format)
            worksheet.write(row, 14, rec["plc_output"], cell_format)
            
            # Embed detection image as thumbnail
            img_path = os.path.join(self.session_dir, rec["image_path"])
            if os.path.exists(img_path):
                # Set row height to fit image (90px ≈ 67.5 points)
                worksheet.set_row(row, 90)
                # Scale image to fit cell (approx 160x90 px)
                worksheet.insert_image(row, 15, img_path, {
                    'x_scale': 0.15, 'y_scale': 0.15,
                    'x_offset': 2, 'y_offset': 2,
                    'object_position': 1
                })
            else:
                worksheet.write(row, 15, "Image not found", cell_format)
            
        workbook.close()
        return path

    def get_count(self) -> int:
        return len(self.records)
