import cv2
import numpy as np
from .preprocessor import preprocess_and_masks, ensure_dir, display_resized
import os

def endpoints_via_minrect(contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    d1 = np.linalg.norm(box[0] - box[1])
    d2 = np.linalg.norm(box[1] - box[2])
    if d1 > d2:
        px_dist = d1
        p1 = (box[1] + box[2]) // 2
        p2 = (box[3] + box[0]) // 2
    else:
        px_dist = d2
        p1 = (box[0] + box[1]) // 2
        p2 = (box[2] + box[3]) // 2
    return tuple(p1.astype(int)), tuple(p2.astype(int)), px_dist

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
        p1, p2, px_dist = endpoints_via_minrect(cnt)
        real_dist = px_dist * mm_per_px if mm_per_px else None
        cv2.drawContours(out, [cnt], -1, (255,255,0), 2)
        cv2.line(out, p1, p2, (255,0,0), 3)
        results.append({'side': i, 'px_dist': float(px_dist), 'real_mm': real_dist})

    if draw_output:
        display_resized(out, max_height=800)
    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)
    return results