import cv2
import numpy as np
from .preprocessor import preprocess_and_masks, ensure_dir
from .measurement import strong_mask, auto_select_mask, find_largest_contours, refined_endpoints
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

def measure_live_sandals(input_data, mm_per_px=None, draw_output=True, save_out=None, use_sam=False, use_yolo=False):
    """
    Live camera measurement with improved detection.
    
    Args:
        use_yolo: If True, use YOLOv8-seg for detection (recommended)
    
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

    inference_time = 0
    
    if use_yolo:
        # Use YOLO-Seg (recommended for all objects)
        try:
            from .yolo_inference import segment_image
            mask, contour, inference_time = segment_image(img)
            if contour is not None:
                contours = [contour]
            else:
                print("[LIVE] YOLO failed, using auto_select_mask")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
        except ImportError as e:
            print(f"[LIVE] YOLO not available: {e}, using auto_select_mask")
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
    elif use_sam:
        # Use FastSAM
        try:
            from .fastsam_inference import segment_image
            mask, contour, inference_time = segment_image(img)
            if contour is not None:
                contours = [contour]
            else:
                print("[LIVE] SAM failed, using auto_select_mask")
                mask = auto_select_mask(img)
                contours = find_largest_contours(mask, num_contours=1)
        except ImportError:
            mask = auto_select_mask(img)
            contours = find_largest_contours(mask, num_contours=1)
    else:
        # Use improved auto_select_mask (with strong_mask for beige detection)
        mask = auto_select_mask(img)
        contours = find_largest_contours(mask, num_contours=1)

    out = img.copy()
    results = []

    for cnt in contours:
        if cv2.contourArea(cnt) < 1000:
            continue

        box, w, h, angle = endpoints_via_minrect(cnt)
        
        # Use refined_endpoints for better length measurement
        px_length = refined_endpoints(cnt)
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

        # Draw contour + box with method-specific colors
        if use_yolo:
            contour_color = (0, 165, 255)  # Orange for YOLO
        elif use_sam:
            contour_color = (255, 0, 255)  # Magenta for SAM
        else:
            contour_color = (255, 255, 0)  # Cyan for standard
        cv2.drawContours(out, [cnt], -1, contour_color, 2)
        cv2.drawContours(out, [box], 0, (0, 255, 0), 2)

        # Put text at TOP-LEFT of image (not near the box)
        if draw_output:
            # Fixed position at top-left of frame
            x, y = 20, 35

            # Draw background for readability (bigger for more info)
            cv2.rectangle(out, (10, 10), (320, 155), (0, 0, 0), -1)

            method_text = "Method: "
            if use_yolo:
                method_text += "YOLO-Seg (AI)"
            elif use_sam:
                method_text += "FastSAM (AI)"
            else:
                method_text += "Standard (Beige Ready)"
            cv2.putText(out, method_text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.putText(out, f"Length: {real_length_mm:.1f} mm ({px_length:.0f} px)",
                        (x, y + 25), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0, 255, 255), 2)

            cv2.putText(out, f"Width:  {real_width_mm:.1f} mm ({px_width:.0f} px)",
                        (x, y + 50), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0, 200, 255), 2)
            
            cv2.putText(out, f"Scale: {mm_per_px:.6f} mm/px",
                        (x, y + 75), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (200, 200, 200), 1)
            
            inf_text = f"L: {real_length_cm:.2f}cm W: {real_width_cm:.2f}cm"
            if use_sam and inference_time > 0:
                inf_text += f" ({inference_time:.0f}ms)"
            
            cv2.putText(out, inf_text,
                        (x, y + 100), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (150, 255, 150), 1)

        # Add to results dict
        results.append({
            "px_length": float(px_length),
            "px_width": float(px_width),
            "real_length_mm": float(real_length_mm) if real_length_mm else None,
            "real_width_mm": float(real_width_mm) if real_width_mm else None,
            "real_length_cm": float(real_length_cm) if real_length_cm else None,
            "real_width_cm": float(real_width_cm) if real_width_cm else None,
            "pass_fail": pass_fail,
            "inference_time_ms": inference_time if use_sam else 0
        })

    if save_out:
        ensure_dir(os.path.dirname(save_out))
        cv2.imwrite(save_out, out)

    return results, out
