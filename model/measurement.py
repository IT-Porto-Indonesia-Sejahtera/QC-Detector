import cv2
import numpy as np
import os
from .preprocessor import preprocess_and_masks, ensure_dir

def base_mask(gray):
    return preprocess_and_masks(gray)

def strong_mask(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)

    th1 = cv2.adaptiveThreshold(
        L, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51, 5
    )

    edges = cv2.Canny(L, 40, 120)

    mask = cv2.bitwise_or(th1, edges)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    return mask

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

def auto_select_mask(img):
    """
    Logika pemilihan:
    1. coba base_mask (untuk kontras)
    2. cek kualitas:
       - apakah area kontur terbesar > threshold
       - apakah bentuknya solid (rasio bounding box)
    3. Jika buruk → ganti strong_mask
    """

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask1 = base_mask(gray)
    cnts1 = find_largest_contours(mask1, 1)

    if len(cnts1) == 0 or cv2.contourArea(cnts1[0]) < 2000:
        return strong_mask(img)

    area = cv2.contourArea(cnts1[0])
    x, y, w, h = cv2.boundingRect(cnts1[0])
    rect_area = w * h

    solidity = area / (rect_area + 1e-6)

    if solidity < 0.4:
        return strong_mask(img)

    return mask1

def measure_sandals(path, mm_per_px=None, draw_output=True, save_out=None):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")

    mask = auto_select_mask(img)

    contours = find_largest_contours(mask, num_contours=1)
    out = img.copy()
    results = []

    for cnt in contours:
        if cv2.contourArea(cnt) < 2000:
            continue

        box, w, h, angle = endpoints_via_minrect(cnt)

        px_length = max(w, h)
        px_width  = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width  = px_width * mm_per_px if mm_per_px else None

        cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        results.append({
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None
        })

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out
