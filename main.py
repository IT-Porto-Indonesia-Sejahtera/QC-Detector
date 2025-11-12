import os
from model.measurement import measure_sandals

if __name__ == "__main__":
    img_path = "QC-Detector\\input\\temp_assets\\WhatsApp Image 2025-11-11 at 14.54.35 (1).jpeg"
    mm_per_px = None 

    print("Measuring:", img_path)
    res = measure_sandals(
        img_path, 
        mm_per_px=mm_per_px,
        draw_output=True,
        save_out="output/measured.png"
    )
    print("Results:", res)
