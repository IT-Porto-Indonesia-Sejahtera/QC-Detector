import sys
import os
import time

# Add the project root to the path so we can import app.utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.utils.ip_camera_discovery import get_discovery
except ImportError:
    print("Error: Could not import camera discovery utility.")
    print("Please make sure you are running this script from the project root.")
    sys.exit(1)

def main():
    print("--- IP Camera Discovery Tool ---")
    print("Scanning local network for ONVIF and RTSP cameras...")
    
    discovery = get_discovery()
    
    # Simple callback to print progress
    def on_found(cameras):
        print(f"\nScan complete. Found {len(cameras)} camera(s):")
        for i, cam in enumerate(cameras, 1):
            print(f"{i}. {cam}")
            print(f"   IP: {cam.ip}")
            print(f"   Port: {cam.port}")
            print(f"   Manufacturer: {cam.manufacturer}")
            print(f"   Suggested Path: {cam.rtsp_path}")
            print("-" * 30)

    # Start discovery
    discovery.discover_cameras(timeout=10.0, callback=on_found)

if __name__ == "__main__":
    main()
