import os
from datetime import datetime
from model.measurement import measure_sandals
import project_utilities as putils
import app.main_windows as app  # import the PyQt app

def run_cli_mode():
    """Run measurement in command-line mode."""
    img_path = "QC-Detector\\input\\temp_assets\\WhatsApp Image 2025-11-11 at 14.54.35 (1).jpeg"
    mm_per_px = None 

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"measured_{timestamp}.png"
    output_path = os.path.join("QC-Detector", "output", "log_output", output_filename)

    print("Measuring:", img_path)
    normalized_path = putils.normalize_path(img_path)
    print("Normalized path:", normalized_path)

    res = measure_sandals(
        normalized_path, 
        mm_per_px=mm_per_px,
        draw_output=True,
        save_out=output_path
    )
    print("Results:", res)

def run_ui_mode():
    """Run the GUI version of the app."""
    app.run_app()

if __name__ == "__main__":
    MODE = "ui"
    if MODE == "ui":
        run_ui_mode()
    else:
        run_cli_mode()
