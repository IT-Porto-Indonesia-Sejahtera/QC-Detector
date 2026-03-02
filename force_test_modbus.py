
import time
import sys
from input.plc_modbus_trigger import PLCModbusTrigger, ModbusConfig

PORT = "/dev/cu.usbserial-14320"
BAUD = 9600
PARITY = 'E'

# Addresses from user and logs
TRIGGER_REG = 12   # D12
RESULT_REG  = 100  # D100
COIL_ADDR   = 1600 # CIO 100.00 is usually 1600 or nearby in Omron Modbus mapping

def force_test_slave(slave_id):
    cfg = ModbusConfig(
        connection_type="rtu",
        serial_port=PORT,
        baudrate=BAUD,
        parity=PARITY,
        slave_id=slave_id,
        timeout=2.0
    )
    
    client = PLCModbusTrigger(cfg)
    print(f"\n--- Testing Slave ID: {slave_id} ---")
    
    if not client.connect():
        print(f"FAILED to open port for Slave {slave_id}")
        return False

    # 1. Try Writing to D100
    test_val = 99
    print(f"Attempting WRITE {test_val} to Holding Reg {RESULT_REG}...")
    if client.write_register(RESULT_REG, test_val):
        print("  ✓ WRITE SUCCESS!")
    else:
        print("  ✗ WRITE FAILED (No response)")

    # 2. Try Pulsing Coil 1600
    print(f"Attempting PULSE Coil {COIL_ADDR}...")
    if client.write_coil(COIL_ADDR, True):
        print("  ✓ COIL ON SUCCESS!")
        time.sleep(0.5)
        client.write_coil(COIL_ADDR, False)
        print("  ✓ COIL OFF SUCCESS!")
    else:
        print("  ✗ COIL WRITE FAILED (No response)")

    # 3. Try Reading D12
    print(f"Attempting READ Holding Reg {TRIGGER_REG}...")
    val = client._read_register()
    if val is not None:
        print(f"  ✓ READ SUCCESS! Reg {TRIGGER_REG} = {val}")
    else:
        print("  ✗ READ FAILED (No response)")

    client.disconnect()
    return True

if __name__ == "__main__":
    # Test common Omron slave IDs
    for sid in [1, 0, 2]:
        force_test_slave(sid)
        time.sleep(1)
