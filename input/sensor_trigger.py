"""
Sensor Trigger Module

Reads from ESP32 ultrasonic sensor via Serial (COM port).
Triggers capture when object is detected within threshold distance.

Expected ESP32 Serial Output Format:
- Distance in cm as plain number (e.g., "25.5")
- Or "TRIGGER" text for direct trigger signal
"""

import serial
import serial.tools.list_ports
import threading
import time
from typing import Optional, Callable, List
from dataclasses import dataclass


@dataclass
class SensorConfig:
    """Configuration for sensor trigger"""
    port: str = "COM6"  # COM port (e.g., "COM3")
    baud_rate: int = 115200  # ESP32 default
    trigger_threshold_cm: float = 30.0  # Trigger when distance < this
    cooldown_seconds: float = 2.0  # Minimum time between triggers
    enabled: bool = True


class SensorTrigger:
    """
    Reads ultrasonic sensor data from ESP32 via Serial.
    Triggers callback when object detected within threshold.
    """
    
    def __init__(self, config: Optional[SensorConfig] = None):
        self.config = config or SensorConfig()
        self.serial_conn: Optional[serial.Serial] = None
        self.read_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_trigger_time = 0
        self.last_distance = -1
        
        # Callback when trigger condition met
        self.on_trigger: Optional[Callable[[], None]] = None
        # Callback for distance updates (for UI display)
        self.on_distance_update: Optional[Callable[[float], None]] = None
        # Callback for connection status changes
        self.on_connection_change: Optional[Callable[[bool, str], None]] = None
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """List available COM ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    @staticmethod
    def find_esp32_port() -> Optional[str]:
        """Try to auto-detect ESP32 port by common identifiers"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = port.description.lower()
            # Common ESP32 USB-Serial chip identifiers
            if any(x in desc for x in ['cp210', 'ch340', 'ftdi', 'usb serial', 'esp32']):
                return port.device
        return None
    
    def connect(self, port: Optional[str] = None) -> bool:
        """
        Connect to the sensor.
        
        Args:
            port: COM port. If None, tries auto-detection.
            
        Returns:
            True if connected successfully
        """
        if self.serial_conn and self.serial_conn.is_open:
            self.disconnect()
        
        target_port = port or self.config.port or self.find_esp32_port()
        
        if not target_port:
            self._notify_connection(False, "No COM port found")
            return False
        
        try:
            self.serial_conn = serial.Serial(
                port=target_port,
                baudrate=self.config.baud_rate,
                timeout=1
            )
            self.config.port = target_port
            self._notify_connection(True, f"Connected to {target_port}")
            return True
        except serial.SerialException as e:
            self._notify_connection(False, f"Failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from sensor"""
        self.stop()
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None
        self._notify_connection(False, "Disconnected")
    
    def start(self):
        """Start reading sensor data in background thread"""
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return False
        
        if self.running:
            return True
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        return True
    
    def stop(self):
        """Stop reading sensor data"""
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        self.read_thread = None
    
    def _read_loop(self):
        """Main loop reading sensor data"""
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._process_data(line)
            except serial.SerialException:
                self._notify_connection(False, "Connection lost")
                break
            except Exception as e:
                print(f"Sensor read error: {e}")
            
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    
    def _process_data(self, data: str):
        """Process incoming sensor data"""
        data = data.strip().upper()
        
        # Check for direct trigger command
        if data == "TRIGGER":
            self._check_trigger()
            return
        
        # Try to parse as distance value
        try:
            distance = float(data.replace(",", "."))
            self.last_distance = distance
            
            # Notify distance update
            if self.on_distance_update:
                self.on_distance_update(distance)
            
            # Check if should trigger
            if self.config.enabled and distance > 0 and distance < self.config.trigger_threshold_cm:
                self._check_trigger()
                
        except ValueError:
            # Not a number, ignore
            pass
    
    def _check_trigger(self):
        """Check cooldown and trigger if allowed"""
        current_time = time.time()
        
        if current_time - self.last_trigger_time >= self.config.cooldown_seconds:
            self.last_trigger_time = current_time
            if self.on_trigger:
                self.on_trigger()
    
    def _notify_connection(self, connected: bool, message: str):
        """Notify connection status change"""
        if self.on_connection_change:
            self.on_connection_change(connected, message)


# Singleton instance
_sensor_instance: Optional[SensorTrigger] = None


def get_sensor() -> SensorTrigger:
    """Get the global sensor instance"""
    global _sensor_instance
    if _sensor_instance is None:
        _sensor_instance = SensorTrigger()
    return _sensor_instance
