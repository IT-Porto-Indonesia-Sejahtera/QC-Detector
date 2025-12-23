import socket
import subprocess
import platform
import os
import re

def get_interfaces():
    """Get all active network interfaces and their IPs on macOS"""
    interfaces = []
    try:
        output = subprocess.check_output(["ifconfig"]).decode()
        # Split by interface start
        parts = re.split(r'^([a-z0-9]+):', output, flags=re.MULTILINE)
        
        current_iface = None
        for i in range(1, len(parts), 2):
            name = parts[i]
            body = parts[i+1]
            
            # Find IP in body
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', body)
            status_match = re.search(r'status:\s+(\w+)', body)
            
            if ip_match:
                ip = ip_match.group(1)
                if not ip.startswith("127."):
                    status = status_match.group(1) if status_match else "unknown"
                    interfaces.append({"name": name, "ip": ip, "status": status})
    except Exception as e:
        print(f"Error getting interfaces: {e}")
    return interfaces

def check_port(host, port):
    """Check if a specific TCP port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def check_ping_simple(host, interface=None):
    """Simple ping to verify Layer 3 connectivity, with optional interface binding"""
    if interface:
        print(f"Testing forced ping to {host} via {interface}...")
        command = ["ping", "-c", "2", "-I", interface, host]
    else:
        print(f"Testing basic ping to {host}...")
        command = ["ping", "-c", "2", host]
    
    try:
        res = subprocess.call(command)
        return res == 0
    except Exception as e:
        print(f"Ping Error: {e}")
        return False

def discovery_scan(subnet_base):
    print(f"\n--- Subnet Discovery Scan ({subnet_base}.x) ---")
    print("Testing if ANY device responds on this wire...")
    # Broadcast ping to populate ARP
    broadcast = f"{subnet_base}.255"
    try:
        # Pinging broadcast with -t 2 (wait 2 seconds)
        subprocess.call(["ping", "-c", "3", "-t", "2", broadcast], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Now check ARP again
        print("Checking ARP table for new entries...")
        output = subprocess.check_output(["arp", "-a"]).decode()
        entries = [line for line in output.splitlines() if subnet_base in line and "at" in line]
        if entries:
            print("[FOUND] The following devices were found on this wire:")
            for e in entries:
                print(f" - {e}")
        else:
            print("[FAILED] No other devices found. Check if the camera is powered on and the cable is secure.")
    except Exception as e:
        print(f"Discovery Error: {e}")

def get_arp_table(host):
    print(f"\n--- ARP Table (arp -a) ---")
    try:
        output = subprocess.check_output(["arp", "-a"]).decode()
        found = False
        for line in output.splitlines():
            if host in line:
                print(f"[FOUND] {line}")
                found = True
        if not found:
            print(f"[MISSING] No ARP entry for {host}. This means the Mac hasn't \"seen\" the camera yet at the hardware level.")
    except Exception as e:
        print(f"Error getting ARP: {e}")

def scan_ports(host):
    """Scan common RTSP, HTTP, and ONVIF ports"""
    # Adding port 80 because Safari works
    ports = [80, 554, 8554, 8000, 8080, 81, 8888, 10554, 443]
    open_ports = []
    print(f"\nScanning common ports on {host}...")
    for port in ports:
        if check_port(host, port):
            print(f" - Port {port}: OPEN")
            open_ports.append(port)
    return open_ports

def get_routing_table():
    print(f"\n--- Routing Table (netstat -rn) ---")
    try:
        output = subprocess.check_output(["netstat", "-rn"]).decode()
        # Look for the 192.168.1 line
        for line in output.splitlines():
            if "192.168.1" in line or "default" in line:
                print(line)
    except Exception as e:
        print(f"Error getting routing table: {e}")

def get_ifconfig_details(iface):
    print(f"\n--- Interface Details for {iface} ---")
    try:
        output = subprocess.check_output(["ifconfig", iface]).decode()
        print(output)
    except Exception as e:
        print(f"Error getting ifconfig for {iface}: {e}")

def main():
    print("=== Advanced Network Diagnostics ===\n")
    
    target_camera = "192.168.1.64"
    ifaces = get_interfaces()
    
    if not ifaces:
        print("No active network interfaces found!")
        return

    print("Detected Interfaces:")
    for iface in ifaces:
        if iface['ip'] == "192.168.1.1":
            print(f" ! {iface['name']} ({iface['ip']}): [WARNING] This IP is usually for routers. This may cause a conflict!")
        else:
            print(f" - {iface['name']} ({iface['ip']})")
        get_ifconfig_details(iface['name'])

    get_routing_table()
    get_arp_table(target_camera)
    discovery_scan("192.168.1")

    # 2. Basic Reachability
    has_reach = check_ping_simple(target_camera)
    if not has_reach:
        print("\n[INFO] Basic ping failed. Trying to FORCE the USB-LAN interface (en5)...")
        has_reach = check_ping_simple(target_camera, interface="en5")

    if has_reach:
        print(f"\n[SUCCESS] Ping to {target_camera} worked!")
    else:
        print(f"\n[CRITICAL] Cannot reach {target_camera}! Please check Ethernet cable.")

    # 3. Interface Conflict Check
    active_ifaces = [i for i in ifaces if i['status'] == 'active' or i['status'] == 'unknown']
    if len(active_ifaces) > 1:
        print(f"\n[WARNING] You have {len(active_ifaces)} active network interfaces.")
        print("Python sometimes gets confused. Try DISABLING WiFi so only Ethernet is active.")

    # 3. Port Scan
    # Adding port 80 because Safari works
    ports_to_check = [80, 554, 8554, 8000, 8080, 81, 8888, 10554]
    open_ports = []
    print(f"\nScanning common ports on {target_camera}...")
    for port in ports_to_check:
        if check_port(target_camera, port):
            open_ports.append(port)
            
    if open_ports:
        print(f"\n[SUCCESS] Use one of these ports in Settings: {open_ports}")
        if 80 in open_ports and 554 not in open_ports:
            print("[INFO] Port 80 is open (Web), but 554 (Video) is closed. Please check 'RTSP' settings in Hikvision Web UI.")
    else:
        print(f"\n[FAILED] No common video ports found on {target_camera}.")

if __name__ == "__main__":
    main()
