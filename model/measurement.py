import cv2
import numpy as np
import os
from .preprocessor import preprocess_and_masks, ensure_dir

def evaluate_mask_quality(mask):
    """
    Scoring system to judge if a mask is 'Good' (Smooth & Solid) or 'Bad' (Jagged & Hollow).
    Returns a score between 0.0 and 1.0.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    
    # Get largest contour
    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    perimeter = cv2.arcLength(c, True)
    
    if area < 1000 or perimeter == 0:
        return 0.0
    
    # 1. Solidity (Area / Convex Hull Area) - Checks if object is "filled"
    hull = cv2.convexHull(c)
    hull_area = cv2.contourArea(hull)
    solidity = area / (hull_area + 1e-6)
    
    # 2. Compactness (4*pi*Area / Perimeter^2) - Checks if edges are smooth
    # A circle is 1.0. A jagged noisy shape is close to 0.
    compactness = (4 * np.pi * area) / (perimeter ** 2)
    
    # Weighted Score: Solidity is most important to avoid "Hollow" green noise
    score = (solidity * 0.6) + (compactness * 0.4)
    return score

def get_channel_mask(img, channel_type):
    """Generates a mask based on a specific strategy"""
    h, w = img.shape[:2]
    
    # Setup Background Sampling (Corners)
    mask_corners = np.zeros((h, w), dtype=np.uint8)
    corner_size = max(5, int(min(w, h) * 0.10))
    cv2.rectangle(mask_corners, (0, 0), (corner_size, corner_size), 255, -1)
    cv2.rectangle(mask_corners, (w-corner_size, 0), (w, corner_size), 255, -1)
    cv2.rectangle(mask_corners, (0, h-corner_size), (corner_size, h), 255, -1)
    cv2.rectangle(mask_corners, (w-corner_size, h-corner_size), (w, h), 255, -1)
    
    raw_mask = None
    
    if channel_type == 'A': # LAB 'A' Channel (Green-Red axis)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        _, A, _ = cv2.split(lab)
        # Otsu threshold on A channel is usually perfect for Black/White/Color on Green
        _, raw_mask = cv2.threshold(A, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Check if we need to invert (if corners are white, invert)
        corner_mean = cv2.mean(raw_mask, mask=mask_corners)[0]
        if corner_mean > 127:
            raw_mask = cv2.bitwise_not(raw_mask)
            
    elif channel_type == 'S': # HSV 'S' Channel (Saturation)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        _, S, _ = cv2.split(hsv)
        
        # Calculate difference from background saturation
        mean_bg_sat = cv2.mean(S, mask=mask_corners)[0]
        diff_sat = cv2.absdiff(S, int(mean_bg_sat))
        
        # Threshold: Background is hyper-saturated, Sandal is matte.
        # Fixed threshold (25) often works better than Otsu for saturation diff
        _, raw_mask = cv2.threshold(diff_sat, 25, 255, cv2.THRESH_BINARY)
        
    elif channel_type == 'L': # LAB 'L' Channel (Lightness) - Fallback
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        L, _, _ = cv2.split(lab)
        # Adaptive threshold for contrast
        raw_mask = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY_INV, 21, 5)

    # Clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    clean_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    # Floodfill to ensure it's solid (crucial for scoring)
    h_m, w_m = clean_mask.shape
    mask_flood = np.zeros((h_m+2, w_m+2), np.uint8)
    flooded = clean_mask.copy()
    cv2.floodFill(flooded, mask_flood, (0, 0), 255)
    filled_mask = cv2.bitwise_not(flooded)
    final_mask = clean_mask | filled_mask
    
    return final_mask

def strong_mask(img):
    """
    Adaptive 'Tournament' Segmentation.
    Strategically picks the best method (Color vs Saturation) based on quality.
    """
    
    # 1. Try STRATEGY A (Color / A-Channel)
    # This is the champion for Black, White, and Patterned sandals.
    mask_a = get_channel_mask(img, 'A')
    score_a = evaluate_mask_quality(mask_a)
    
    # If Strategy A is very good (Solid & Smooth), STOP HERE.
    # This prevents the noisy 'Saturation' logic from ruining a good Black sandal mask.
    if score_a > 0.65:
        # print(f"[strong_mask] Fast Success: A-Channel (Score: {score_a:.2f})")
        return mask_a
        
    # 2. Try STRATEGY B (Saturation / S-Channel)
    # We only run this if A-Channel failed (likely a Green Sandal).
    mask_s = get_channel_mask(img, 'S')
    score_s = evaluate_mask_quality(mask_s)
    
    # Compare candidates
    if score_s > score_a:
        # print(f"[strong_mask] Winner: S-Channel (Score: {score_s:.2f} vs A: {score_a:.2f})")
        return mask_s
    else:
        # print(f"[strong_mask] Winner: A-Channel (Score: {score_a:.2f} vs S: {score_s:.2f})")
        return mask_a

def endpoints_via_minrect(contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    (center), (w, h), angle = rect
    return box, w, h, angle

def find_largest_contours(mask, num_contours=2):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=lambda c: cv2.contourArea(cv2.convexHull(c)), reverse=True)
    return cnts[:num_contours]

# def auto_select_mask(img):
#     # Standard fallback logic
#     return strong_mask(img)

def auto_select_mask(img):
    mask = strong_mask(img)
    score = evaluate_mask_quality(mask)

    # Rescue logic for black objects
    if score < 0.50:
        dark_mask = dark_object_mask(img)
        dark_score = evaluate_mask_quality(dark_mask)

        if dark_score > score:
            return dark_mask

    return mask


def dark_object_mask(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold isolates dark object
    mask = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        41, 5
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

    return mask


def principal_axis(contour):
    pts = contour.reshape(-1, 2).astype(np.float32)
    mean = np.mean(pts, axis=0)
    cov = np.cov(pts.T)
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    idx = np.argmax(eigenvalues)
    direction = eigenvectors[:, idx]
    direction /= np.linalg.norm(direction)
    return mean, direction

def project_onto_axis(contour, origin, direction):
    pts = contour.reshape(-1, 2).astype(np.float32)
    vecs = pts - origin
    proj = vecs @ direction
    return proj

def refined_endpoints(contour):
    origin, axis = principal_axis(contour)
    proj = project_onto_axis(contour, origin, axis)
    order = np.argsort(proj)
    proj_sorted = proj[order]
    
    n = len(proj_sorted)
    k = max(int(0.05 * n), 10)

    xL = proj_sorted[:k]
    yL = np.arange(len(xL))
    aL, bL = np.polyfit(yL, xL, 1)
    left = aL * (-0.5) + bL

    xR = proj_sorted[-k:]
    yR = np.arange(len(xR))
    aR, bR = np.polyfit(yR, xR, 1)
    right = aR * (len(xR) - 0.5) + bR

    length_px = right - left
    return length_px

def measure_sandals(path, mm_per_px=None, draw_output=True, save_out=None, use_sam=False, use_yolo=False, use_advanced=False):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")

    out = img.copy()
    results = []
    inference_time = 0
    detection_method = 'standard'
    
    if use_advanced:
        detection_method = 'advanced (yolox+sam)'
        try:
            from .advanced_inference import segment_image as advanced_segment
            mask, contour, inference_time = advanced_segment(img)
            
            if contour is not None:
                contours = [contour]
            else:
                print("[Advanced] No contour found, falling back to standard method")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
                detection_method = 'standard (fallback)'
                
        except ImportError as e:
            print(f"[Advanced] Not available: {e}, using standard method")
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
            detection_method = 'standard (fallback)'
    elif use_yolo:
        detection_method = 'yolo-seg'
        try:
            from .yolo_inference import segment_image
            mask, contour, inference_time = segment_image(img)
            
            if contour is not None:
                contours = [contour]
            else:
                print("[YOLO-Seg] No contour found, falling back to standard method")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
                
        except ImportError as e:
            print(f"[YOLO-Seg] YOLOv8-seg not available: {e}, using standard method")
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
    else:
        mask = auto_select_mask(img)
        contours = find_largest_contours(mask, num_contours=1)

    for cnt in contours:
        contour_area = cv2.contourArea(cnt)
        if contour_area < 2000:
            continue
        
        rect = cv2.minAreaRect(cnt)
        (w, h) = rect[1]
        
        if min(w, h) == 0:
            continue
        
        aspect_ratio = max(w, h) / min(w, h)
    
        # Sandal shape sanity filter
        if aspect_ratio < 2.0 or aspect_ratio > 6.0:
            continue
    

        box, w, h, angle = endpoints_via_minrect(cnt)
        px_length = refined_endpoints(cnt)
        px_width  = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width  = px_width * mm_per_px if mm_per_px else None

        cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        result_dict = {
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None,
            'contour_area_px': float(contour_area),
            'detection_method': detection_method
        }
        
        if inference_time > 0:
            result_dict['inference_time_ms'] = inference_time
            
        results.append(result_dict)

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out