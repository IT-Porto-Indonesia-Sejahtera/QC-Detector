import cv2
import numpy as np
import os
from .preprocessor import preprocess_and_masks, ensure_dir

def base_mask(gray):
    return preprocess_and_masks(gray)

def strong_mask(img):
    """
    Edge-first metrology approach for precision object detection.
    Uses Sobel gradients for sub-pixel accuracy and explicit white object detection.
    """
    h, w = img.shape[:2]
    
    # Convert to LAB and HSV for analysis
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    L, A, B = cv2.split(lab)
    
    # === 1. Explicit White Object Detection ===
    # High V (brightness) + Low S (saturation) = white/light objects
    white_hsv = cv2.inRange(hsv, 
                            np.array([0, 0, 140]),      # Low saturation, high value
                            np.array([180, 60, 255]))
    
    # Also check LAB: High L (lightness)
    white_lab = cv2.inRange(lab,
                           np.array([170, 0, 0]),       # High L lightness
                           np.array([255, 255, 255]))
    
    # Combine white detectors
    white_combined = cv2.bitwise_or(white_hsv, white_lab)
    
    # Check if this is a white object (>10% white pixels)
    white_pixel_ratio = np.sum(white_combined > 0) / (h * w)
    is_white_object = white_pixel_ratio > 0.10
    
    # === 2. Sobel Edge Detection (better than Canny) ===
    # Sobel gradient magnitude for sub-pixel accuracy
    sobel_x = cv2.Sobel(L, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(L, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    
    # === 2.5 Gradient Direction Coherence (CRITICAL FIX) ===
    angle = np.arctan2(sobel_y, sobel_x)  # radians

    # Normalize angle to [0, pi]
    angle = np.abs(angle)

    # Coherence: strong if neighboring gradients align
    kernel = np.ones((3, 3), np.float32)
    mean_mag = cv2.filter2D(magnitude, -1, kernel)
    coherence = magnitude / (mean_mag + 1e-6)

    # Boost weak but coherent edges
    boost_mask = (coherence > 0.6) & (magnitude > 8)
    magnitude_boosted = magnitude.copy()
    magnitude_boosted[boost_mask] *= 1.8

    # Normalize magnitude to 0-255
    magnitude_norm = cv2.normalize(magnitude_boosted, None, 0, 255, cv2.NORM_MINMAX)
    magnitude_norm = magnitude_norm.astype(np.uint8)
    
    # Threshold for edges
    _, edges = cv2.threshold(magnitude_norm, 25, 255, cv2.THRESH_BINARY)
    
    # === 3. Adaptive Logic: White vs Dark Objects ===
    if is_white_object:
        print(f"[strong_mask] White object detected ({white_pixel_ratio*100:.1f}% white) - using edge-first approach")
        
        # For white: Use edges only to avoid over-segmentation
        final_mask = edges.copy()
        
        # Close small gaps in edges
        # kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        # final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        # Directional edge bridging (no inflation)
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))

        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel_h, iterations=1)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel_v, iterations=1)

        
    else:
        print(f"[strong_mask] Dark object detected ({white_pixel_ratio*100:.1f}% white) - using LAB + edges")
        
        # For dark: Combine LAB threshold + edges
        # Adaptive threshold on L channel for dark objects
        th1 = cv2.adaptiveThreshold(
            L, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            51, 5
        )
        
        # Combine LAB mask + edges
        final_mask = cv2.bitwise_or(th1, edges)
        
        # Morphology for smooth contours
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # === 4. Inner Contour Enforcement (Metrology Trick) ===
    # Erode slightly to ensure we measure from inside boundary
    # This provides consistent precision and avoids aliasing
    # kernel_inner = np.ones((2, 2), np.uint8)
    # final_mask = cv2.erode(final_mask, kernel_inner, iterations=1)
    final_mask = cv2.erode(final_mask, None, iterations=1)

    return final_mask


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
        # Use YOLOv8-seg for AI-based segmentation (recommended)
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
    elif use_sam:
        # Use FastSAM for AI-based segmentation
        try:
            from .fastsam_inference import segment_image
            
            mask, contour, inference_time = segment_image(img)
            
            if contour is not None:
                contours = [contour]
            else:
                print("[SAM] No contour found, falling back to standard method")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
                
        except ImportError as e:
            print(f"[SAM] FastSAM not available: {e}, using standard method")
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
    else:
        # Use traditional contour detection
        mask = auto_select_mask(img)
        contours = find_largest_contours(mask, num_contours=1)

    for cnt in contours:
        contour_area = cv2.contourArea(cnt)
        if contour_area < 2000:
            if use_sam:
                print(f"[SAM DEBUG] Skipping contour with area {contour_area:.0f}px² (too small)")
            continue

        box, w, h, angle = endpoints_via_minrect(cnt)

        px_length = max(w, h)
        px_width  = min(w, h)

        real_length = px_length * mm_per_px if mm_per_px else None
        real_width  = px_width * mm_per_px if mm_per_px else None

        # Debug output for SAM
        if use_sam:
            x, y, bw, bh = cv2.boundingRect(cnt)
            print(f"[SAM DEBUG] ═══════════════════════════════════════")
            print(f"[SAM DEBUG] Detection Method: FastSAM (AI)")
            print(f"[SAM DEBUG] Contour Area: {contour_area:.0f} px²")
            print(f"[SAM DEBUG] Bounding Rect: x={x}, y={y}, w={bw}, h={bh}")
            print(f"[SAM DEBUG] MinAreaRect: w={w:.1f}, h={h:.1f}, angle={angle:.1f}°")
            print(f"[SAM DEBUG] ───────────────────────────────────────")
            print(f"[SAM DEBUG] Measured Length: {px_length:.1f} px")
            print(f"[SAM DEBUG] Measured Width:  {px_width:.1f} px")
            if mm_per_px:
                print(f"[SAM DEBUG] Real Length: {real_length:.2f} mm")
                print(f"[SAM DEBUG] Real Width:  {real_width:.2f} mm")
            print(f"[SAM DEBUG] ═══════════════════════════════════════")

        # Draw contours - use different color for SAM vs standard
        if use_sam:
            cv2.drawContours(out, [cnt], -1, (255, 0, 255), 2)  # Magenta for SAM
        else:
            cv2.drawContours(out, [cnt], -1, (255, 255, 0), 2)  # Cyan for standard
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        result_dict = {
            'px_length': float(px_length),
            'px_width': float(px_width),
            'real_length_mm': float(real_length) if real_length else None,
            'real_width_mm': float(real_width) if real_width else None,
            'contour_area_px': float(contour_area),
            'detection_method': 'sam' if use_sam else 'standard'
        }
        
        if use_sam and inference_time > 0:
            result_dict['inference_time_ms'] = inference_time
            
        results.append(result_dict)

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out
