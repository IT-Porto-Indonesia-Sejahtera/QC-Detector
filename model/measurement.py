import cv2
import numpy as np
import os
from .preprocessor import preprocess_and_masks, ensure_dir

def base_mask(gray):
    return preprocess_and_masks(gray)

def get_green_chromakey_mask(img):
    """
    Mendeteksi background hijau dan membalikkannya.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([90, 255, 255])
    bg_mask = cv2.inRange(hsv, lower_green, upper_green)
    object_mask = cv2.bitwise_not(bg_mask)
    
    # Cleaning
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    return object_mask

def strong_mask(img):
    h, w = img.shape[:2]
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    L, A, B = cv2.split(lab)
    
    # 1. White Detection
    white_hsv = cv2.inRange(hsv, np.array([0, 0, 140]), np.array([180, 60, 255]))
    white_lab = cv2.inRange(lab, np.array([170, 0, 0]), np.array([255, 255, 255]))
    white_combined = cv2.bitwise_or(white_hsv, white_lab)
    white_ratio = np.sum(white_combined > 0) / (h * w)
    is_white_object = white_ratio > 0.10
    
    # 2. Edges
    sobel_x = cv2.Sobel(L, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(L, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    magnitude_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, edges = cv2.threshold(magnitude_norm, 25, 255, cv2.THRESH_BINARY)
    
    # 3. Adaptive Logic: White vs Low-Contrast vs Dark Objects ===
    if is_white_object:
        # WHITE LOGIC
        _, mask_a = cv2.threshold(A, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_clean = cv2.morphologyEx(mask_a, cv2.MORPH_OPEN, kernel_clean, iterations=1)
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel_clean, iterations=2)
        final_mask = cv2.dilate(mask_clean, kernel_clean, iterations=1)
    else:
        # FALLBACK LOGIC (Dark/Green Objects)
        th1 = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 51, 5)
        final_mask = cv2.bitwise_or(th1, edges)
        
        # Reduced morphology to prevent smoothing out valid corners
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)) # Sedikit diperkecil dari 9x9
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2) # Iterasi dikurangi jadi 2
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Fill holes
    h_m, w_m = final_mask.shape
    mask_flood = np.zeros((h_m+2, w_m+2), np.uint8)
    filled = final_mask.copy()
    cv2.floodFill(filled, mask_flood, (0, 0), 255)
    final_mask = final_mask | cv2.bitwise_not(filled)
    
    # === DELETE: FINAL ERODE REMOVED ===
    # final_mask = cv2.erode(final_mask, None, iterations=1) # <--- HAPUS INI
    
    return final_mask


def endpoints_via_minrect(contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    (center), (w, h), angle = rect
    return box, w, h, angle

def find_largest_contours(mask, num_contours=2):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Sort by convex hull area (safer for metrology, handles partial edges better)
    cnts = sorted(cnts, key=lambda c: cv2.contourArea(cv2.convexHull(c)), reverse=True)
    return cnts[:num_contours]

def auto_select_mask(img):
    h, w = img.shape[:2]
    img_area = h * w

    # 1. White Check
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    white_hsv = cv2.inRange(img_hsv, np.array([0, 0, 140]), np.array([180, 60, 255]))
    white_ratio = np.sum(white_hsv > 0) / img_area
    if white_ratio > 0.10:
        return strong_mask(img)

    # 2. Chroma Key Check
    chroma_mask = get_green_chromakey_mask(img)
    cnts_chroma = find_largest_contours(chroma_mask, 1)
    if len(cnts_chroma) > 0:
        area = cv2.contourArea(cnts_chroma[0])
        if area > (img_area * 0.05): 
            x,y,bw,bh = cv2.boundingRect(cnts_chroma[0])
            aspect_ratio = float(bw)/bh
            if 0.2 < aspect_ratio < 5.0:
                return chroma_mask

    # 3. Fallback
    return strong_mask(img)

def principal_axis(contour):
    pts = contour.reshape(-1, 2).astype(np.float32)
    mean = np.mean(pts, axis=0)

    # PCA via covariance
    cov = np.cov(pts.T)
    eigenvalues, eigenvectors = np.linalg.eig(cov)

    # Major axis = largest eigenvalue
    idx = np.argmax(eigenvalues)
    direction = eigenvectors[:, idx]
    direction /= np.linalg.norm(direction)

    return mean, direction

def project_onto_axis(contour, origin, direction):
    pts = contour.reshape(-1, 2).astype(np.float32)
    vecs = pts - origin
    proj = vecs @ direction  # dot product
    return proj

def refined_endpoints(contour):
    origin, axis = principal_axis(contour)
    proj = project_onto_axis(contour, origin, axis)

    # Sort points along axis
    order = np.argsort(proj)
    proj_sorted = proj[order]
    pts_sorted = contour.reshape(-1, 2)[order]

    n = len(proj_sorted)
    k = max(int(0.05 * n), 10)  # 5% tails

    # Left end
    xL = proj_sorted[:k]
    yL = np.arange(len(xL))
    aL, bL = np.polyfit(yL, xL, 1)
    left = aL * (-0.5) + bL

    # Right end
    xR = proj_sorted[-k:]
    yR = np.arange(len(xR))
    aR, bR = np.polyfit(yR, xR, 1)
    right = aR * (len(xR) - 0.5) + bR

    length_px = right - left
    return length_px

def measure_sandals(path, mm_per_px=None, draw_output=True, save_out=None, use_sam=False, use_yolo=False):
    """
    Measure object dimensions in an image.
    
    Args:
        path: Path to the image file
        mm_per_px: Conversion factor from pixels to millimeters
        draw_output: Whether to draw contours on output image
        save_out: Path to save the output image
        use_sam: If True, use FastSAM (AI) for segmentation instead of traditional method
        use_yolo: If True, use YOLOv8-seg (AI) for segmentation (recommended for all objects)
        
    Returns:
        results: List of measurement dictionaries
        out: Output image with drawn contours
    """
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")

    out = img.copy()
    results = []
    inference_time = 0
    
    if use_yolo:
        try:
            from .yolo_inference import segment_image
            mask, contour, inference_time = segment_image(img)
            
            if contour is None or cv2.contourArea(contour) < 1000:
                print("[YOLO-Seg] Fallback to Auto-Select Mask")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
            else:
                contours = [contour]
                
        except ImportError as e:
            print(f"[YOLO-Seg] Error: {e}")
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
    else:
        mask = auto_select_mask(img)
        contours = find_largest_contours(mask, num_contours=1)

    for cnt in contours:
        contour_area = cv2.contourArea(cnt)
        if contour_area < 2000:
            continue

        box, w, h, angle = endpoints_via_minrect(cnt)
        px_length = refined_endpoints(cnt)
        px_width  = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width  = px_width * mm_per_px if mm_per_px else None

        color = (255, 0, 255) if use_sam else (255, 255, 0)
        cv2.drawContours(out, [cnt], -1, color, 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        result_dict = {
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None,
            'contour_area_px': float(contour_area),
            'detection_method': 'yolo' if use_yolo else 'standard'
        }
        
        # Log detection result to detections.log
        try:
            from project_utilities.logger_config import get_detection_logger
            det_logger = get_detection_logger()
            log_msg = f"Detection Result: Length={result_dict['real_length_mm']:.2f}mm, Width={result_dict['real_width_mm']:.2f}mm, Method={result_dict['detection_method']}" if result_dict['real_length_mm'] else f"Detection Result (PX): Length={px_length:.1f}px, Width={px_width:.1f}px"
            det_logger.info(log_msg)
        except Exception as e:
            print(f"Failed to log detection: {e}")

        
        if inference_time > 0:
            result_dict['inference_time_ms'] = inference_time
            
        results.append(result_dict)

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out
