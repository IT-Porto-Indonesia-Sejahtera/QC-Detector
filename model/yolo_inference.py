"""
YOLOv8-seg Inference Module

Segmentation using YOLOv8n-seg (nano variant optimized for CPU).
Faster than FastSAM with better mask quality for curved edges.
"""

import cv2
import numpy as np
import os

# Global model instance (lazy loading)
_model = None
_model_path = None


def get_model():
    """
    Load YOLOv8n-seg model (lazy loading with caching).
    Downloads ~6.7MB model on first use.
    """
    global _model, _model_path
    
    if _model is not None:
        return _model
    
    try:
        from ultralytics import YOLO
        
        # YOLOv8n-seg is the nano variant (~6.7MB, optimized for CPU)
        model_name = "yolov8n-seg.pt"
        
        # Store in model folder
        model_dir = os.path.dirname(os.path.abspath(__file__))
        _model_path = os.path.join(model_dir, model_name)
        
        print(f"[YOLOv8-seg] Loading model: {model_name}")
        
        # YOLO will auto-download if not present
        _model = YOLO(model_name)
        
        print("[YOLOv8-seg] Model loaded successfully")
        return _model
        
    except ImportError:
        print("[YOLOv8-seg] Error: ultralytics not installed. Run: pip install ultralytics")
        return None
    except Exception as e:
        print(f"[YOLOv8-seg] Error loading model: {e}")
        return None


def refine_ai_mask_with_edges(image, ai_mask):
    """
    Return AI mask as-is without refinement.
    Any morphological operation erodes edges, so we preserve the original AI boundaries.
    
    Args:
        image: Original BGR image (not used, kept for compatibility)
        ai_mask: Binary mask from AI model (values 0 or 255)
        
    Returns:
        ai_mask: Original unmodified mask
    """
    if ai_mask is None or np.sum(ai_mask) == 0:
        return ai_mask
    
    # Return AI mask without any refinement to preserve full edges
    print("[Refinement] Using raw AI mask (no morphology - full edge preservation)")
    return ai_mask






def segment_image(image, conf=0.25):
    import time
    model = get_model()
    if model is None: return None, None, 0
    
    if isinstance(image, str): img = cv2.imread(image)
    else: img = image
    
    if img is None: return None, None, 0
    
    h, w = img.shape[:2]
    img_area = h * w
    img_center = (w / 2, h / 2)
    
    start_time = time.time()
    
    results = model(img, device='cpu', conf=conf, verbose=False)
    inference_time = (time.time() - start_time) * 1000
    
    if len(results) == 0 or results[0].masks is None:
        return None, None, inference_time
    
    masks = results[0].masks.data.cpu().numpy()
    boxes = results[0].boxes.xyxy.cpu().numpy()
    
    if len(masks) == 0: return None, None, inference_time
    
    print(f"[YOLOv8-seg] Found {len(masks)} objects, selecting best one...")
    best_box = None
    best_score = -1
    
    for i, (mask, box) in enumerate(zip(masks, boxes)):
        mask_resized = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        mask_area = np.sum(mask_resized > 0)
        area_ratio = mask_area / img_area
        
        if area_ratio > 0.70: continue
        if area_ratio < 0.01: continue
        
        moments = cv2.moments(mask_resized)
        if moments["m00"] > 0:
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            center_dist = np.sqrt((cx - img_center[0])**2 + (cy - img_center[1])**2)
            max_dist = np.sqrt(img_center[0]**2 + img_center[1]**2)
            center_score = 1 - (center_dist / max_dist)
        else:
            center_score = 0
            
        score = (area_ratio * 0.7) + (center_score * 0.3)
        if score > best_score:
            best_score = score
            best_box = box
            
    if best_box is None: return None, None, inference_time
    
    # === CRITICAL FIX: PERBESAR ROI MARGIN ===
    x1, y1, x2, y2 = map(int, best_box)
    
    # Ubah dari 0.05 menjadi 0.20 (20%)
    # Ini memberi ruang agar contour tidak terpotong oleh kotak bounding box
    margin = 0.20  
    
    box_w = x2 - x1
    box_h = y2 - y1
    x1 = max(0, int(x1 - box_w * margin))
    y1 = max(0, int(y1 - box_h * margin))
    x2 = min(w, int(x2 + box_w * margin))
    y2 = min(h, int(y2 + box_h * margin))
    
    print(f"[YOLOv8-seg] Extracting ROI: ({x1}, {y1}) to ({x2}, {y2}) with 20% margin")
    roi = img[y1:y2, x1:x2]
    
    if roi.size == 0: return None, None, inference_time
    
    # Gunakan Auto Select Mask pada ROI
    from model.measurement import auto_select_mask
    roi_mask = auto_select_mask(roi)
    
    # Validasi mask
    roi_area = roi_mask.shape[0] * roi_mask.shape[1]
    mask_pixels = cv2.countNonZero(roi_mask)
    
    # Fallback ke YOLO Raw Mask jika mask presisi gagal total
    if mask_pixels < (roi_area * 0.02):
        print(f"[YOLOv8-seg] Precision mask failed. Fallback to raw YOLO mask.")
        return None, None, inference_time

    contours, _ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0: return None, None, inference_time
    
    largest_contour_roi = max(contours, key=cv2.contourArea)
    
    # Transformasi koordinat ROI ke Global
    largest_contour = largest_contour_roi.copy()
    largest_contour[:, :, 0] += x1
    largest_contour[:, :, 1] += y1
    
    mask_binary = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_binary, [largest_contour], -1, 255, thickness=-1)
    
    return mask_binary, largest_contour, inference_time



def get_mask_and_contour(image_path):
    """
    Convenience function to get mask and contour for measurement.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        contour: Largest object contour (for measurement)
        mask: Binary mask
        inference_time: Time in milliseconds
    """
    mask, contour, inference_time = segment_image(image_path)
    return contour, mask, inference_time


def is_available():
    """Check if YOLOv8-seg dependencies are available."""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        return False
