"""
Advanced Inference Module — YOLOv8-X + SAM Pipeline

Two-model architecture:
  1. The Spotter (YOLOv8-X): Finds the bounding box. The Extra Large model
     is smart enough to see texture differences even when colors are identical.
  2. The Surgeon (SAM): Pixel-perfect segmentation within that bounding box.
     Uses edge and depth cues — doesn't care about class labels or color.
"""

import cv2
import numpy as np
import os

# Global model instances (lazy loading)
_yolo_model = None
_sam_model = None


def _get_device():
    """Auto-detect CUDA GPU, fallback to CPU."""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"[Advanced] Using GPU: {torch.cuda.get_device_name(0)}")
            return 'cuda'
    except ImportError:
        pass
    return 'cpu'


def get_yolo_model():
    """
    Load YOLOv8-X detection model (lazy loading with caching).
    Downloads ~130MB model on first use.
    """
    global _yolo_model

    if _yolo_model is not None:
        return _yolo_model

    try:
        from ultralytics import YOLO

        model_name = "yolov8x.pt"
        print(f"[Advanced] Loading YOLOv8-X (The Spotter): {model_name}")

        _yolo_model = YOLO(model_name)

        print("[Advanced] YOLOv8-X loaded successfully")
        return _yolo_model

    except ImportError:
        print("[Advanced] Error: ultralytics not installed. Run: pip install ultralytics")
        return None
    except Exception as e:
        print(f"[Advanced] Error loading YOLOv8-X: {e}")
        return None


def get_sam_model():
    """
    Load SAM (Segment Anything Model) via Ultralytics (lazy loading with caching).
    Downloads ~375MB model on first use.
    """
    global _sam_model

    if _sam_model is not None:
        return _sam_model

    try:
        from ultralytics import SAM

        model_name = "sam_b.pt"
        print(f"[Advanced] Loading SAM (The Surgeon): {model_name}")

        _sam_model = SAM(model_name)

        print("[Advanced] SAM loaded successfully")
        return _sam_model

    except ImportError:
        print("[Advanced] Error: ultralytics not installed. Run: pip install ultralytics")
        return None
    except Exception as e:
        print(f"[Advanced] Error loading SAM: {e}")
        return None


