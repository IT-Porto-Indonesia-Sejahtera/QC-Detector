"""
Size-Based Categorization Utility
=================================
Categorizes sandal measurements into GOOD, OVEN, or REJECT
based on deviation from target size.

Business Logic:
- Target Size = Selected Size + Otorisasi
- Target Length (cm) = Target Size × (2/3)
- Deviation is measured in "size units" (1 size unit = 2/3 cm ≈ 6.67 mm)

Categories:
- GOOD 1: 0 to +0.25 size units
- GOOD 2: +0.25 to +0.5 size units
- OVEN 1: +0.5 to +1.0 size units
- OVEN 2: +1.0 to +1.5 size units
- REJECT: Below 0 OR Above +1.5 size units
"""

from typing import Dict, Any, Optional


def categorize_measurement(
    measured_length_mm: float,
    selected_size: float,
    otorisasi: float = 0.0
) -> Dict[str, Any]:
    """
    Categorize a sandal measurement based on size deviation.
    
    Args:
        measured_length_mm: The measured length in millimeters.
        selected_size: The selected size (e.g., 40).
        otorisasi: The authorization scaling factor (e.g., +1).
    
    Returns:
        Dictionary with:
        - category: "GOOD", "OVEN", or "REJECT"
        - detail: "GOOD 1", "GOOD 2", "OVEN 1", "OVEN 2", or "REJECT"
        - target_size: The calculated target size (selected + otorisasi)
        - target_length_mm: The target length in mm
        - measured_size: The measured length converted to size units
        - deviation_size: The deviation from target in size units
        - deviation_mm: The deviation from target in mm
    """
    # Calculate target
    target_size = selected_size + otorisasi
    target_length_cm = target_size * (2 / 3)
    target_length_mm = target_length_cm * 10  # Convert to mm
    
    # Convert measured length to size units
    measured_length_cm = measured_length_mm / 10
    measured_size = measured_length_cm * (3 / 2)  # Inverse of 2/3
    
    # Calculate deviation in size units
    deviation_size = measured_size - target_size
    deviation_mm = measured_length_mm - target_length_mm
    
    # Categorize based on deviation
    if deviation_size < 0:
        category = "REJECT"
        detail = "REJECT (UNDER)"
    elif deviation_size <= 0.25:
        category = "GOOD"
        detail = "GOOD 1"
    elif deviation_size <= 0.5:
        category = "GOOD"
        detail = "GOOD 2"
    elif deviation_size <= 1.0:
        category = "OVEN"
        detail = "OVEN 1"
    elif deviation_size <= 1.5:
        category = "OVEN"
        detail = "OVEN 2"
    else:
        category = "REJECT"
        detail = "REJECT (OVER)"
    
    return {
        "category": category,
        "detail": detail,
        "target_size": target_size,
        "target_length_mm": round(target_length_mm, 2),
        "measured_size": round(measured_size, 2),
        "deviation_size": round(deviation_size, 4),
        "deviation_mm": round(deviation_mm, 2)
    }


def get_category_color(category: str) -> str:
    """
    Get the display color for a category.
    
    Returns:
        Hex color code for UI display.
    """
    colors = {
        "GOOD": "#4CAF50",   # Green
        "OVEN": "#FF9800",   # Orange
        "REJECT": "#D32F2F"  # Red
    }
    return colors.get(category, "#999999")
