import cv2
import numpy as np
from .preprocessor import preprocess_and_masks, ensure_dir, display_resized
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

def measure_sandals(path, mm_per_px=None, draw_output=True, save_out=None):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = preprocess_and_masks(gray)
    contours = find_largest_contours(mask, num_contours=1)
    out = img.copy()
    results = []

    for i, cnt in enumerate(contours):
        if cv2.contourArea(cnt) < 1000:
            continue
        box, w, h, angle = endpoints_via_minrect(cnt)
        px_length = max(w, h)
        px_width = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width = px_width * mm_per_px if mm_per_px else None
        # contour line
        cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)
        # bounding box
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        results.append({
            # 'side': i,
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None
        })

    if draw_output:
        display_resized(out, max_height=800)
    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)
    return results