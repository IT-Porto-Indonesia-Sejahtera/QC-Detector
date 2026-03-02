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
    try:
        # Pymodbus v3.x style
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    except ImportError:
        # Pymodbus v2.x style
        from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
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
    baudrate: int = 115200
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
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5
        
        while self.running:
            # If client was lost, try to reconnect
            if not self.client:
                print(f"[{time.strftime('%H:%M:%S')}] [PLC] No client - attempting reconnect...")
                if not self.connect():
                    time.sleep(2.0)  # Wait before retry
                    continue

            try:
                value = self._read_register()
                
                if value is not None:
                    consecutive_errors = 0  # Reset error counter on success
                    # Only log if value is 1 (trigger) or if it changes back to 0
                    if value == 1 or (value == 0 and self.last_value == 1):
                        print(f"[{time.strftime('%H:%M:%S')}] [PLC] Reg {self.config.register_address} value: {value} (was: {self.last_value})")
                    # Notify value update
                    if self.on_value_update:
                        self.on_value_update(value)
                    
                    # Check for rising edge (0 -> 1)
                    if self.config.enabled:
                        if self.last_value == 0 and value == 1:
                            self._fire_trigger()
                    
                    self.last_value = value
                else:
                    # Read returned None — count as a soft error
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"[{time.strftime('%H:%M:%S')}] [PLC] {consecutive_errors} consecutive failed reads on Reg {self.config.register_address} (addr {self.config.register_address}, slave {self.config.slave_id}) - disconnecting for reconnect")
                        self._notify_connection(False, f"Too many read failures on reg {self.config.register_address}")
                        try:
                            self.client.close()
                        except Exception:
                            pass
                        self.client = None
                        consecutive_errors = 0
                        time.sleep(2.0)
                        continue
                        
            except Exception as e:
                consecutive_errors += 1
                print(f"[{time.strftime('%H:%M:%S')}] [PLC] Poll exception (#{consecutive_errors}): {type(e).__name__}: {e}")
                self._notify_connection(False, f"Read error: {str(e)}")
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"[{time.strftime('%H:%M:%S')}] [PLC] Too many exceptions - resetting connection")
                    try:
                        self.client.close()
                    except Exception:
                        pass
                    self.client = None
                    consecutive_errors = 0
                    time.sleep(2.0)
                    continue
            
            time.sleep(self.config.poll_interval_ms / 1000.0)
    
    def _read_register(self) -> Optional[int]:
        """Read the configured register from PLC"""
        if not self.client:
            print(f"[PLC] _read_register: client is None (reg={self.config.register_address}, slave={self.config.slave_id})")
            return None
        
        try:
            reg_type = self.config.register_type.lower()
            address = self.config.register_address
            
            if reg_type == "coil":
                result = self._safe_modbus_call(self.client.read_coils, address, count=1)
            elif reg_type == "discrete_input":
                result = self._safe_modbus_call(self.client.read_discrete_inputs, address, count=1)
            elif reg_type == "holding":
                result = self._safe_modbus_call(self.client.read_holding_registers, address, count=1)
            elif reg_type == "input":
                result = self._safe_modbus_call(self.client.read_input_registers, address, count=1)
            else:
                print(f"[PLC] Unknown register type: {reg_type}")
                return None
            
            # Bug fix: result can be None or an Exception (not just an error response)
            if result is None:
                print(f"[PLC] _read_register: got None result for addr={address}, type={reg_type}, slave={self.config.slave_id}")
                return None
            
            # pymodbus can return an exception object (not raise it) for some error types
            if isinstance(result, Exception):
                print(f"[PLC] _read_register: exception object in result for addr={address}: {result}")
                return None
            
            if hasattr(result, 'isError') and result.isError():
                print(f"[PLC] _read_register: Modbus error response for addr={address}, type={reg_type}, slave={self.config.slave_id}: {result}")
                return None
            
            # Get value based on register type
            if reg_type in ("coil", "discrete_input"):
                if not hasattr(result, 'bits') or not result.bits:
                    print(f"[PLC] _read_register: no bits in result for addr={address}")
                    return None
                return 1 if result.bits[0] else 0
            else:
                if not hasattr(result, 'registers') or not result.registers:
                    print(f"[PLC] _read_register: no registers in result for addr={address}")
                    return None
                return result.registers[0]
                
        except Exception as e:
            print(f"[PLC] _read_register exception for addr={self.config.register_address}, type={self.config.register_type}, slave={self.config.slave_id}: {type(e).__name__}: {e}")
            return None
    
    def _fire_trigger(self):
        """Fire the trigger callback immediately (no cooldown)"""
        print("[PLC] Rising edge detected (0 -> 1) - Triggering!")
        if self.on_trigger:
            self.on_trigger()
    
    def _safe_modbus_call(self, func, *args, **kwargs):
        """Helper to try both 'slave' and 'unit' keywords for compatibility"""
        slave_id = self.config.slave_id
        try:
            # Try 'slave' first (Pymodbus v3.x style)
            return func(*args, **kwargs, slave=slave_id)
        except TypeError:
            try:
                # Try 'unit' (Pymodbus v2.x style)
                return func(*args, **kwargs, unit=slave_id)
            except TypeError:
                # Some versions might use 'device_id' or no keyword
                return func(*args, **kwargs)

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
            value: Value to write (0-65535)
        """
        if not self.client:
            return False
        
        try:
            result = self._safe_modbus_call(self.client.write_register, address, value)
            
            if result.isError():
                print(f"[PLC] Write error to register {address}: {result}")
                return False
            
            print(f"[PLC] Written value {value} to register {address}")
            return True
            
        except Exception as e:
            print(f"[PLC] Write exception: {e}")
            return False

    def write_coil(self, address: int, value: bool) -> bool:
        """
        Write a boolean value to a coil on the PLC.
        
        Args:
            address: Coil address to write to
            value: Value to write (True or False)
            
        Returns:
            True if write was successful
        """
        if not self.client:
            print(f"[PLC] Cannot write coil - not connected")
            return False
        
        try:
            # pymodbus write_coil accepts address, value
            result = self._safe_modbus_call(self.client.write_coil, address, value)
            
            if result.isError():
                print(f"[PLC] Write error to coil {address}: {result}")
                return False
            
            print(f"[PLC] Written value {value} to coil {address}")
            return True
            
        except Exception as e:
            print(f"[PLC] Coil write exception: {e}")
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
            print(f"[PLC] read_any_register: Cannot read addr={address} - not connected")
            return None
        
        try:
            # Bug fix: was using hardcoded 'device_id' which is invalid in all pymodbus versions.
            # Use _safe_modbus_call to handle v2/v3 compatibility automatically.
            result = self._safe_modbus_call(self.client.read_holding_registers, address, count=1)
            
            if result is None or isinstance(result, Exception):
                print(f"[PLC] read_any_register: bad result from addr={address}: {result}")
                return None
            
            if hasattr(result, 'isError') and result.isError():
                print(f"[PLC] read_any_register: Modbus error from addr={address}: {result}")
                return None
            
            if not hasattr(result, 'registers') or not result.registers:
                print(f"[PLC] read_any_register: no registers in result for addr={address}")
                return None
            
            value = result.registers[0]
            print(f"[PLC] read_any_register: addr={address} = {value}")
            return value
            
        except Exception as e:
            print(f"[PLC] read_any_register exception for addr={address}: {type(e).__name__}: {e}")
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
