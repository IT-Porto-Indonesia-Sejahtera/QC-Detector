# PLC Integration (Modbus RTU)

The QC Detector can integrate with industrial PLCs via **Modbus RTU** for automated capture triggering and result reporting.

## Configuration

Go to **Settings** and configure:

| Setting | Default | Description |
|---------|---------|-------------|
| PLC Port | — | COM port for Modbus communication (e.g., `COM3`) |
| Trigger Register | `12` | Holding register monitored for capture trigger |
| Result Register | `13` | Holding register where measurement results are written |

## Trigger Flow

```
PLC writes 1 to Register 12
        ↓
QC Detector detects 0→1 transition
        ↓
Camera captures image immediately
        ↓
Measurement runs (selected detection method)
        ↓
Result written to Register 13
        ↓
QC Detector resets Register 12 to 0
```

## Result Values

| Value Range | Meaning |
|-------------|---------|
| 1–4 | **Good** — measurement within tolerance |
| 5–8 | **Bad** — measurement outside tolerance |

## Troubleshooting

!!! warning "Connection Issues"
    - Verify the correct COM port in Device Manager
    - Check Modbus RTU settings (baud rate, parity, stop bits)
    - Ensure the PLC is powered on and configured for Modbus slave mode
    - Test with `python test_plc_modbus.py` to verify connectivity
