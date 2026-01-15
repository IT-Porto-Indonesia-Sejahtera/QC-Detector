"""
Quick diagnostic script to test IP camera connectivity on Windows.
"""
import socket
import subprocess
import cv2
import os

def test_ping(host):
    """Test if we can ping the camera"""
    print(f"\n[1] Testing ping to {host}...")
    try:
        # Windows ping command
        result = subprocess.run(
            ["ping", "-n", "2", "-w", "1000", host],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"    ✓ Ping successful!")
            return True
        else:
            print(f"    ✗ Ping failed - camera may be off or unreachable")
            print(f"      {result.stdout}")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def test_port(host, port):
    """Test if a specific TCP port is open"""
    print(f"\n[2] Testing TCP port {port} on {host}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"    ✓ Port {port} is OPEN")
            return True
        else:
            print(f"    ✗ Port {port} is CLOSED or filtered")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def scan_common_ports(host):
    """Scan common camera ports"""
    print(f"\n[3] Scanning common camera ports on {host}...")
    ports = [80, 554, 8554, 8000, 8080, 443, 8888, 10554]
    open_ports = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"    ✓ Port {port}: OPEN")
                open_ports.append(port)
            else:
                print(f"    - Port {port}: closed")
        except:
            print(f"    - Port {port}: error")
    return open_ports

def test_rtsp_connection(host, port, username, password, path=""):
    """Test RTSP connection with OpenCV"""
    print(f"\n[4] Testing RTSP connection...")
    
    # Build URL
    if username and password:
        url = f"rtsp://{username}:{password}@{host}:{port}{path}"
        masked_url = f"rtsp://{username}:****@{host}:{port}{path}"
    else:
        url = f"rtsp://{host}:{port}{path}"
        masked_url = url
    
    print(f"    URL: {masked_url}")
    
    # Test with TCP transport
    print(f"\n    Testing with TCP transport...")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"    ✓ SUCCESS! Got frame: {frame.shape}")
            cap.release()
            return True
        else:
            print(f"    ✗ Opened but couldn't read frame")
    else:
        print(f"    ✗ Failed to open with TCP")
    cap.release()
    
    # Test with UDP transport
    print(f"\n    Testing with UDP transport...")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"    ✓ SUCCESS! Got frame: {frame.shape}")
            cap.release()
            return True
        else:
            print(f"    ✗ Opened but couldn't read frame")
    else:
        print(f"    ✗ Failed to open with UDP")
    cap.release()
    
    return False

def check_firewall():
    """Check Windows Firewall status"""
    print(f"\n[5] Checking Windows Firewall...")
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if "ON" in result.stdout:
            print("    ⚠ Firewall is ON - may need to allow Python through firewall")
    except Exception as e:
        print(f"    Could not check firewall: {e}")

def get_network_adapters():
    """List network adapters"""
    print(f"\n[6] Network Adapters...")
    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True
        )
        # Just show adapters with IPs
        lines = result.stdout.split('\n')
        current_adapter = ""
        for line in lines:
            if "adapter" in line.lower():
                current_adapter = line.strip()
            if "IPv4" in line:
                print(f"    {current_adapter}")
                print(f"      {line.strip()}")
    except Exception as e:
        print(f"    Error: {e}")

def main():
    print("=" * 60)
    print("IP Camera Connection Diagnostic Tool (Windows)")
    print("=" * 60)
    
    # Camera settings from app_settings.json
    host = "192.168.1.64"
    port = 554
    username = "admin"
    password = "Porto.cctv"
    path = ""  # Empty in your settings
    
    print(f"\nTesting camera: {host}:{port}")
    print(f"Username: {username}")
    
    # Run tests
    get_network_adapters()
    ping_ok = test_ping(host)
    
    if not ping_ok:
        print("\n" + "=" * 60)
        print("⚠ PING FAILED - Troubleshooting steps:")
        print("=" * 60)
        print("1. Check if camera is powered on")
        print("2. Check network cable connections")
        print("3. Verify your PC is on the same subnet (192.168.1.x)")
        print("4. Try accessing camera via web browser: http://192.168.1.64")
        print("5. Temporarily disable Windows Firewall to test")
    
    port_ok = test_port(host, port)
    open_ports = scan_common_ports(host)
    
    if not port_ok:
        print("\n" + "=" * 60)
        print("⚠ RTSP PORT 554 CLOSED - Troubleshooting:")
        print("=" * 60)
        print("1. Check camera's RTSP settings in web interface")
        print("2. Some cameras use port 8554 instead of 554")
        if open_ports:
            print(f"3. Try these open ports instead: {open_ports}")
    
    check_firewall()
    
    # Try different paths
    print("\n" + "=" * 60)
    print("Testing RTSP connections with different paths...")
    print("=" * 60)
    
    paths_to_try = [
        "",  # No path
        "/Streaming/Channels/101",  # Hikvision
        "/Streaming/Channels/1",
        "/cam/realmonitor",  # Dahua
        "/stream1",
        "/live/ch00_0",
        "/h264/ch1/main/av_stream",
    ]
    
    for path in paths_to_try:
        print(f"\n--- Trying path: '{path}' ---")
        if test_rtsp_connection(host, port, username, password, path):
            print(f"\n✓✓✓ SUCCESS with path: '{path}'")
            print(f"Update your settings to use this path!")
            break
    else:
        print("\n" + "=" * 60)
        print("✗ Could not connect with any common path")
        print("=" * 60)
        print("\nPossible solutions:")
        print("1. Check if RTSP is enabled in camera settings")
        print("2. Verify username/password are correct")
        print("3. Try VLC Media Player: vlc rtsp://admin:Porto.cctv@192.168.1.64:554/")
        print("4. Check if antivirus is blocking connections")
        print("5. Make sure you're on the same network as the camera")

if __name__ == "__main__":
    main()
