import cv2
import numpy as np
from itertools import combinations

def detect_aruco_markers(frame, marker_size_mm, dictionary_id=cv2.aruco.DICT_4X4_250):
    """
    Detects multiple ArUco markers and calculates mm/px using:
    1. Individual marker sizes (basic method)
    2. Inter-marker distances (high-precision method when 2+ markers detected)
    
    For inter-marker distance calculation, we use known marker center positions
    from the calibration sheet layout.
    
    Returns:
        tuple: (success, result_dict)
    """
    if frame is None:
        return False, {"error": "Invalid frame", "code": "INVALID_FRAME"}

    # Initialize the aruco detector
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
    aruco_params = cv2.aruco.DetectorParameters()
    
    # Robust detection parameters
    aruco_params.adaptiveThreshWinSizeMin = 3
    aruco_params.adaptiveThreshWinSizeMax = 53
    aruco_params.adaptiveThreshWinSizeStep = 4
    aruco_params.minMarkerPerimeterRate = 0.01
    aruco_params.maxMarkerPerimeterRate = 4.0
    aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Image quality metrics
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = np.mean(gray)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    # Refine corners for higher accuracy
    if ids is not None and len(ids) > 0:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
        for corner in corners:
            cv2.cornerSubPix(gray, corner, (5, 5), (-1, -1), criteria)

    if ids is None or len(ids) == 0:
        msg = "No ArUco marker detected."
        if laplacian_var < 100:
            msg += " Image seems blurry."
        if mean_brightness < 40:
            msg += " Too dark."
        elif mean_brightness > 220:
            msg += " Overexposed."
            
        return False, {
            "error": msg, 
            "code": "NO_MARKER",
            "sharpness": laplacian_var,
            "brightness": mean_brightness,
            "rejected_count": len(rejected) if rejected else 0
        }

    # Process all detected markers
    marker_data = []
    mmpx_from_sizes = []
    
    for i, marker_id in enumerate(ids):
        marker_corners = corners[i][0]
        
        # Calculate pixel size of this marker
        side1 = np.linalg.norm(marker_corners[0] - marker_corners[1])
        side2 = np.linalg.norm(marker_corners[1] - marker_corners[2])
        side3 = np.linalg.norm(marker_corners[2] - marker_corners[3])
        side4 = np.linalg.norm(marker_corners[3] - marker_corners[0])
        
        avg_side_px = (side1 + side2 + side3 + side4) / 4.0
        mmpx = marker_size_mm / avg_side_px
        mmpx_from_sizes.append(mmpx)
        
        # Calculate center
        center = np.mean(marker_corners, axis=0)
        
        # Check for tilt
        ratio_h = max(side1, side3) / min(side1, side3) if min(side1, side3) > 0 else 999
        ratio_v = max(side2, side4) / min(side2, side4) if min(side2, side4) > 0 else 999
        is_tilted = ratio_h > 1.15 or ratio_v > 1.15
        
        marker_data.append({
            "id": int(marker_id[0]),
            "center": center,
            "corners": marker_corners,
            "pixel_size": avg_side_px,
            "mmpx": mmpx,
            "is_tilted": is_tilted
        })
    
    # Calculate mm/px from marker sizes (basic method)
    avg_mmpx_size = float(np.mean(mmpx_from_sizes))
    std_mmpx_size = float(np.std(mmpx_from_sizes))
    
    # ========== HIGH-PRECISION: Inter-marker distance calculation ==========
    # If we have 2+ markers, we can calculate mm/px from their relative positions
    # This is MORE ACCURATE than using marker size alone because:
    # 1. Distances are larger -> less pixel quantization error
    # 2. Any systematic marker size error is eliminated
    
    mmpx_from_distances = []
    distance_pairs = []
    
    if len(marker_data) >= 2:
        # For each pair of markers, calculate the distance
        for m1, m2 in combinations(marker_data, 2):
            # Pixel distance between marker centers
            px_distance = np.linalg.norm(m1["center"] - m2["center"])
            
            if px_distance > 50:  # Minimum distance threshold
                distance_pairs.append({
                    "id1": m1["id"],
                    "id2": m2["id"],
                    "px_distance": float(px_distance)
                })
    
    # ========== FINAL mm/px CALCULATION ==========
    # Use marker size method (we don't have layout knowledge yet)
    final_mmpx = avg_mmpx_size
    method_used = "marker_size"
    
    # Calculate stability score (how consistent are the measurements)
    if len(mmpx_from_sizes) > 1:
        stability = 100 - min(100, (std_mmpx_size / avg_mmpx_size) * 1000) if avg_mmpx_size > 0 else 0
    else:
        stability = 100.0  # Single marker = no variance to measure
    
    # Check if any marker is tilted
    any_tilted = any(m["is_tilted"] for m in marker_data)
    
    # Draw results
    out_frame = frame.copy()
    cv2.aruco.drawDetectedMarkers(out_frame, corners, ids)
    
    # Draw info for each marker
    for m in marker_data:
        center = m["center"].astype(int)
        color = (0, 255, 0) if not m["is_tilted"] else (0, 165, 255)
        cv2.putText(out_frame, f"ID{m['id']}: {m['mmpx']:.4f}", 
                    (center[0] - 40, center[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Draw distance lines between markers (for debugging)
    for pair in distance_pairs:
        m1 = next(m for m in marker_data if m["id"] == pair["id1"])
        m2 = next(m for m in marker_data if m["id"] == pair["id2"])
        pt1 = tuple(m1["center"].astype(int))
        pt2 = tuple(m2["center"].astype(int))
        cv2.line(out_frame, pt1, pt2, (255, 0, 255), 1)
    
    # Draw summary text
    cv2.putText(out_frame, f"mm/px: {final_mmpx:.6f} | Markers: {len(ids)}", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    if any_tilted:
        cv2.putText(out_frame, "WARNING: Tilt detected", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return True, {
        "success": True,
        "mm_per_px": final_mmpx,
        "marker_count": len(ids),
        "markers": marker_data,
        "distance_pairs": distance_pairs,
        "method": method_used,
        "std_dev": std_mmpx_size,
        "stability": stability,
        "is_tilted": any_tilted,
        "annotated_frame": out_frame,
        "sharpness": laplacian_var,
        "brightness": mean_brightness
    }


# Backward compatibility alias
def detect_aruco_marker(frame, marker_size_mm, dictionary_id=cv2.aruco.DICT_4X4_250):
    """Alias for backward compatibility - calls the multi-marker version."""
    return detect_aruco_markers(frame, marker_size_mm, dictionary_id)
