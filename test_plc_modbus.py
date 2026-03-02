"""
PLC Modbus RTU Debugger / Test Tool
=====================================
Usage:
    python test_plc_modbus.py [port] [slave_id] [parity] [baudrate]

Examples:
    python test_plc_modbus.py COM3
    python test_plc_modbus.py COM3 1 E 9600
    python test_plc_modbus.py COM3 1 N 115200

If connection succeeds, it polls Reg 12 continuously and shows live values.
If connection fails, it auto-scans all common baudrate / parity / slave-ID combos.
"""

import sys
import time
import random

try:
    import serial.tools.list_ports
    SERIAL_TOOLS_AVAILABLE = True
except ImportError:
    SERIAL_TOOLS_AVAILABLE = False

from input.plc_modbus_trigger import (
    ModbusConfig, PLCModbusTrigger, check_pymodbus_available,
    _PYMODBUS_V2, _PYMODBUS_V3_FRAMER
)

# ─────────────────────────────────────────────
# 1. Sanity checks
# ─────────────────────────────────────────────
if not check_pymodbus_available():
    print("ERROR: pymodbus is not installed!")
    print("Run: pip install pymodbus")
    sys.exit(1)

try:
    import pymodbus
    _pmv = pymodbus.__version__
except Exception:
    _pmv = "unknown"

if _PYMODBUS_V2:
    _framing_info = f"v2.x — using method='rtu'"
elif _PYMODBUS_V3_FRAMER:
    _framing_info = f"v3.1+ (FramerType.RTU) — explicit RTU framing"
else:
    _framing_info = f"v3.0 — RTU is default framer"

print(f"pymodbus {_pmv}  [{_framing_info}]")


def list_serial_ports():
    if not SERIAL_TOOLS_AVAILABLE:
        print("  (serial.tools.list_ports not available - install pyserial)")
        return
    ports = list(serial.tools.list_ports.comports())
    print("\nAvailable Serial Ports:")
    if not ports:
        print("  (None found — check USB cable / driver)")
    for port in sorted(ports):
        print(f"  - {port.device}: {port.description}  [{port.hwid}]")
    print()

list_serial_ports()

print("=" * 65)
print("  PLC Modbus RTU Debugger")
print("=" * 65)

# ─────────────────────────────────────────────
# 2. Config from CLI args
# ─────────────────────────────────────────────
target_port  = sys.argv[1] if len(sys.argv) > 1 else "COM3"
slave_id     = int(sys.argv[2]) if len(sys.argv) > 2 else 1
parity       = sys.argv[3].upper() if len(sys.argv) > 3 else "E"
baudrate     = int(sys.argv[4]) if len(sys.argv) > 4 else 115200

TRIGGER_REG  = 12
RESULT_REG   = 100
COIL_TRIG    = 1600
PRE_CAPTURE_DELAY  = 0.0
POST_RESULT_DELAY  = 0.0

config = ModbusConfig(
    connection_type="rtu",
    serial_port=target_port,
    baudrate=baudrate,
    parity=parity,
    stopbits=1,
    bytesize=8,
    slave_id=slave_id,
    register_address=TRIGGER_REG,
    register_type="holding",
    poll_interval_ms=10,
    timeout=3.0,
    retries=0,  # No retries — let each read wait the full timeout
)

print(f"Port     : {config.serial_port}")
print(f"Baudrate : {config.baudrate}")
print(f"Parity   : {config.parity}  (N=None, E=Even, O=Odd)")
print(f"Stopbits : {config.stopbits}")
print(f"Slave ID : {slave_id}")
print(f"Trigger Reg (Read) : D{TRIGGER_REG}  →  Modbus holding addr {TRIGGER_REG}")
print(f"Result  Reg (Write): D{RESULT_REG}")
print(f"Result  Coil (Pulse): CIO 100.00 → Coil {COIL_TRIG}")
print("-" * 65)

# ─────────────────────────────────────────────
# 3. Callbacks
# ─────────────────────────────────────────────
def on_trigger():
    print(f"\n[TRIGGER] {time.strftime('%H:%M:%S')} >>> Reg {TRIGGER_REG} = 1  (rising edge!)")
    print(f"[TRIGGER]  Pre-capture delay: {PRE_CAPTURE_DELAY}s")
    time.sleep(PRE_CAPTURE_DELAY)

    is_good = random.choice([True, False])
    val     = random.randint(1, 4) if is_good else random.randint(5, 8)
    label   = "GOOD" if is_good else "BAD"

    print(f"[TRIGGER]  Writing result {label} ({val}) → Reg {RESULT_REG}")
    if trigger.write_register(RESULT_REG, val):
        print(f"[TRIGGER]  Write OK.")
    else:
        print(f"[TRIGGER]  Write FAILED.")

    time.sleep(POST_RESULT_DELAY)

    print(f"[TRIGGER]  Pulsing Coil {COIL_TRIG} HIGH for 500ms...")
    if trigger.write_coil(COIL_TRIG, True):
        time.sleep(0.5)
        trigger.write_coil(COIL_TRIG, False)
        print(f"[TRIGGER]  Coil pulse done.")
    else:
        print(f"[TRIGGER]  Coil write FAILED.")

    print("-" * 30 + " READY " + "-" * 30)


