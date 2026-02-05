#!/usr/bin/env python3
"""
Generate a clean A3 ArUco calibration sheet with 8 markers only.
No lines, no text, no decorations - just pure markers for maximum detection reliability.
"""

import cv2
import numpy as np
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from io import BytesIO

def generate_aruco_marker(marker_id, size_px=500, dictionary_id=cv2.aruco.DICT_4X4_250):
    """Generate a single ArUco marker image."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    return marker_img

def create_clean_calibration_pdf(output_path, marker_size_mm=50):
    """
    Create a clean A3 landscape PDF with 8 ArUco markers.
    Layout: 3 markers on top row, 2 on middle (left/right edges), 3 on bottom row.
    """
    page_width, page_height = landscape(A3)
    c = canvas.Canvas(output_path, pagesize=landscape(A3))
    
    marker_size = marker_size_mm * mm
    margin = 20 * mm
    
    # Calculate positions for 3-2-3 layout
    # Top row: 3 markers evenly spaced
    # Middle row: 2 markers on far left and far right
    # Bottom row: 3 markers evenly spaced
    
    usable_width = page_width - 2 * margin - marker_size
    usable_height = page_height - 2 * margin - marker_size
    
    # X positions for 3 columns
    x_left = margin
    x_center = margin + usable_width / 2
    x_right = margin + usable_width
    
    # Y positions for 3 rows
    y_top = margin + usable_height
    y_middle = margin + usable_height / 2
    y_bottom = margin
    
    # Marker positions (x, y) and their IDs
    # Using IDs 0-7 from DICT_4X4_250
    positions = [
        # Top row (left to right)
        (x_left, y_top, 0),
        (x_center, y_top, 1),
        (x_right, y_top, 2),
        # Middle row
        (x_left, y_middle, 3),
        (x_right, y_middle, 4),
        # Bottom row (left to right)
        (x_left, y_bottom, 5),
        (x_center, y_bottom, 6),
        (x_right, y_bottom, 7),
    ]
    
    # Generate and place each marker
    for x, y, marker_id in positions:
        # Generate marker image
        marker_img = generate_aruco_marker(marker_id, size_px=500)
        
        # Save to temporary buffer
        from PIL import Image
        pil_img = Image.fromarray(marker_img)
        img_buffer = BytesIO()
        pil_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Draw on PDF
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(img_buffer)
        c.drawImage(img_reader, x, y, width=marker_size, height=marker_size)
    
    c.save()
    print(f"Created: {output_path}")
    print(f"Marker size: {marker_size_mm}mm x {marker_size_mm}mm")
    print(f"Dictionary: DICT_4X4_250")
    print(f"Marker IDs: 0-7")

if __name__ == "__main__":
    import os
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "aruco_clean_8markers.pdf")
    create_clean_calibration_pdf(output_path, marker_size_mm=50)
