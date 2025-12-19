"""
IP Camera Discovery Utility

Uses WS-Discovery to find ONVIF-compliant IP cameras on the local network.
Falls back to scanning common RTSP ports if no ONVIF devices found.
"""

import socket
import struct
import threading
import re
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import cv2


@dataclass
class DiscoveredCamera:
    """Represents a discovered IP camera"""
    ip: str
    port: int = 554
    name: str = ""
    manufacturer: str = ""
    requires_auth: bool = True  # Assume auth required by default
    rtsp_path: str = "/stream1"  # Common default path
    
    def get_rtsp_url(self, username: str = "", password: str = "") -> str:
        """Build RTSP URL with optional credentials"""
        if username and password:
            return f"rtsp://{username}:{password}@{self.ip}:{self.port}{self.rtsp_path}"
        return f"rtsp://{self.ip}:{self.port}{self.rtsp_path}"
    
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.ip})"
        if self.manufacturer:
            return f"{self.manufacturer} ({self.ip})"
        return f"IP Camera ({self.ip})"


class IPCameraDiscovery:
    """Discovers IP cameras on the local network"""
    
    # WS-Discovery probe message for ONVIF devices
    WS_DISCOVERY_PROBE = '''<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
    xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
    xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
    xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
    <e:Header>
        <w:MessageID>uuid:84ede3de-7dec-11d0-c360-F01234567890</w:MessageID>
        <w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
        <w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
    </e:Header>
    <e:Body>
        <d:Probe>
            <d:Types>dn:NetworkVideoTransmitter</d:Types>
        </d:Probe>
    </e:Body>
</e:Envelope>'''
    
    MULTICAST_GROUP = "239.255.255.250"
    MULTICAST_PORT = 3702
    
    # Common RTSP ports to scan
    COMMON_RTSP_PORTS = [554, 8554, 8080]
    
    # Common RTSP paths for different manufacturers
    COMMON_RTSP_PATHS = [
        "/stream1",
        "/h264/ch1/main/av_stream",
        "/cam/realmonitor",
        "/live/ch00_0",
        "/Streaming/Channels/101",
        "/video1",
    ]
    
    def __init__(self):
        self._discovery_thread: Optional[threading.Thread] = None
        self._stop_discovery = threading.Event()
        self._discovered_cameras: List[DiscoveredCamera] = []
        self._lock = threading.Lock()
    
    def discover_cameras(
        self, 
        timeout: float = 5.0,
        callback: Optional[Callable[[List[DiscoveredCamera]], None]] = None
    ) -> List[DiscoveredCamera]:
        """
        Discover IP cameras on the network.
        
        Args:
            timeout: How long to wait for responses (seconds)
            callback: Optional callback function called when discovery completes
            
        Returns:
            List of discovered cameras
        """
        self._discovered_cameras = []
        self._stop_discovery.clear()
        
        # Try WS-Discovery first (ONVIF)
        self._ws_discovery(timeout)
        
        # Also try port scanning on local subnet if few cameras found
        if len(self._discovered_cameras) < 2:
            self._port_scan_discovery(timeout / 2)
        
        if callback:
            callback(self._discovered_cameras)
            
        return self._discovered_cameras
    
    def discover_cameras_async(
        self,
        timeout: float = 5.0,
        callback: Optional[Callable[[List[DiscoveredCamera]], None]] = None
    ):
        """Start camera discovery in a background thread"""
        self._stop_discovery.clear()
        self._discovery_thread = threading.Thread(
            target=self.discover_cameras,
            args=(timeout, callback),
            daemon=True
        )
        self._discovery_thread.start()
    
    def stop_discovery(self):
        """Stop ongoing discovery"""
        self._stop_discovery.set()
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=1.0)
    
    def _ws_discovery(self, timeout: float):
        """Perform WS-Discovery to find ONVIF cameras"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.settimeout(timeout)
            
            # Send probe
            sock.sendto(
                self.WS_DISCOVERY_PROBE.encode('utf-8'),
                (self.MULTICAST_GROUP, self.MULTICAST_PORT)
            )
            
            # Collect responses
            start_time = socket.getdefaulttimeout()
            while not self._stop_discovery.is_set():
                try:
                    data, addr = sock.recvfrom(65535)
                    self._parse_ws_discovery_response(data.decode('utf-8'), addr[0])
                except socket.timeout:
                    break
                except Exception:
                    continue
                    
            sock.close()
        except Exception as e:
            print(f"WS-Discovery error: {e}")
    
    def _parse_ws_discovery_response(self, response: str, ip: str):
        """Parse WS-Discovery response and extract camera info"""
        # Check if this IP already discovered
        with self._lock:
            if any(c.ip == ip for c in self._discovered_cameras):
                return
        
        camera = DiscoveredCamera(ip=ip)
        
        # Try to extract manufacturer/model from response
        # Look for common patterns in ONVIF responses
        if "hikvision" in response.lower():
            camera.manufacturer = "Hikvision"
            camera.rtsp_path = "/Streaming/Channels/101"
        elif "dahua" in response.lower():
            camera.manufacturer = "Dahua"
            camera.rtsp_path = "/cam/realmonitor"
        elif "axis" in response.lower():
            camera.manufacturer = "Axis"
            camera.rtsp_path = "/axis-media/media.amp"
        elif "onvif" in response.lower():
            camera.manufacturer = "ONVIF Camera"
        
        # Extract XAddrs for port info
        xaddrs_match = re.search(r'XAddrs[^>]*>([^<]+)', response)
        if xaddrs_match:
            xaddrs = xaddrs_match.group(1)
            port_match = re.search(r':(\d+)/', xaddrs)
            if port_match:
                camera.port = int(port_match.group(1))
        
        with self._lock:
            self._discovered_cameras.append(camera)
    
    def _port_scan_discovery(self, timeout: float):
        """Scan local subnet for common RTSP ports"""
        try:
            # Get local IP
            local_ip = self._get_local_ip()
            if not local_ip:
                return
            
            # Scan subnet (last octet)
            base_ip = ".".join(local_ip.split(".")[:-1])
            per_host_timeout = timeout / 20  # Limit time per host
            
            for i in range(1, 255):
                if self._stop_discovery.is_set():
                    break
                    
                target_ip = f"{base_ip}.{i}"
                if target_ip == local_ip:
                    continue
                
                # Quick check on common RTSP port
                for port in self.COMMON_RTSP_PORTS[:1]:  # Just check 554 for speed
                    if self._check_port_open(target_ip, port, per_host_timeout):
                        with self._lock:
                            if not any(c.ip == target_ip for c in self._discovered_cameras):
                                self._discovered_cameras.append(
                                    DiscoveredCamera(ip=target_ip, port=port)
                                )
                        break
        except Exception as e:
            print(f"Port scan error: {e}")
    
    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    def _check_port_open(self, ip: str, port: int, timeout: float) -> bool:
        """Check if a port is open on the given IP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    def test_camera_connection(
        ip: str,
        port: int = 554,
        rtsp_path: str = "/stream1",
        username: str = "",
        password: str = "",
        timeout: float = 5.0
    ) -> Tuple[bool, str]:
        """
        Test if we can connect to a camera.
        
        Returns:
            Tuple of (success, message)
        """
        if username and password:
            url = f"rtsp://{username}:{password}@{ip}:{port}{rtsp_path}"
        else:
            url = f"rtsp://{ip}:{port}{rtsp_path}"
        
        try:
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    return True, "Connected successfully"
                return False, "Connected but no frames received"
            else:
                return False, "Failed to open stream (check credentials)"
        except Exception as e:
            return False, f"Error: {str(e)}"


# Singleton instance for easy access
_discovery_instance: Optional[IPCameraDiscovery] = None

def get_discovery() -> IPCameraDiscovery:
    """Get the singleton discovery instance"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = IPCameraDiscovery()
    return _discovery_instance
