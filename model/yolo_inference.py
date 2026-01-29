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
    """
    Segment the image using YOLOv8n-seg.
    
    Args:
        image: BGR image (numpy array) or path to image
        conf: Confidence threshold (default 0.25)
    
    Returns:
        mask: Binary mask of the largest detected object (numpy array)
        contour: Contour of the largest object
        inference_time: Time taken for inference in milliseconds
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
        device='cpu',
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
    best_idx = -1
    
    for i, (mask, box) in enumerate(zip(masks, boxes)):
        # Resize mask to image dimensions for area calculation
        mask_resized = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Calculate mask area ratio
        mask_area = np.sum(mask_resized > 0)
        area_ratio = mask_area / img_area
        
        # Skip if too large (background) or too small (noise)
        if area_ratio > 0.70:
            print(f"[YOLOv8-seg]   Detection {i}: {area_ratio*100:.1f}% - skipped (too large, likely background)")
            continue
        if area_ratio < 0.01:
            print(f"[YOLOv8-seg]   Detection {i}: {area_ratio*100:.1f}% - skipped (too small)")
            continue
        
        # Calculate mask centroid
        moments = cv2.moments(mask_resized)
        if moments["m00"] > 0:
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            
            # Distance from center (normalized)
            center_dist = np.sqrt((cx - img_center[0])**2 + (cy - img_center[1])**2)
            max_dist = np.sqrt(img_center[0]**2 + img_center[1]**2)
            center_score = 1 - (center_dist / max_dist)  # Higher = more centered
        else:
            center_score = 0
        
        # Score: prefer larger masks that are centered
        score = (area_ratio * 0.7) + (center_score * 0.3)
        
        print(f"[YOLOv8-seg]   Detection {i}: {area_ratio*100:.1f}% area, center_score={center_score:.2f}, score={score:.3f}")
        
        if score > best_score:
            best_score = score
            best_box = box
            best_idx = i
    
    if best_box is None:
        print("[YOLOv8-seg] No suitable detection found")
        return None, None, inference_time
    
    # === HYBRID APPROACH: Use YOLO bounding box to extract ROI ===
    x1, y1, x2, y2 = map(int, best_box)
    
    # Expand ROI slightly to ensure we don't cut edges (5% margin)
    margin = 0.05
    box_w = x2 - x1
    box_h = y2 - y1
    x1 = max(0, int(x1 - box_w * margin))
    y1 = max(0, int(y1 - box_h * margin))
    x2 = min(w, int(x2 + box_w * margin))
    y2 = min(h, int(y2 + box_h * margin))
    
    print(f"[YOLOv8-seg] Extracting ROI: ({x1}, {y1}) to ({x2}, {y2})")
    
    # Extract ROI from original image
    roi = img[y1:y2, x1:x2]
    
    if roi.size == 0:
        print("[YOLOv8-seg] Error: Empty ROI")
        return None, None, inference_time
    
    # === Run precise contour detection INSIDE ROI ===
    print("[YOLOv8-seg] Running precision contour detection inside ROI...")
    from model.measurement import strong_mask
    
    roi_mask = strong_mask(roi)
    
    # Find contour in ROI space
    contours, _ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        print("[YOLOv8-seg] No contour found in ROI")
        return None, None, inference_time
    
    # Get the largest contour in ROI
    largest_contour_roi = max(contours, key=cv2.contourArea)
    
    # === Transform contour coordinates to global image space ===
    largest_contour = largest_contour_roi.copy()
    largest_contour[:, :, 0] += x1  # Shift X by ROI offset
    largest_contour[:, :, 1] += y1  # Shift Y by ROI offset
    
    # Create full-size mask for visualization
    mask_binary = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_binary, [largest_contour], -1, 255, thickness=-1)
    
    print(f"[YOLOv8-seg] Hybrid segmentation complete in {inference_time:.1f}ms")
    print(f"[YOLOv8-seg] ROI-based contour: {len(largest_contour)} points")
    
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
