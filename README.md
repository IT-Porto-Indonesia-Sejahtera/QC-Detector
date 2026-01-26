# QC Detector System

A **Quality Control Detection System** for automated measurement and inspection of products (primarily sandals/footwear). Built with Python, OpenCV for computer vision, and PySide6 for a modern desktop GUI.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-red.svg)

## Features

- **Live Camera Measurement** - Real-time object detection and measurement from USB or IP cameras
- **Photo Measurement** - Analyze and measure objects from static images
- **Video Measurement** - Process video files for batch measurements
- **Product Profiles** - Manage product SKUs with expected dimensions and tolerances
- **PLC Integration** - Modbus RTU communication for industrial automation triggers
- **Database Support** - PostgreSQL backend for storing measurement results
- **ArUco Calibration** - Automatic scale calibration using ArUco markers
- **Lens Correction** - Built-in lens distortion compensation

## System Requirements

- Python 3.8 or higher
- Windows, macOS, or Linux
- USB webcam or IP camera (RTSP supported)
- PostgreSQL database (optional, for result storage)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/IT-Porto-Indonesia-Sejahtera/QC-Detector.git
cd QC-Detector
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
Create a `.env` file in the project root for database configuration:
```env
DB_HOST=localhost
DB_NAME=qc_detector
DB_USER=app_user
DB_PASS=your_password
DB_PORT=5432
```

## Usage

### Running the Application

**Windows:**
```bash
python main.py
# Or double-click: windows.bat
```

**macOS:**
```bash
python3 main.py
# Or double-click: mac.command
```

**Linux:**
```bash
python3 main.py
# Or run: ./linux.sh
```

### Application Screens

| Screen | Description |
|--------|-------------|
| **Menu** | Main navigation hub |
| **Live Camera** | Real-time measurement with live camera feed |
| **Measure Photo** | Load and measure from image files |
| **Measure Video** | Process video files for measurements |
| **Capture Dataset** | Capture images for training/reference |
| **Settings** | Configure camera, calibration, and PLC settings |
| **Profiles** | Manage product profiles with expected dimensions |

### Camera Setup

#### USB Camera
1. Go to **Settings**
2. Select camera index from the dropdown (0, 1, 2...)

#### IP Camera (RTSP)
1. Go to **Settings** → **IP Camera Configuration**
2. Add a new preset with:
   - Protocol: `rtsp`
   - IP Address: `192.168.x.x`
   - Port: `554`
   - Path: `/Streaming/Channels/101` (varies by manufacturer)
   - Username/Password (if required)

### Calibration

For accurate real-world measurements:

1. Print an **ArUco marker** of known size (default: 50mm)
2. Place marker in the camera's field of view
3. Go to **Settings** → Set the marker size in mm
4. The system will auto-calculate `mm/pixel` ratio

### PLC Integration (Modbus RTU)

Configure in **Settings**:
- **PLC Port**: COM port for Modbus communication
- **Trigger Register**: Register to monitor for capture trigger (default: 12)
- **Result Register**: Register to write measurement results (default: 13)

## Project Structure

```
QC-Detector/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── app/                    # GUI application
│   ├── main_windows.py     # Main window controller
│   ├── pages/              # Screen/page components
│   ├── widgets/            # Reusable UI widgets
│   └── utils/              # UI utilities
├── model/                  # Computer vision & measurement
│   ├── measurement.py      # Core measurement logic
│   ├── preprocessor.py     # Image preprocessing
│   └── measure_live_sandals.py
├── backend/                # Backend services
│   ├── DB.py               # PostgreSQL database module
│   ├── aruco_utils.py      # ArUco marker detection
│   └── get_product_sku.py  # Product SKU management
├── input/                  # Input files & assets
├── output/                 # Output files & settings
│   ├── settings/           # App configuration JSON files
│   └── log_output/         # Measurement result images
└── tests/                  # Unit tests
```

## Configuration Files

Located in `output/settings/`:

| File | Purpose |
|------|---------|
| `app_settings.json` | Camera, calibration, and PLC settings |
| `profiles.json` | Product measurement profiles |
| `presets.json` | Camera presets |
| `result.json` | Measurement results log |

## Troubleshooting

### Camera Not Detected
- Ensure camera is connected before launching the app
- For IP cameras, verify network connectivity with `ping`
- Run `python find_camera.py` to list available cameras

### White Objects Not Detected
- The system uses adaptive thresholding
- Ensure good contrast between object and background
- Use a dark/colored background for white objects

### Database Connection Failed
- App continues without database if connection fails
- Check `.env` file configuration
- Verify PostgreSQL server is running

## License

Proprietary - PT Porto Indonesia Sejahtera

## Support

For issues and feature requests, contact the IT Development team.