import cv2
import numpy as np
from .preprocessor import preprocess_and_masks, ensure_dir
import os

def endpoints_via_minrect(contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    (center), (w, h), angle = rect
    return box, w, h, angle

def find_largest_contours(mask, num_contours=2):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=lambda c: cv2.contourArea(c), reverse=True)
    return cnts[:num_contours]

def measure_live_sandals(input_data, mm_per_px=None, draw_output=True, save_out=None):
    """
    Returns:
      results list, processed image array (with text drawn)
    """
    # Load image
    if isinstance(input_data, str):
        img = cv2.imread(input_data)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {input_data}")
    else:
        img = input_data.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = preprocess_and_masks(gray)
    contours = find_largest_contours(mask, num_contours=1)

    out = img.copy()
    results = []

    for cnt in contours:
        if cv2.contourArea(cnt) < 1000:
            continue

        box, w, h, angle = endpoints_via_minrect(cnt)
        px_length = max(w, h)
        px_width = min(w, h)

        # Conversions
        real_length_mm = px_length * mm_per_px if mm_per_px else None
        real_width_mm  = px_width  * mm_per_px if mm_per_px else None

        real_length_cm = real_length_mm / 10.0 if real_length_mm else None
        real_width_cm  = real_width_mm / 10.0 if real_width_mm else None

        # PASS/FAIL (dummy logic)
        if real_length_cm:
            pass_fail = "PASS" if real_length_cm > 20 else "FAIL"
        else:
            pass_fail = "UNKNOWN"

        # Draw contour + box
        cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        # Put text near box
        if draw_output:

            # top-left corner of the box
            x, y = box[0]

            # Draw background for readability
            cv2.rectangle(out, (x, y - 60), (x + 200, y), (0, 0, 0), -1)

            # Draw measurement text
            cv2.putText(out, f"L: {real_length_cm:.1f} cm",
                        (x + 5, y - 40), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 255), 2)

            cv2.putText(out, f"W: {real_width_cm:.1f} cm",
                        (x + 5, y - 18), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 200, 255), 2)

            # PASS/FAIL text
            color = (0, 255, 0) if pass_fail == "PASS" else (0, 0, 255)
            cv2.putText(out, pass_fail,
                        (x + 120, y - 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, color, 2)

        # Add to results dict
        results.append({
            "px_length": float(px_length),
            "px_width": float(px_width),
            "real_length_mm": float(real_length_mm) if real_length_mm else None,
            "real_width_mm": float(real_width_mm) if real_width_mm else None,
            "real_length_cm": float(real_length_cm) if real_length_cm else None,
            "real_width_cm": float(real_width_cm) if real_width_cm else None,
            "pass_fail": pass_fail
        })

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out

