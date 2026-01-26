import sys
import serial.tools.list_ports
import random
import time

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

print("=" * 50)
print("PLC Modbus RTU Test")
print("=" * 50)

# Configure for Modbus RTU (Serial)
# Default to first argument if provided
target_port = "COM7" # Default
if len(sys.argv) > 1:
    target_port = sys.argv[1]
    print(f"Using provided port: {target_port}")
else:
    print("TIP: You can run this with a specific port: ./venv/bin/python test_plc_modbus.py /dev/tty.usbserial-XXX")

config = ModbusConfig(
    connection_type="rtu",  # Use RTU for serial connection
    serial_port=target_port,
    baudrate=9600,
    parity="E",
    stopbits=1,
    bytesize=8,
    slave_id=1,
    register_address=12,
    register_type="holding",
    poll_interval_ms=100
)

print(f"Connection Type: {config.connection_type}")
print(f"Serial Port: {config.serial_port}")
print(f"Baudrate: {config.baudrate}")
print(f"Parity: {config.parity}")
print(f"Slave ID: {config.slave_id}")
print(f"Register Address: {config.register_address}")
print(f"Register Type: {config.register_type}")
print("=" * 50)

# Create trigger instance
trigger = PLCModbusTrigger(config)

# Set up callbacks
def on_trigger():
    print("\n" + "!" * 50)
    print(">>> TRIGGER FIRED! (Value changed from 0 to 1)")
    print("!" * 50 + "\n")

def on_value_update(value):
    pass  # Quiet mode - the module already prints this

def on_connection_change(connected, message):
    status = "CONNECTED" if connected else "DISCONNECTED"
    print(f"[{status}] {message}")

trigger.on_trigger = on_trigger
trigger.on_value_update = on_value_update
trigger.on_connection_change = on_connection_change

# Try to connect
print("\nAttempting to connect...")
if trigger.connect():
    print("\n" + "=" * 50)
    print("CONNECTION SUCCESSFUL!")
    print("=" * 50)
    
    # Test write to register 13
    print("\n--- WRITE TEST ---")
    test_value = random.randint(1, 8)
    print(f"Testing write: Sending value {test_value} to register 13...")
    
    if trigger.write_register(13, test_value):
        print("✓ WRITE SUCCESS!")
        
        # Read back to verify
        print("\n--- READ BACK TEST ---")
        print("Reading register 13 to verify...")
        read_value = trigger.read_any_register(13)
        
        if read_value is not None:
            if read_value == test_value:
                print(f"✓ VERIFIED! Register 13 = {read_value} (matches written value)")
            else:
                print(f"⚠ MISMATCH! Wrote {test_value} but read {read_value}")
        else:
            print("✗ Could not read back register 13")
    else:
        print("✗ WRITE FAILED! Check connection and permissions.")
    
    print("\n--- READ TEST ---")
    print("Starting polling loop... Press Ctrl+C to stop.")
    print("Watching register 12 for trigger (0 -> 1)\n")
    
    trigger.start()
    
    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        trigger.stop()
        trigger.disconnect()
        print("Done!")
else:
    print("\n" + "=" * 50)
    print("CONNECTION FAILED!")
    print("=" * 50)
    print("\nPlease check:")
    print("  1. Is COM7 the correct port?")
    print("  2. Is the PLC powered on?")
    print("  3. Is the cable connected?")
    print("  4. Are the Modbus settings correct?")
    print("     - Baudrate: 9600")
    print("     - Parity: E (Even)")
    print("     - Slave ID: 1")