def on_value_update(value):
    # Printed inline so it doesn't spam the terminal
    print(f"[{time.strftime('%H:%M:%S')}]  Reg {TRIGGER_REG} = {value}          ", end='\r')


def on_connection_change(connected: bool, message: str):
    marker = "✓ CONNECTED" if connected else "✗ DISCONNECTED"
    print(f"\n[CONN]  {marker}  — {message}")


# ─────────────────────────────────────────────
# 4. Wire callbacks and attempt connection
# ─────────────────────────────────────────────
trigger = PLCModbusTrigger(config)
trigger.on_trigger           = on_trigger
trigger.on_value_update      = on_value_update
trigger.on_connection_change = on_connection_change

print("\nAttempting connection...")
t0 = time.time()
connected = trigger.connect()
elapsed_ms = (time.time() - t0) * 1000
print(f"Connection attempt took {elapsed_ms:.0f}ms")

if connected:
    # ── LIVE POLLING MODE ──────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  CONNECTION OK  —  polling for triggers (Ctrl+C to stop)")
    print("=" * 65)
    print()

    # One-shot diagnostic read BEFORE starting the thread so we can see timing
    print("[DIAG]  Doing a single manual read to check response time...")
    t1 = time.time()
    val = trigger._read_register()
    t2 = time.time()
    rtt_ms = (t2 - t1) * 1000
    if val is not None:
        print(f"[DIAG]  OK  — Reg {TRIGGER_REG} = {val}  (RTT: {rtt_ms:.1f}ms)")
    else:
        print(f"[DIAG]  WARNING: read returned None after {rtt_ms:.1f}ms")
        print(f"[DIAG]  Port opened, but PLC is not ACK-ing Modbus requests.")
        print(f"[DIAG]  Possible causes:")
        print(f"         1. Wrong slave ID  (current: {slave_id}) — try 0")
        print(f"         2. Wrong parity   (current: {parity}) — try N or O")
        print(f"         3. Wrong register type — holding vs input")
        print(f"         4. RS-485 wiring: A/B lines may be swapped")
        print(f"         5. PLC Modbus function not enabled in CX-Programmer")
        print(f"         6. Register D{TRIGGER_REG} may not exist on this PLC model")
        print()

    trigger.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        trigger.stop()
        trigger.disconnect()
        print("Disconnected. Done.")

else:
    # ── AUTO SCAN MODE ─────────────────────────────────────────────────────
    print()
    print("─── Connection failed. Starting auto-scan... ───")
    print("(This tries every common baudrate × parity × slave-ID combo)")
    print()

    BAUDRATES  = [9600, 19200, 38400, 57600, 115200]
    PARITIES   = ["E", "N", "O"]
    SLAVE_IDS  = [1, 0, 2, 3]

    total = len(BAUDRATES) * len(PARITIES) * len(SLAVE_IDS)
    tried = 0
    found = False

    for baud in BAUDRATES:
        if found:
            break
        for par in PARITIES:
            if found:
                break
            for sid in SLAVE_IDS:
                tried += 1
                cfg = ModbusConfig(
                    connection_type="rtu",
                    serial_port=target_port,
                    baudrate=baud,
                    parity=par,
                    stopbits=1,
                    bytesize=8,
                    slave_id=sid,
                    register_address=TRIGGER_REG,
                    register_type="holding",
                    timeout=1.5,  # shorter timeout for scan speed
                )
                label = f"Baud={baud:>6}  Parity={par}  SlaveID={sid}"
                print(f"  [{tried:>3}/{total}] Trying {label} ...", end='', flush=True)

                t_scan = time.time()
                scan_trigger = PLCModbusTrigger(cfg)
                ok = scan_trigger.connect()
                if ok:
                    val = scan_trigger._read_register()
                    elapsed = (time.time() - t_scan) * 1000
                    if val is not None:
                        print(f"  ✓  FOUND! Reg {TRIGGER_REG} = {val}  ({elapsed:.0f}ms)")
                        print()
                        print("=" * 65)
                        print(f"  PLC FOUND with these settings:")
                        print(f"    Port     : {target_port}")
                        print(f"    Baudrate : {baud}")
                        print(f"    Parity   : {par}")
                        print(f"    Slave ID : {sid}")
                        print(f"  Update your app settings to match the above!")
                        print("=" * 65)
                        found = True
                        scan_trigger.disconnect()
                        break
                    else:
                        print(f"  ~ Port opened, no Modbus reply  ({elapsed:.0f}ms)")
                else:
                    elapsed = (time.time() - t_scan) * 1000
                    print(f"  ✗  Port open failed  ({elapsed:.0f}ms)")
                scan_trigger.disconnect()

    if not found:
        print()
        print("=" * 65)
        print("  SCAN COMPLETE — PLC not responding on any setting.")
        print()
        print("  Hardware checklist:")
        print("   [?] Is the USB-Serial adapter showing in Device Manager?")
        print("   [?] Is the PLC powered ON?")
        print("   [?] Are TX/RX (or A/B for RS-485) wired correctly?")
        print("       Try swapping A ↔ B on the RS-485 terminal block.")
        print("   [?] Is the PLC Modbus slave function enabled?")
        print("       Check CX-Programmer: PLC Settings → Serial Port")
        print("   [?] Does the PLC use RS-232 or RS-485? Check cable spec.")
        print("=" * 65)
