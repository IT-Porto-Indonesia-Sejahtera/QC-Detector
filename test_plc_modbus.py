import sys
import serial.tools.list_ports
import random
import time

from input.plc_modbus_trigger import (
    ModbusConfig, PLCModbusTrigger, check_pymodbus_available
)

# Check if pymodbus is installed
if not check_pymodbus_available():
    print("ERROR: pymodbus is not installed!")
    print("Please run: pip install pymodbus")
    exit(1)

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    print("\nAvailable Serial Ports:")
    if not ports:
        print("  (None found)")
    for port, desc, hwid in sorted(ports):
        print(f"  - {port}: {desc}")
    print("")

list_serial_ports()

print("=" * 60)
print("PLC Modbus RTU Debugger Tool")
print("=" * 60)

# CONFIGURATION
target_port = "/dev/ttyUSB0" 
slave_id = 1
parity = "E"

if len(sys.argv) > 1:
    target_port = sys.argv[1]
if len(sys.argv) > 2:
    slave_id = int(sys.argv[2])
if len(sys.argv) > 3:
    parity = sys.argv[3].upper() # N, E, or O

# Default addresses per new requirements
TRIGGER_REG = 12
RESULT_REG = 100
COIL_TRIG = 1600

# Delays for testing
PRE_CAPTURE_DELAY = 0.5 
POST_RESULT_DELAY = 0.5

config = ModbusConfig(
    connection_type="rtu",
    serial_port=target_port,
    baudrate=9600,
    parity=parity,
    stopbits=1,
    bytesize=8,
    slave_id=slave_id,
    register_address=TRIGGER_REG,
    register_type="holding",
    poll_interval_ms=100
)

print(f"Port: {config.serial_port} | Baud: {config.baudrate} | Parity: {config.parity} | Slave ID: {slave_id}")
print(f"Trigger Reg (R): {TRIGGER_REG}")
print(f"Result Reg (W): {RESULT_REG}")
print(f"Coil Trig (W): {COIL_TRIG}")
print("-" * 60)

trigger = PLCModbusTrigger(config)

def on_trigger():
    print(f"\n[DEBUG] {time.strftime('%H:%M:%S')} >>> PLC TRIGGER DETECTED (Reg {TRIGGER_REG} = 1)")
    
    # 1. Simulate Pre-Capture Delay
    print(f"[DEBUG] Waiting {PRE_CAPTURE_DELAY}s (Pre-Capture)...")
    time.sleep(PRE_CAPTURE_DELAY)
    
    # 2. Simulate Capture & Logic
    is_good = random.choice([True, False])
    val = random.randint(1, 4) if is_good else random.randint(5, 8)
    res_str = "GOOD" if is_good else "BAD"
    
    # 3. Write Result
    print(f"[DEBUG] Writing {res_str} result ({val}) to Register {RESULT_REG}...")
    if trigger.write_register(RESULT_REG, val):
        print(f"[DEBUG] Result written successfully.")
    
    # 4. Post-Result Delay
    print(f"[DEBUG] Waiting {POST_RESULT_DELAY}s (Post-Result)...")
    time.sleep(POST_RESULT_DELAY)
    
    # 5. Pulse Coil
    print(f"[DEBUG] Sending Pulse to Coil {COIL_TRIG}...")
    if trigger.write_coil(COIL_TRIG, True):
        time.sleep(0.5) # Holding pulse for 500ms
        trigger.write_coil(COIL_TRIG, False)
        print(f"[DEBUG] Coil pulse complete.")
    
    print("-" * 30)
    print("READY FOR NEXT TRIGGER")
    print("-" * 30)

def on_connection_change(connected, message):
    status = "CONNECTED" if connected else "DISCONNECTED"
    print(f"[{status}] {message}")

trigger.on_trigger = on_trigger
trigger.on_connection_change = on_connection_change

print("\nAttempting to connect...")
if trigger.connect():
    print("\n" + "=" * 60)
    print("CONNECTION SUCCESSFUL! Polling for triggers...")
    print("=" * 60)
    
    trigger.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        trigger.stop()
        trigger.disconnect()
        print("Done.")
else:
    print("\nCONNECTION FAILED! Check your port and PLC settings.")
