import cv2
import numpy as np

def detect_aruco_marker(frame, marker_size_mm, dictionary_id=cv2.aruco.DICT_4X4_50):
    """
    Detects a single ArUco marker and calculates mm/px.
    Includes pose estimation to detect tilt and improve accuracy.
    
    Returns:
        tuple: (success, result_dict)
    """
    if frame is None:
        return False, {"error": "Invalid frame", "code": "INVALID_FRAME"}

    # Initialize the aruco detector
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
    aruco_params = cv2.aruco.DetectorParameters()
    
    # Improve detection robustness
    aruco_params.adaptiveThreshWinSizeMin = 3
    aruco_params.adaptiveThreshWinSizeMax = 23
    aruco_params.adaptiveThreshWinSizeStep = 10
    
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Debug info: Sharpness and Brightness
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = np.mean(gray)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None and len(ids) > 0:
        # Refine corners for higher accuracy
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
        for corner in corners:
            cv2.cornerSubPix(gray, corner, (5, 5), (-1, -1), criteria)

    if ids is None or len(ids) == 0:
        msg = "No ArUco marker detected."
        if laplacian_var < 100:
            msg += " Image seems blurry. Try to focus the camera."
        if mean_brightness < 40:
            msg += " Image is too dark. Improve lighting."
        elif mean_brightness > 220:
            msg += " Image is too bright (overexposed)."
            
        return False, {
            "error": msg, 
            "code": "NO_MARKER",
            "sharpness": laplacian_var,
            "brightness": mean_brightness
        }

    if len(ids) > 1:
        return False, {"error": f"Multiple markers detected ({len(ids)}). Please show only one marker.", "code": "MULTIPLE_MARKERS"}

    # Process the single detected marker
    marker_corners = corners[0][0] # Get the 4 corners of the first marker
    
    # Calculate pixel size (average of the four sides for robustness)
    # corners order: top-left, top-right, bottom-right, bottom-left
    side1 = np.linalg.norm(marker_corners[0] - marker_corners[1])
    side2 = np.linalg.norm(marker_corners[1] - marker_corners[2])
    side3 = np.linalg.norm(marker_corners[2] - marker_corners[3])
    side4 = np.linalg.norm(marker_corners[3] - marker_corners[0])
    
    avg_pixel_size = (side1 + side2 + side3 + side4) / 4.0
    
    # Check for perspective distortion (tilt)
    # If the marker is perfectly facing the camera, side1/side3 and side2/side4 should be close to 1
    # Also side1 should be close to side2
    ratio_h = max(side1, side3) / min(side1, side3) if min(side1, side3) > 0 else 999
    ratio_v = max(side2, side4) / min(side2, side4) if min(side2, side4) > 0 else 999
    ratio_aspect = max(side1, side2) / min(side1, side2) if min(side1, side2) > 0 else 999
    
    is_tilted = ratio_h > 1.1 or ratio_v > 1.1 or ratio_aspect > 1.1
    
    if avg_pixel_size < 20: # Increased minimum size for better accuracy
        return False, {"error": "Marker too small in frame. Please move it closer to the camera.", "code": "TOO_SMALL"}

    mm_per_px = marker_size_mm / avg_pixel_size

    # Draw result for confirmation
    out_frame = frame.copy()
    cv2.aruco.drawDetectedMarkers(out_frame, corners, ids)
    
    # Annotate with mm/px
    center = np.mean(marker_corners, axis=0).astype(int)
    color = (0, 255, 0) if not is_tilted else (0, 165, 255) # Green if good, Orange if tilted
    
    cv2.putText(out_frame, f"{mm_per_px:.6f} mm/px", (center[0] - 80, center[1]), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    if is_tilted:
        cv2.putText(out_frame, "TILT DETECTED - KEEP FLAT", (center[0] - 100, center[1] + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return True, {
        "success": True,
        "mm_per_px": mm_per_px,
        "pixel_size": avg_pixel_size,
        "marker_id": int(ids[0][0]),
        "annotated_frame": out_frame,
        "is_tilted": is_tilted,
        "tilt_info": {"ratio_h": ratio_h, "ratio_v": ratio_v, "ratio_aspect": ratio_aspect},
        "sharpness": laplacian_var,
        "brightness": mean_brightness
    }