def segment_image(image, conf=0.15):
    """
    Advanced two-model segmentation pipeline.

    1. YOLOv8-X detects objects → bounding box
    2. SAM segments inside that box → pixel-perfect mask

    Args:
        image: BGR image (numpy array) or path to image
        conf: Confidence threshold for YOLOv8-X detection

    Returns:
        mask: Binary mask of the best detected object (numpy array, 0/255)
        contour: Largest contour of the segmented object
        inference_time: Total time for both models in milliseconds
    """
    import time

    yolo_model = get_yolo_model()
    sam_model = get_sam_model()

    if yolo_model is None or sam_model is None:
        print("[Advanced] Error: One or both models failed to load")
        return None, None, 0

    # Load image if path is provided
    if isinstance(image, str):
        img = cv2.imread(image)
    else:
        img = image

    if img is None:
        print("[Advanced] Error: Could not load image")
        return None, None, 0

    h, w = img.shape[:2]
    img_area = h * w
    img_center = (w / 2, h / 2)

    start_time = time.time()

    # ======================================================
    # STEP 1: THE SPOTTER — YOLOv8-X finds the bounding box
    # ======================================================
    print("[Advanced] Step 1: Running YOLOv8-X detection...")

    yolo_results = yolo_model(
        img,
        device=_get_device(),
        conf=conf,
        verbose=False
    )

    yolo_time = (time.time() - start_time) * 1000
    print(f"[Advanced] YOLOv8-X inference: {yolo_time:.0f}ms")

    best_box = None

    if len(yolo_results) == 0 or yolo_results[0].boxes is None or len(yolo_results[0].boxes) == 0:
        print("[Advanced] YOLOv8-X found no objects")
    else:
        boxes = yolo_results[0].boxes.xyxy.cpu().numpy()
        confidences = yolo_results[0].boxes.conf.cpu().numpy()

        print(f"[Advanced] YOLOv8-X found {len(boxes)} objects, selecting best one...")

        # === Select the best bounding box ===
        best_score = -1

        for i, (box, box_conf) in enumerate(zip(boxes, confidences)):
            x1, y1, x2, y2 = box
            box_w = x2 - x1
            box_h = y2 - y1
            box_area = box_w * box_h
            area_ratio = box_area / img_area

            # Skip background-sized or noise-sized detections
            if area_ratio > 0.80:
                continue
            if area_ratio < 0.01:
                continue

            # Center score: prefer objects near image center
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            center_dist = np.sqrt((cx - img_center[0])**2 + (cy - img_center[1])**2)
            max_dist = np.sqrt(img_center[0]**2 + img_center[1]**2)
            center_score = 1 - (center_dist / max_dist)

            # Combined score: area + center + confidence
            score = (area_ratio * 0.4) + (center_score * 0.3) + (float(box_conf) * 0.3)

            print(f"[Advanced]   Box {i}: area={area_ratio*100:.1f}%, center={center_score:.2f}, "
                  f"conf={box_conf:.2f}, score={score:.3f}")

            if score > best_score:
                best_score = score
                best_box = box

    # ======================================================
    # STEP 2: THE SURGEON — SAM segments the object
    # ======================================================
    sam_start = time.time()

    if best_box is not None:
        # === Normal path: YOLO found a box → feed it to SAM ===
        x1, y1, x2, y2 = best_box
        box_w = x2 - x1
        box_h = y2 - y1
        margin = 0.03
        x1_exp = max(0, int(x1 - box_w * margin))
        y1_exp = max(0, int(y1 - box_h * margin))
        x2_exp = min(w, int(x2 + box_w * margin))
        y2_exp = min(h, int(y2 + box_h * margin))

        print(f"[Advanced] Step 2: Running SAM with bounding box [{x1_exp}, {y1_exp}, {x2_exp}, {y2_exp}]...")

        sam_results = sam_model(
            img,
            bboxes=[x1_exp, y1_exp, x2_exp, y2_exp],
            verbose=False
        )
    else:
        # === Fallback path: YOLO is blind → prompt SAM with center point ===
        # SAM uses edges & texture, NOT color — it can see green-on-green
        center_x = int(w / 2)
        center_y = int(h / 2)

        print(f"[Advanced] Step 2: YOLO blind — Running SAM with center point ({center_x}, {center_y})...")

        sam_results = sam_model(
            img,
            points=[[center_x, center_y]],
            labels=[1],  # 1 = foreground point
            verbose=False
        )

    sam_time = (time.time() - sam_start) * 1000
    print(f"[Advanced] SAM inference: {sam_time:.0f}ms")

    if len(sam_results) == 0 or sam_results[0].masks is None or len(sam_results[0].masks) == 0:
        print("[Advanced] SAM produced no masks, falling back to bounding box crop")
        total_time = (time.time() - start_time) * 1000
        return None, None, total_time

    # SAM may return multiple masks — pick the one with the largest area
    sam_masks = sam_results[0].masks.data.cpu().numpy()
    print(f"[Advanced] SAM produced {len(sam_masks)} mask(s)")

    best_sam_mask = None
    best_sam_area = 0

    for i, mask in enumerate(sam_masks):
        mask_resized = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        mask_area = np.sum(mask_resized > 0)
        area_ratio = mask_area / img_area

        # Skip if the mask covers basically the entire image (background)
        if area_ratio > 0.85:
            print(f"[Advanced]   SAM Mask {i}: {area_ratio*100:.1f}% — skipped (background)")
            continue

        if mask_area > best_sam_area:
            best_sam_area = mask_area
            best_sam_mask = mask_resized

    if best_sam_mask is None:
        # If all masks were too large, just use the first one
        print("[Advanced] All SAM masks were large, using first mask")
        best_sam_mask = cv2.resize(sam_masks[0].astype(np.uint8), (w, h),
                                   interpolation=cv2.INTER_NEAREST)

    # Convert to binary mask (0 or 255)
    mask_binary = (best_sam_mask * 255).astype(np.uint8)
    from .measurement import evaluate_mask_quality

    # score = evaluate_mask_quality(mask_binary)
    # quality_thresh = 0.60 if best_box is not None else 0.45
    # if score < quality_thresh:
    #     print(f"[Advanced] Low-quality SAM mask (score={score:.2f}) → fallback")
    #     return None, None, total_time
    from .measurement import evaluate_mask_quality, dark_object_mask

    score = evaluate_mask_quality(mask_binary)
    
    quality_thresh = 0.60 if best_box is not None else 0.45
    
    if score < quality_thresh:
        print(f"[Advanced] Low-quality SAM mask (score={score:.2f}) → trying dark-object rescue")
    
        dark_mask = dark_object_mask(img)
        dark_score = evaluate_mask_quality(dark_mask)
    
        print(f"[Advanced] Dark-mask score = {dark_score:.2f}")
    
        if dark_score > score and dark_score > 0.45:
            print("[Advanced] Using dark-object fallback mask")
            mask_binary = dark_mask
        else:
            return None, None, total_time
    

    # Light morphological cleanup (SAM is already precise, minimal cleanup)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # === Extract Final Contour ===
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        print("[Advanced] No contour found in SAM mask")
        total_time = (time.time() - start_time) * 1000
        return mask_binary, None, total_time

    largest_contour = max(contours, key=cv2.contourArea)

    total_time = (time.time() - start_time) * 1000

    final_area = cv2.contourArea(largest_contour)
    final_ratio = final_area / img_area
    print(f"[Advanced] Final mask: {final_ratio*100:.1f}% of image")
    print(f"[Advanced] Total pipeline: {total_time:.0f}ms (YOLO: {yolo_time:.0f}ms + SAM: {sam_time:.0f}ms)")

    return mask_binary, largest_contour, total_time


def is_available():
    """Check if Advanced Model dependencies are available."""
    try:
        from ultralytics import YOLO, SAM
        return True
    except ImportError:
        return False


def get_mask_and_contour(image_path):
    """Convenience function matching the interface of other inference modules."""
    mask, contour, inference_time = segment_image(image_path)
    return contour, mask, inference_time
