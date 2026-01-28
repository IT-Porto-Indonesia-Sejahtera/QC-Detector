"""
ArUco Marker PDF Generator for QC Detector
Generates a printable PDF with ArUco markers for camera calibration.
"""

import cv2
import numpy as np
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import tempfile

# A4 dimensions in mm
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297


def generate_aruco_marker(marker_id: int, size_px: int = 200, dictionary_id=cv2.aruco.DICT_4X4_50):
    """Generate an ArUco marker image."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    return marker_image


def create_aruco_pdf(
    output_path: str,
    marker_id: int = 0,
    marker_size_mm: float = 50.0,
    include_border: bool = True,
    border_mm: float = 10.0
):
    """
    Create a PDF with an ArUco marker for printing.
    
    Args:
        output_path: Path to save the PDF
        marker_id: ArUco marker ID (0-49 for DICT_4X4_50)
        marker_size_mm: Physical size of the marker in millimeters
        include_border: Whether to include a white border around the marker
        border_mm: Size of the white border in mm
    """
    # Create PDF
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    
    # Generate high-resolution marker (600 DPI equivalent for quality printing)
    # 1 inch = 25.4 mm, so for marker_size_mm at 600 DPI:
    dpi = 600
    marker_px = int((marker_size_mm / 25.4) * dpi)
    marker_image = generate_aruco_marker(marker_id, marker_px)
    
    # Convert to PIL Image
    pil_image = Image.fromarray(marker_image)
    
    # Add white border if requested
    if include_border:
        total_size_px = marker_px + int((border_mm * 2 / 25.4) * dpi)
        bordered_image = Image.new('L', (total_size_px, total_size_px), 255)
        border_px = int((border_mm / 25.4) * dpi)
        bordered_image.paste(pil_image, (border_px, border_px))
        pil_image = bordered_image
        total_size_mm = marker_size_mm + (border_mm * 2)
    else:
        total_size_mm = marker_size_mm
    
    # Convert to RGB
    pil_image = pil_image.convert('RGB')
    
    # Save to temporary file (fpdf2 needs a file path or BytesIO)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        pil_image.save(tmp, format='PNG', dpi=(dpi, dpi))
        tmp_path = tmp.name
    
    try:
        # Calculate position (centered on page)
        x = (A4_WIDTH_MM - total_size_mm) / 2
        y = (A4_HEIGHT_MM - total_size_mm) / 2
        
        # Draw the marker at exact size
        pdf.image(tmp_path, x=x, y=y, w=total_size_mm, h=total_size_mm)
        
        # Add title and instructions
        pdf.set_font("Helvetica", "B", 16)
        title = f"ArUco Marker ID: {marker_id}"
        pdf.set_xy(0, 25)
        pdf.cell(A4_WIDTH_MM, 10, title, align="C")
        
        pdf.set_font("Helvetica", "", 12)
        subtitle = f"Marker Size: {marker_size_mm} mm x {marker_size_mm} mm (Exact)"
        pdf.set_xy(0, 35)
        pdf.cell(A4_WIDTH_MM, 10, subtitle, align="C")
        
        # Add usage instructions at bottom
        pdf.set_font("Helvetica", "", 10)
        instructions = [
            "Instructions:",
            "1. Print this page at 100% scale (no scaling/fit to page)",
            f"2. Verify the marker measures exactly {marker_size_mm} mm with a ruler",
            "3. Place the marker on a flat surface within camera view",
            "4. Run auto-calibration in QC Detector settings",
            "",
            "Dictionary: DICT_4X4_50 | Compatible with QC Detector"
        ]
        
        y_pos = A4_HEIGHT_MM - 70
        for line in instructions:
            pdf.set_xy(0, y_pos)
            pdf.cell(A4_WIDTH_MM, 5, line, align="C")
            y_pos += 6
        
        # Add measurement reference lines
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.3)
        
        marker_left = x + border_mm
        marker_right = x + total_size_mm - border_mm
        marker_center_y = y + total_size_mm / 2
        
        # Left tick mark
        pdf.line(marker_left - 5, marker_center_y, marker_left - 2, marker_center_y)
        pdf.line(marker_left - 5, marker_center_y - 3, marker_left - 5, marker_center_y + 3)
        
        # Right tick mark  
        pdf.line(marker_right + 2, marker_center_y, marker_right + 5, marker_center_y)
        pdf.line(marker_right + 5, marker_center_y - 3, marker_right + 5, marker_center_y + 3)
        
        # Size label
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(marker_right + 7, marker_center_y - 2)
        pdf.cell(20, 5, f"{marker_size_mm} mm")
        
        # Add verification box
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(10, A4_HEIGHT_MM - 25)
        pdf.cell(0, 5, "Print Verification: This line should measure exactly 100mm:", align="L")
        pdf.set_line_width(0.5)
        pdf.line(10, A4_HEIGHT_MM - 18, 110, A4_HEIGHT_MM - 18)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(10, A4_HEIGHT_MM - 16)
        pdf.cell(0, 5, "|-- 0mm", align="L")
        pdf.set_xy(105, A4_HEIGHT_MM - 16)
        pdf.cell(0, 5, "100mm --|")
        
        # Save PDF
        pdf.output(output_path)
        print(f"[OK] ArUco marker PDF saved to: {output_path}")
        
    finally:
        # Clean up temp file
        os.unlink(tmp_path)
    
    return output_path


def create_multi_marker_pdf(
    output_path: str,
    marker_ids: list = [0, 1, 2, 3],
    marker_size_mm: float = 40.0
):
    """
    Create a PDF with multiple ArUco markers for backup/variety.
    """
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    
    # Calculate grid positions (2x2)
    margin = 25
    spacing = 20
    
    positions = [
        (margin, 55),  # Top-left
        (A4_WIDTH_MM - margin - marker_size_mm, 55),  # Top-right
        (margin, 55 + marker_size_mm + spacing + 15),  # Bottom-left
        (A4_WIDTH_MM - margin - marker_size_mm, 55 + marker_size_mm + spacing + 15),  # Bottom-right
    ]
    
    dpi = 600
    marker_px = int((marker_size_mm / 25.4) * dpi)
    
    temp_files = []
    
    try:
        for i, marker_id in enumerate(marker_ids[:4]):
            marker_image = generate_aruco_marker(marker_id, marker_px)
            pil_image = Image.fromarray(marker_image).convert('RGB')
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                pil_image.save(tmp, format='PNG', dpi=(dpi, dpi))
                temp_files.append(tmp.name)
            
            x, y = positions[i]
            pdf.image(temp_files[-1], x=x, y=y, w=marker_size_mm, h=marker_size_mm)
            
            # Label each marker
            pdf.set_font("Helvetica", "", 9)
            pdf.set_xy(x, y + marker_size_mm + 2)
            pdf.cell(marker_size_mm, 5, f"ID: {marker_id} | {marker_size_mm}mm", align="C")
        
        # Title
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(0, 20)
        pdf.cell(A4_WIDTH_MM, 10, "ArUco Markers - DICT_4X4_50", align="C")
        
        pdf.set_font("Helvetica", "", 11)
        pdf.set_xy(0, 32)
        pdf.cell(A4_WIDTH_MM, 10, f"Each marker: {marker_size_mm} mm x {marker_size_mm} mm | Print at 100% scale", align="C")
        
        # Instructions at bottom
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(0, A4_HEIGHT_MM - 40)
        pdf.cell(A4_WIDTH_MM, 5, "Cut out any marker and use for QC Detector calibration.", align="C")
        pdf.set_xy(0, A4_HEIGHT_MM - 33)
        pdf.cell(A4_WIDTH_MM, 5, "All markers are compatible with the auto-calibration feature.", align="C")
        
        pdf.output(output_path)
        print(f"[OK] Multi-marker PDF saved to: {output_path}")
        
    finally:
        for tmp_path in temp_files:
            os.unlink(tmp_path)
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate ArUco marker PDF for QC Detector calibration")
    parser.add_argument("--id", type=int, default=0, help="Marker ID (0-49 for DICT_4X4_50)")
    parser.add_argument("--size", type=float, default=50.0, help="Marker size in mm (default: 50)")
    parser.add_argument("--output", type=str, default=None, help="Output PDF path")
    parser.add_argument("--multi", action="store_true", help="Generate multi-marker sheet")
    
    args = parser.parse_args()
    
    # Default output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    if args.multi:
        output_path = args.output or os.path.join(project_dir, "aruco_markers_sheet.pdf")
        create_multi_marker_pdf(output_path, marker_size_mm=args.size)
    else:
        output_path = args.output or os.path.join(project_dir, f"aruco_marker_id{args.id}_{int(args.size)}mm.pdf")
        create_aruco_pdf(output_path, marker_id=args.id, marker_size_mm=args.size)
    
    print(f"\n[SUCCESS] PDF ready for printing!")
    print(f"   IMPORTANT: Print at 100% scale (actual size) for accurate calibration.")
