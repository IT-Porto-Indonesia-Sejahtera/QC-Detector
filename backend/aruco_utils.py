import cv2
import numpy as np

def detect_aruco_marker(frame, marker_size_mm, dictionary_id=cv2.aruco.DICT_4X4_50):
    """
    Detects a single ArUco marker and calculates mm/px.
    
    Returns:
        tuple: (success, result_dict)
    """
    if frame is None:
        return False, {"error": "Invalid frame"}

    # Initialize the aruco detector
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is None or len(ids) == 0:
        return False, {"error": "No ArUco marker detected. Please ensure market is clearly visible."}

    if len(ids) > 1:
        return False, {"error": f"Multiple markers detected ({len(ids)}). Please show only one marker."}

    # Process the single detected marker
    marker_corners = corners[0][0] # Get the 4 corners of the first marker
    
    # Calculate pixel size (average of the four sides for robustness)
    # corners order: top-left, top-right, bottom-right, bottom-left
    side1 = np.linalg.norm(marker_corners[0] - marker_corners[1])
    side2 = np.linalg.norm(marker_corners[1] - marker_corners[2])
    side3 = np.linalg.norm(marker_corners[2] - marker_corners[3])
    side4 = np.linalg.norm(marker_corners[3] - marker_corners[0])
    
    avg_pixel_size = (side1 + side2 + side3 + side4) / 4.0
    
    if avg_pixel_size < 10:
        return False, {"error": "Marker too small in frame. Please move it closer to the camera."}

    mm_per_px = marker_size_mm / avg_pixel_size

    # Draw result for confirmation
    out_frame = frame.copy()
    cv2.aruco.drawDetectedMarkers(out_frame, corners, ids)
    
    # Annotate with mm/px
    center = np.mean(marker_corners, axis=0).astype(int)
    cv2.putText(out_frame, f"{mm_per_px:.6f} mm/px", (center[0] - 50, center[1]), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    return True, {
        "mm_per_px": mm_per_px,
        "pixel_size": avg_pixel_size,
        "marker_id": int(ids[0][0]),
        "annotated_frame": out_frame
    }
