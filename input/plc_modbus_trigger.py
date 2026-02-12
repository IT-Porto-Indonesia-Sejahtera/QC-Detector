"""
PLC Modbus Trigger Module

Reads from PLC via Modbus TCP/RTU.
Triggers capture when a specific register value changes from 0 to 1.

Requires: pymodbus library
"""

import threading
import time
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass

try:
    from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False


@dataclass
class ModbusConfig:
    """Configuration for Modbus PLC trigger"""
    # Connection type: "tcp" or "rtu"
    connection_type: str = "rtu"
    
    # TCP settings
    host: str = "192.168.1.1"
    port: int = 502
    
    # RTU (Serial) settings
    serial_port: str = ""  # Let it be empty for manual entry or discovery
    baudrate: int = 9600
    parity: str = "E"  # N, E, O
    stopbits: int = 1
    bytesize: int = 8
    
    # Modbus settings
    slave_id: int = 1  # Unit ID / Slave address
    register_address: int = 12  # Address of register to monitor
    register_type: str = "holding"  # "coil", "discrete_input", "holding", "input"
    
    # Trigger settings
    poll_interval_ms: int = 10  # Polling interval in milliseconds
    enabled: bool = True


class PLCModbusTrigger:
    """
    Reads PLC register via Modbus.
    Triggers callback when value changes from 0 to 1 (rising edge).
    """
    
    def __init__(self, config: Optional[ModbusConfig] = None):
        if not PYMODBUS_AVAILABLE:
            raise ImportError(
                "pymodbus library not found. Install with: pip install pymodbus"
            )
        
        self.config = config or ModbusConfig()
        print(f"[DEBUG] Initializing PLCModbusTrigger from {__file__}")
        self.client: Optional[ModbusTcpClient | ModbusSerialClient] = None
        self.read_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_value: Optional[int] = None
        
        # Suppress pymodbus internal logging (which can be very noisy)
        # It's better to manage our own logging and only show what's relevant to the UI
        pymodbus_logger = logging.getLogger("pymodbus")
        pymodbus_logger.setLevel(logging.CRITICAL)
        
        # Connectivity state tracking
        self._last_error_time = 0
        self._error_cooldown = 10.0 # Don't log same error more than once every 10 seconds
        
        # Callback when trigger condition met (rising edge 0->1)
        self.on_trigger: Optional[Callable[[], None]] = None
        # Callback for value updates (for UI display)
        self.on_value_update: Optional[Callable[[int], None]] = None
        # Callback for connection status changes
        self.on_connection_change: Optional[Callable[[bool, str], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to the PLC via Modbus.
        
        Returns:
            True if connected successfully
        """
        if self.client:
            self.disconnect()
        
        try:
            if self.config.connection_type.lower() == "tcp":
                if not self.config.host:
                    self._notify_connection(False, "TCP Host is empty")
                    return False
                self.client = ModbusTcpClient(
                    host=self.config.host,
                    port=self.config.port
                )
                connection_str = f"{self.config.host}:{self.config.port}"
            else:  # RTU
                if not self.config.serial_port:
                    self._notify_connection(False, "Serial Port is empty")
                    return False
                self.client = ModbusSerialClient(
                    port=self.config.serial_port,
                    baudrate=self.config.baudrate,
                    parity=self.config.parity,
                    stopbits=self.config.stopbits,
                    bytesize=self.config.bytesize
                )
                connection_str = f"{self.config.serial_port}"
            
            if self.client.connect():
                self._notify_connection(True, f"Connected to {connection_str}")
                return True
            else:
                # Throttle connection failure logging
                current_time = time.time()
                if current_time - self._last_error_time > self._error_cooldown:
                    print(f"[PLC] Failed to connect to {connection_str}")
                    self._last_error_time = current_time
                    
                self._notify_connection(False, f"Failed to connect to {connection_str}")
                return False
                
        except Exception as e:
            # Throttle connection error logging to avoid spamming the console/Lark
            current_time = time.time()
            if current_time - self._last_error_time > self._error_cooldown:
                print(f"[PLC] Connection error: {str(e)}")
                self._last_error_time = current_time
            
            self._notify_connection(False, f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from PLC"""
        self.stop()
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None
        self.last_value = None
        self._notify_connection(False, "Disconnected")
    
    def start(self) -> bool:
        """Start polling PLC register in background thread"""
        if not self.client:
            if not self.connect():
                return False
        
        if self.running:
            return True
        
        self.running = True
        self.read_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.read_thread.start()
        return True
    
    def stop(self):
        """Stop polling"""
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        self.read_thread = None
    
    def _poll_loop(self):
        """Main loop polling the PLC register"""
        while self.running and self.client:
            try:
                value = self._read_register()
                
                if value is not None:
                    # Notify value update (silent - no print for trigger register)
                    if self.on_value_update:
                        self.on_value_update(value)
                    
                    # Check for rising edge (0 -> 1)
                    if self.config.enabled:
                        if self.last_value == 0 and value == 1:
                            self._fire_trigger()
                    
                    self.last_value = value
                    
            except Exception as e:
                print(f"Modbus read error: {e}")
                self._notify_connection(False, f"Read error: {str(e)}")
                break
            
            time.sleep(self.config.poll_interval_ms / 1000.0)
    
    def _read_register(self) -> Optional[int]:
        """Read the configured register from PLC"""
        if not self.client:
            return None
        
        try:
            reg_type = self.config.register_type.lower()
            address = self.config.register_address
            slave = self.config.slave_id
            
            if reg_type == "coil":
                result = self.client.read_coils(address, count=1, device_id=slave)
            elif reg_type == "discrete_input":
                result = self.client.read_discrete_inputs(address, count=1, device_id=slave)
            elif reg_type == "holding":
                result = self.client.read_holding_registers(address, count=1, device_id=slave)
            elif reg_type == "input":
                result = self.client.read_input_registers(address, count=1, device_id=slave)
            else:
                print(f"Unknown register type: {reg_type}")
                return None
            
            if result.isError():
                print(f"Modbus error: {result}")
                return None
            
            # Get value based on register type
            if reg_type in ("coil", "discrete_input"):
                return 1 if result.bits[0] else 0
            else:
                return result.registers[0]
                
        except Exception as e:
            print(f"Register read error: {e}")
            return None
    
    def _fire_trigger(self):
        """Fire the trigger callback immediately (no cooldown)"""
        print("[PLC] Rising edge detected (0 -> 1) - Triggering!")
        if self.on_trigger:
            self.on_trigger()
    
    def _notify_connection(self, connected: bool, message: str):
        """Notify connection status change"""
        if self.on_connection_change:
            self.on_connection_change(connected, message)
    
    def get_current_value(self) -> Optional[int]:
        """Get the last read value"""
        return self.last_value
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.client is not None and self.client.is_socket_open() if hasattr(self.client, 'is_socket_open') else self.client is not None
    
    def write_register(self, address: int, value: int) -> bool:
        """
        Write a value to a holding register on the PLC.
        
        Args:
            address: Register address to write to
            value: Value to write (0-65535 for holding registers)
            
        Returns:
            True if write was successful
        """
        if not self.client:
            print(f"[PLC] Cannot write - not connected")
            return False
        
        try:
            slave = self.config.slave_id
            result = self.client.write_register(address, value, device_id=slave)
            
            if result.isError():
                print(f"[PLC] Write error to register {address}: {result}")
                return False
            
            print(f"[PLC] Written value {value} to register {address}")
            return True
            
        except Exception as e:
            print(f"[PLC] Write exception: {e}")
            return False
    
    def read_any_register(self, address: int) -> Optional[int]:
        """
        Read any holding register from the PLC.
        
        Args:
            address: Register address to read
            
        Returns:
            The register value, or None if read failed
        """
        if not self.client:
            print(f"[PLC] Cannot read - not connected")
            return None
        
        try:
            slave = self.config.slave_id
            result = self.client.read_holding_registers(address, count=1, device_id=slave)
            
            if result.isError():
                print(f"[PLC] Read error from register {address}: {result}")
                return None
            
            value = result.registers[0]
            print(f"[PLC] Read register {address} = {value}")
            return value
            
        except Exception as e:
            print(f"[PLC] Read exception: {e}")
            return None


# Singleton instance
_plc_instance: Optional[PLCModbusTrigger] = None


def get_plc_trigger() -> PLCModbusTrigger:
    """Get the global PLC trigger instance"""
    global _plc_instance
    if _plc_instance is None:
        _plc_instance = PLCModbusTrigger()
    return _plc_instance


def check_pymodbus_available() -> bool:
    """Check if pymodbus library is available"""
    return PYMODBUS_AVAILABLE
