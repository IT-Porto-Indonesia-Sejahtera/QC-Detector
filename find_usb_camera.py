import cv2

def test_cameras(max_index=5):
    print("Scanning for connected USB cameras...")
    available_cameras = []
    
    for index in range(max_index):
        # Suppress OpenCV warnings for missing cameras
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)  # macOS specific backend, or remove the second arg for default
        if cap is None or not cap.isOpened():
            # Try default backend if AVFoundation fails
            cap = cv2.VideoCapture(index)
            
        if cap is not None and cap.isOpened():
            # Try to read a frame to confirm it's actually working
            ret, frame = cap.read()
            if ret:
                print(f"✅ Camera found at index {index}")
                available_cameras.append(index)
            else:
                print(f"⚠️ Camera found at index {index}, but couldn't read frame")
            cap.release()
        else:
            print(f"❌ No camera at index {index}")
            
    if not available_cameras:
        print("\nNo cameras found! Make sure your Sony camera is connected, turned on, and set to 'PC Remote'.")
    else:
        print(f"\nAvailable camera indices: {available_cameras}")
        print("Try using these indices in the QC-Detector Settings -> Device Index.")

if __name__ == "__main__":
    test_cameras()
