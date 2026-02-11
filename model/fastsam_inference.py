"""
FastSAM Inference Module

Lightweight AI-based segmentation using FastSAM (Fast Segment Anything Model).
Runs on CPU and provides better edge detection than traditional contour methods.
"""

import cv2
import numpy as np
import os

# Global model instance (lazy loading)
_model = None
_model_path = None


def get_model():
    """
    Load FastSAM model (lazy loading with caching).
    Downloads ~23MB model on first use.
    """
    global _model, _model_path
    
    if _model is not None:
        return _model
    
    try:
        from ultralytics import YOLO
        
        # FastSAM-s is the smaller variant (~23MB)
        model_name = "FastSAM-s.pt"
        
        # Store in model folder
        model_dir = os.path.dirname(os.path.abspath(__file__))
        _model_path = os.path.join(model_dir, model_name)
        
        print(f"[FastSAM] Loading model: {model_name}")
        
        # YOLO will auto-download if not present
        _model = YOLO(model_name)
        
        print("[FastSAM] Model loaded successfully")
        return _model
        
    except ImportError:
        print("[FastSAM] Error: ultralytics not installed. Run: pip install ultralytics")
        return None
    except Exception as e:
        print(f"[FastSAM] Error loading model: {e}")
        return None


def refine_ai_mask_with_edges(image, ai_mask):
    """
    Tighten AI mask boundaries to match true object edges.
    FastSAM tends to produce masks that extend significantly beyond object boundaries.
    
    Args:
        image: Original BGR image (for potential edge-guided refinement)
        ai_mask: Binary mask from AI model (values 0 or 255)
        
    Returns:
        refined_mask: Eroded mask that better matches actual object edges
    """
    if ai_mask is None or np.sum(ai_mask) == 0:
        return ai_mask
    
    # Now that we run at native resolution (1080p+), we need stronger erosion 
    # to remove the AI "halo" / shadows.
    # 5x5 kernel with 3 iterations removes ~6-8 pixels of bleed from edges
    kernel = np.ones((5, 5), np.uint8)
    refined = cv2.erode(ai_mask, kernel, iterations=3)
    
    print("[Refinement] Applied strong erosion (5x5, 3 iters) to high-res FastSAM mask")
    return refined






def segment_image(image, conf=0.4, iou=0.9):
    """
    Segment the image using FastSAM.
    
    Args:
        image: BGR image (numpy array) or path to image
        conf: Confidence threshold (default 0.4 to reduce shadow/background noise)
        iou: IoU threshold for NMS (default 0.9)
    
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
        print("[FastSAM] Error: Could not load image")
        return None, None, 0
    
    h, w = img.shape[:2]
    img_area = h * w
    img_center = (w / 2, h / 2)
    
    start_time = time.time()
    
    # Calculate optimal inference size (preserve detail)
    # Use the largest dimension, capped at 1920 to prevent memory issues
    # Must be a multiple of 32 for YOLO/FastSAM
    max_dim = max(h, w)
    inference_size = min(max_dim, 1920) 
    # Round to nearest multiple of 32
    inference_size = int(round(inference_size / 32) * 32)
    
    print(f"[FastSAM] Running inference at size {inference_size}x{inference_size} (Original: {w}x{h})")
    
    # Run inference
    results = model(
        img,
        device='cuda' if __import__('torch').cuda.is_available() else 'cpu',
        retina_masks=True,
        imgsz=inference_size,
        conf=conf,
        iou=iou,
        verbose=False
    )
    
    inference_time = (time.time() - start_time) * 1000  # Convert to ms
    
    if len(results) == 0 or results[0].masks is None:
        print("[FastSAM] No objects detected")
        return None, None, inference_time
    
    # Get all masks
    masks = results[0].masks.data.cpu().numpy()
    
    if len(masks) == 0:
        print("[FastSAM] No masks found")
        return None, None, inference_time
    
    print(f"[FastSAM] Found {len(masks)} masks, selecting best one...")
    
    # Find the best mask (not just the largest!)
    # We want: 
    # 1. Not too large (>70% of image = likely background)
    # 2. Not too small (<1% of image = noise)
    # 3. Prefer masks centered in the image
    
    best_mask = None
    best_score = -1
    
    for i, mask in enumerate(masks):
        # Resize mask to image dimensions
        mask_resized = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Calculate mask area ratio
        mask_area = np.sum(mask_resized > 0)
        area_ratio = mask_area / img_area
        
        # Skip if too large (background) or too small (noise)
        if area_ratio > 0.70:
            print(f"[FastSAM]   Mask {i}: {area_ratio*100:.1f}% - skipped (too large, likely background)")
            continue
        if area_ratio < 0.01:
            print(f"[FastSAM]   Mask {i}: {area_ratio*100:.1f}% - skipped (too small)")
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
        # area_ratio is 0-0.7, center_score is 0-1
        score = (area_ratio * 0.7) + (center_score * 0.3)
        
        print(f"[FastSAM]   Mask {i}: {area_ratio*100:.1f}% area, center_score={center_score:.2f}, score={score:.3f}")
        
        if score > best_score:
            best_score = score
            best_mask = mask_resized
    
    if best_mask is None:
        print("[FastSAM] No suitable mask found, using largest non-background mask")
        # Fallback: use the largest mask that's not the background
        for mask in masks:
            mask_resized = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
            mask_area = np.sum(mask_resized > 0)
            area_ratio = mask_area / img_area
            if area_ratio < 0.85:  # Accept anything smaller than 85%
                best_mask = mask_resized
                break
    
    if best_mask is None:
        print("[FastSAM] Could not find suitable object mask")
        return None, None, inference_time
    
    # Convert to binary mask (0 or 255)
    mask_binary = (best_mask * 255).astype(np.uint8)
    
    # Apply edge refinement (hybrid: AI detection + Standard edge precision)
    print("[FastSAM] Applying edge refinement for curved boundaries...")
    mask_binary = refine_ai_mask_with_edges(img, mask_binary)
    
    # Extract contour from refined mask
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return mask_binary, None, inference_time
    
    # Get the largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Smooth the contour using approxPolyDP for cleaner curved edges
    epsilon = 0.002 * cv2.arcLength(largest_contour, True)
    smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    print(f"[FastSAM] Segmentation complete in {inference_time:.1f}ms")
    
    return mask_binary, smoothed_contour, inference_time


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
    """Check if FastSAM dependencies are available."""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        return False
