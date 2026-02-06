import os
import cv2
import platform

def open_video_capture(source, buffer_size=1, timeout_ms=3000, force_width=0, force_height=0):
    """
    Unified function to open a cv2.VideoCapture with proper settings for RTSP, HTTP, and USB cameras.
    
    Args:
        source: Camera index (int), RTSP/HTTP URL (str), or a preset dict.
        buffer_size: Buffer size for the capture. Default is 1 for low latency.
        timeout_ms: Timeout in milliseconds for opening and reading.
        force_width: Forced width (0 for auto).
        force_height: Forced height (0 for auto).
        
    Returns:
        cv2.VideoCapture: The opened capture object.
    """
    final_source = source
    protocol = "usb"
    transport = "tcp" # Default for IP cameras

    # 1. Handle Preset Dictionary
    if isinstance(source, dict):
        protocol = source.get("protocol", "rtsp").lower()
        address = source.get("address", "")
        port = source.get("port", "")
        path = source.get("path", "")
        user = source.get("username", "")
        password = source.get("password", "")
        transport = source.get("transport", "tcp")

        if protocol == "usb":
            try:
                final_source = int(address) if address.isdigit() else 0
            except:
                final_source = 0
        else:
            # Build URL: protocol://[user:pass@]address[:port][path]
            auth = f"{user}:{password}@" if user and password else ""
            port_str = f":{port}" if port else ""
            # Ensure path starts with / if it exists
            if path and not path.startswith("/"):
                path = "/" + path
            
            final_source = f"{protocol}://{auth}{address}{port_str}{path}"

    # 2. Determine protocol if source is a string
    elif isinstance(source, str):
        if source.startswith("rtsp://"):
            protocol = "rtsp"
        elif source.startswith("http://") or source.startswith("https://"):
            protocol = "http"
        elif source.isdigit():
            final_source = int(source)
            protocol = "usb"

    # 3. Configure environment variables for FFMPEG
    if protocol == "rtsp":
        # Force transport protocol. 
        # Semicolon is the standard separator for key;value in OpenCV 4.x
        # We'll stick to just the transport for now as multiple options seem to fail parsing on this system.
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
        print(f"[DEBUG] CameraUtils: Opening RTSP with transport={transport}")
    else:
        # Clear options for non-RTSP sources
        if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ:
            del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]

    # 4. Instantiate VideoCapture
    print(f"[DEBUG] CameraUtils: Final source: {final_source}")
    
    if isinstance(final_source, int):
        if platform.system() == "Windows":
            cap = cv2.VideoCapture(final_source, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(final_source)
        else:
            cap = cv2.VideoCapture(final_source)
    else:
        # For RTSP/HTTP, let OpenCV choose the best backend (default is usually FFMPEG)
        # Explicitly passing CAP_FFMPEG with a string source can sometimes fail.
        cap = cv2.VideoCapture(final_source)

    # 5. Apply properties
    if cap.isOpened():
        # Set Resolution if requested (Must be before buffer size for some backends)
        if force_width > 0 and force_height > 0:
            print(f"[DEBUG] CameraUtils: Forcing resolution to {force_width}x{force_height}")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, force_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, force_height)
            
        cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
        # These might still be useful for some backends
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)
        print(f"[DEBUG] CameraUtils: Successfully opened camera")
    else:
        print(f"[DEBUG] CameraUtils: Failed to open camera")
        
    return cap
