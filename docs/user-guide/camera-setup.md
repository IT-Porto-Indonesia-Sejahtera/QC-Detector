# Camera Setup

## USB Camera

1. Connect the USB camera to your computer
2. Go to **Settings** in the application
3. Select camera index from dropdown (0, 1, 2...)
4. Adjust resolution if needed

!!! tip
    Run `python find_camera.py` to list all available camera indices before launching the app.

## IP Camera (RTSP)

1. Go to **Settings** → **IP Camera Configuration**
2. Add a new preset with:

| Field | Example Value | Description |
|-------|---------------|-------------|
| Protocol | `rtsp` | Streaming protocol |
| IP Address | `192.168.1.100` | Camera's network IP |
| Port | `554` | RTSP port (default: 554) |
| Path | `/Streaming/Channels/101` | Manufacturer-specific stream path |
| Username | `admin` | Camera credentials (if required) |
| Password | `password` | Camera credentials (if required) |

### Common RTSP Paths by Manufacturer

| Manufacturer | RTSP Path |
|-------------|-----------|
| Hikvision | `/Streaming/Channels/101` |
| Dahua | `/cam/realmonitor?channel=1&subtype=0` |
| Generic ONVIF | `/onvif1` |

!!! warning
    Ensure your PC is on the same subnet as the camera (e.g., `192.168.1.x`).
    Test connectivity with `ping <camera-ip>` before configuring.
