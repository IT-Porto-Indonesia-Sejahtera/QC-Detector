from __future__ import annotations
"""
YOLOv8-seg Inference Module

Segmentation using YOLOv8n-seg (nano variant optimized for CPU).
Includes a "Safety Net" that falls back to the raw YOLO mask if
precision refinement fails (e.g., Green Sandal on Green Screen).
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


def segment_image(image, conf=0.25):
    """
    Segment the image using YOLOv8n-seg.
    """
    import time
    
    model = get_model()
    if model is None:
        return None, None, 0
    
    # Load image if path is provided
    if isinstance(image, str):
        img = cv2.imread(image)
    else:
        img = image
    
    if img is None:
        print("[YOLOv8-seg] Error: Could not load image")
        return None, None, 0
    
    h, w = img.shape[:2]
    img_area = h * w
    img_center = (w / 2, h / 2)
    
    start_time = time.time()
    
    # Run inference
    results = model(
        img,
        device='cuda' if __import__('torch').cuda.is_available() else 'cpu',
        conf=conf,
        verbose=False
    )
    
    inference_time = (time.time() - start_time) * 1000  # Convert to ms
    
    if len(results) == 0 or results[0].masks is None:
        print("[YOLOv8-seg] No objects detected")
        return None, None, inference_time
    
    # Get all masks and boxes from results
    masks = results[0].masks.data.cpu().numpy()
    boxes = results[0].boxes.xyxy.cpu().numpy()  # Bounding boxes
    
    if len(masks) == 0 or len(boxes) == 0:
        print("[YOLOv8-seg] No masks found")
        return None, None, inference_time
    
    print(f"[YOLOv8-seg] Found {len(masks)} objects, selecting best one...")
    
    # Find the best detection using same scoring logic
    best_box = None
    best_score = -1
    best_mask = None
    
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
            best_mask = mask_resized
    
    if best_box is None:
        print("[YOLOv8-seg] No suitable detection found")
        return None, None, inference_time
    
    # === ROI Extraction ===
    x1, y1, x2, y2 = map(int, best_box)
    
    # Expand ROI (10% margin) to prevent cutting edges
    margin = 0.10  
    box_w = x2 - x1
    box_h = y2 - y1
    x1 = max(0, int(x1 - box_w * margin))
    y1 = max(0, int(y1 - box_h * margin))
    x2 = min(w, int(x2 + box_w * margin))
    y2 = min(h, int(y2 + box_h * margin))
    
    roi = img[y1:y2, x1:x2]
    if roi.size == 0: return None, None, inference_time
    
    # === SAFETY NET STRATEGY ===
    # 1. Get the Raw YOLO Mask for this ROI
    yolo_mask_roi = best_mask[y1:y2, x1:x2]
    _, yolo_mask_roi = cv2.threshold(yolo_mask_roi, 0.5, 255, cv2.THRESH_BINARY)
    yolo_mask_roi = yolo_mask_roi.astype(np.uint8)

    # 2. Run Precision Refinement (Strong Mask)
    from .measurement import strong_mask
    cv_mask_roi = strong_mask(roi)
    
    # 3. COMPARE: Calculate Intersection over Union (IoU)
    intersection = cv2.bitwise_and(yolo_mask_roi, cv_mask_roi)
    union = cv2.bitwise_or(yolo_mask_roi, cv_mask_roi)
    count_inter = cv2.countNonZero(intersection)
    count_union = cv2.countNonZero(union)
    
    iou = count_inter / (count_union + 1e-6)
    print(f"[YOLOv8-seg] Mask Agreement (IoU): {iou:.3f}")

    final_roi_mask = None
    
    # DECISION LOGIC:
    # If IoU > 0.60: The CV mask is valid (Agrees with AI, but sharper edges).
    # If IoU < 0.60: The CV mask failed (Camouflage/Noise). Fallback to YOLO.
    if iou > 0.60:
        # print("[YOLOv8-seg] Precision mask valid. Using refined mask.")
        final_roi_mask = cv_mask_roi
    else:
        print(f"[YOLOv8-seg] Precision mask diverged (IoU={iou:.2f}). Fallback to YOLO raw mask.")
        final_roi_mask = cv2.morphologyEx(yolo_mask_roi, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
        if cv2.countNonZero(final_roi_mask) == 0:
            final_roi_mask = cv_mask_roi

    # === Final Contour Extraction ===
    contours, _ = cv2.findContours(final_roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        print("[YOLOv8-seg] No contour found in final mask")
        return None, None, inference_time
    
    largest_contour_roi = max(contours, key=cv2.contourArea)
    
    # Transform coordinates back to global image
    largest_contour = largest_contour_roi.copy()
    largest_contour[:, :, 0] += x1
    largest_contour[:, :, 1] += y1
    
    # Create final binary mask for display
    mask_binary = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_binary, [largest_contour], -1, 255, thickness=-1)
    
    return mask_binary, largest_contour, inference_time

    return contour, mask, inference_time


def is_available():
    """Check if YOLO dependencies are available."""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        return False