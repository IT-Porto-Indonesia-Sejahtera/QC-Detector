import cv2
import numpy as np
from .measurement import endpoints_via_minrect, find_largest_contours
from .preprocessor import preprocess_and_masks

def process_video(frame, mm_per_px=None, draw_output=False, save_out=None):
    """
    Analisis satu frame video dan kembalikan hasil + frame dengan anotasi.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = preprocess_and_masks(gray)
    contours = find_largest_contours(mask, num_contours=1)
    out = frame.copy()
    results = []

    for cnt in contours:
        if cv2.contourArea(cnt) < 1000:
            continue
        box, w, h, angle = endpoints_via_minrect(cnt)
        px_length = max(w, h)
        px_width = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width = px_width * mm_per_px if mm_per_px else None

        cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        results.append({
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None
        })

    if save_out:
        cv2.imwrite(save_out, out)

    return results, out
