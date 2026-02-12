# Getting Started

## System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **Camera**: USB webcam or IP camera (RTSP supported)
- **Database**: PostgreSQL (optional, for result storage)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/IT-Porto-Indonesia-Sejahtera/QC-Detector.git
cd QC-Detector
```

### 2. Create Virtual Environment

=== "Windows"

    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

=== "macOS"

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

=== "Linux"

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install AI Models (Optional but Recommended)

```bash
# For YOLOv8-seg and Advanced (YOLOv8x + SAM)
pip install ultralytics
```

Models will auto-download on first use:

| Model | Size | Used By |
|-------|------|---------|
| `yolov8n-seg.pt` | ~13 MB | YOLO-Seg detection |
| `yolov8x.pt` | ~130 MB | Advanced — The Spotter |
| `sam_b.pt` | ~375 MB | Advanced — The Surgeon |
| `FastSAM-s.pt` | ~24 MB | FastSAM detection |

### 5. Configure Environment Variables (Optional)

Create a `.env` file in the project root for database connectivity:

```env
DB_HOST=localhost
DB_NAME=qc_detector
DB_USER=app_user
DB_PASS=your_password
DB_PORT=5432
```

## Running the Application

=== "Windows"

    ```bash
    python main.py
    # Or double-click: windows.bat
    ```

=== "macOS"

    ```bash
    python3 main.py
    # Or double-click: mac.command
    ```

=== "Linux"

    ```bash
    python3 main.py
    # Or run: ./linux.sh
    ```

## Application Screens

| Screen | Description |
|--------|-------------|
| **Menu** | Main navigation hub |
| **Live Camera** | Real-time measurement with live camera feed |
| **Measure Photo** | Load and measure from image files |
| **Measure Video** | Process video files for measurements |
| **Capture Dataset** | Capture images for training/reference |
| **Settings** | Configure camera, calibration, and PLC settings |
| **Profiles** | Manage product profiles with expected dimensions |

## Troubleshooting

### Camera Not Detected

- Ensure camera is connected before launching
- For IP cameras, verify network with `ping <camera-ip>`
- Run `python find_camera.py` to list available cameras

### Database Connection Failed

- App continues without database — this is safe
- Check `.env` configuration values
- Verify PostgreSQL is running: `pg_ctl status`

### AI Models Not Working

- Ensure `ultralytics` is installed: `pip install ultralytics`
- Models download on first use — internet connection required
- Check console output for specific error messages
