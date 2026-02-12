# QC Detector System

A **Quality Control Detection System** for automated measurement and inspection of products (primarily sandals/footwear). Built with Python, OpenCV for computer vision, and PySide6 for a modern desktop GUI.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-red.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8x%20%2B%20SAM-purple.svg)



### Core Capabilities
- **Live Camera Measurement** - Real-time object detection and measurement from USB or IP cameras
- **Photo Measurement** - Analyze and measure objects from static images
- **Video Measurement** - Process video files for batch measurements
- **Product Profiles** - Manage product SKUs with expected dimensions and tolerances
- **PLC Integration** - Modbus RTU communication for industrial automation triggers
- **Database Support** - PostgreSQL backend for storing measurement results

### Advanced Computer Vision
- **Multiple Detection Methods**:
  - **Standard (Contour)** - Traditional OpenCV edge detection with HSV color filtering
  - **YOLOv8n-seg (AI)** - Deep learning segmentation with hybrid ROI approach
  - **FastSAM (AI)** - Fast Segment Anything Model for universal object detection
  - **Advanced Multi AI (YOLOv8x + SAM)** - Two-model pipeline: YOLOv8 Extra-Large detects objects, SAM produces pixel-perfect masks

### Measurement Technologies
- **Metrology-Grade Edge Detection**:
  - Sobel gradient magnitude for sub-pixel accuracy
  - Gradient direction coherence analysis
  - Directional edge bridging (prevents over-segmentation)
  
- **Advanced Endpoint Detection**:
  - PCA-based principal axis analysis
  - Linear regression on projected endpoints
  - Robust to noise and measurement variations

- **Calibration Systems**:
  - ArUco marker auto-calibration
  - Lens distortion compensation
  - Real-time mm/pixel ratio calculation
  
## 📋 System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **Camera**: USB webcam or IP camera (RTSP supported)
- **Database**: PostgreSQL (optional, for result storage)
- **AI Models** (optional):
  - Standard (Contour)
  - FastSAM
  - YOLOv8-seg
  - YOLOv8x + SAM (advanced two-model pipeline)

## 🔧 Installation

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

### 4. Install AI Models (Optional but Recommended)
```bash
# For YOLOv8-seg and Advanced (YOLOv8x + SAM)
pip install ultralytics

# Models will auto-download on first use:
#   - yolov8n-seg.pt  (~13MB)  for YOLO-Seg
#   - yolov8x.pt      (~130MB) for Advanced (The Spotter)
#   - sam_b.pt         (~375MB) for Advanced (The Surgeon)
```

### 5. Configure Environment Variables (Optional)
Create a `.env` file in the project root:
```env
DB_HOST=localhost
DB_NAME=qc_detector
DB_USER=app_user
DB_PASS=your_password
DB_PORT=5432
```

## 🎮 Usage

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

### Detection Methods

#### 🔵 Standard (Contour)
Best for: Dark objects with good contrast
- Traditional OpenCV edge detection
- HSV color filtering for white objects on green background
- Fast and CPU-efficient
- Good for controlled environments
  
#### 🟡 FastSAM (AI)
Best for: Unknown object types
- Universal object segmentation
- Good for diverse product types
- Similar to YOLO-Seg but more general-purpose

#### 🟢 YOLO-Seg (AI)
Best for: All object types, especially white/light colored
- **Hybrid Approach**: AI finds ROI → Contour measures precisely
- Handles all colors equally well
- Metrology-grade edge detection with Sobel gradients
- Sub-pixel accuracy with PCA-based endpoints
- Slightly slower but much more accurate

#### 🟣 Advanced (YOLOv8x + SAM)
Best for: Maximum segmentation quality, difficult objects
- **Two-Model Pipeline**: YOLOv8 Extra-Large detects → SAM segments with pixel-perfect precision
- YOLOv8x ("The Spotter"): Extra-Large model sees texture differences invisible to smaller models
- SAM ("The Surgeon"): Segment Anything Model produces studio-quality masks from edge & depth cues
- Smart bounding-box expansion (5% margin) for SAM prompt
- Falls back to center-point prompt if YOLO finds no objects
- Background mask filtering (rejects masks >70% of image area)
- GPU accelerated with automatic CUDA detection
- Slowest but highest quality segmentation

### Camera Setup

#### USB Camera
1. Go to **Settings**
2. Select camera index from dropdown (0, 1, 2...)
3. Adjust resolution if needed

#### IP Camera (RTSP)
1. Go to **Settings** → **IP Camera Configuration**
2. Add preset with:
   - Protocol: `rtsp`
   - IP Address: `192.168.x.x`
   - Port: `554`
   - Path: `/Streaming/Channels/101` (manufacturer-specific)
   - Credentials (if required)

### Calibration

For accurate real-world measurements:

1. **Print ArUco Marker**: Use 50mm marker (default size)
2. **Place in View**: Position marker in camera's field of view
3. **Configure**: Settings → Set marker size in mm
4. **Auto-Calibrate**: System calculates mm/pixel ratio automatically

### PLC Integration (Modbus RTU)

Configure in **Settings**:
- **PLC Port**: COM port for Modbus communication
- **Trigger Register**: Monitor this register for capture trigger (default: 12)
- **Result Register**: Write measurement results here (default: 13)

When register 12 changes from 0→1, system automatically captures and measures.

## 📁 Project Structure

```
QC-Detector/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── app/                         # GUI application
│   ├── main_windows.py          # Main window controller
│   ├── pages/                   # Screen components
│   │   ├── menu.py              # Main menu
│   │   ├── live_camera_screen.py
│   │   ├── measure_photo_screen.py
│   │   ├── measure_video_screen.py
│   │   ├── capture_dataset_screen.py
│   │   ├── settings_screen.py
│   │   └── profiles_screen.py
│   ├── widgets/                 # Reusable UI components
│   └── utils/                   # UI utilities
├── model/                       # Computer vision & measurement
│   ├── measurement.py           # Core measurement logic
│   │   ├── strong_mask()        # Edge-first metrology detection
│   │   ├── refined_endpoints()  # PCA-based length measurement
│   │   └── measure_sandals()    # Main measurement function
│   ├── advanced_inference.py    # Advanced YOLOv8x + SAM pipeline
│   ├── yolo_inference.py        # YOLOv8-seg integration (Hybrid ROI)
│   ├── fastsam_inference.py     # FastSAM integration
│   ├── preprocessor.py          # Image preprocessing
│   └── measure_live_sandals.py  # Live camera measurement
├── backend/                     # Backend services
│   ├── DB.py                    # PostgreSQL database module
│   ├── aruco_utils.py           # ArUco marker detection
│   ├── plc_handler.py           # Modbus PLC communication
│   └── get_product_sku.py       # Product SKU management
├── input/                       # Input files & assets
├── output/                      # Output files & settings
│   ├── settings/                # App configuration JSON files
│   └── log_output/              # Measurement result images
└── tests/                       # Unit tests
```

## 🔬 Technical Details

### 📊 Performance

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| Standard | ⚡⚡⚡ Fast | Good | Dark objects, controlled lighting |
| FastSAM | ⚡⚡ Medium | Very Good | Diverse object types |
| YOLO-Seg | ⚡⚡ Medium | Excellent ⭐ | All colors (more contrast object), precision needed |
| Advanced (YOLOv8x + SAM) | ⚡ Slower (need GPU for best inference) | Best ⭐⭐ | Difficult objects (low contrast object), maximum quality |

### Measurement Precision

- **Sub-pixel Accuracy**: Sobel gradients preserve boundary precision
- **Gradient Coherence**: Boosts weak but aligned edges (1.8x multiplier)
- **PCA Endpoints**: Uses 5% tails with linear regression extrapolation
- **Inner Contour**: Metrology standard for consistent measurements

## 🐛 Troubleshooting

### Camera Issues

**Camera Not Detected**
- Ensure camera is connected before launching
- For IP cameras, verify network with `ping <camera-ip>`
- Run `python find_camera.py` to list available cameras

**Poor Image Quality**
- Check camera focus and lighting
- Adjust resolution in Settings
- Clean camera lens

### Detection Issues

**White Objects Over-Segmented (Entire Surface Filled)**
- **Solution**: Use **YOLO-Seg (AI)** detection method
- The edge-first approach prevents over-segmentation on white objects
- Console will show: `[strong_mask] White object detected - using edge-first approach`

**Dark Objects with Curved Edges Cut Off**
- **Solution**: YOLO-Seg with hybrid ROI approach
- System extracts ROI first, then runs precision contour inside
- Console shows: `[YOLOv8-seg] Extracting ROI... Running precision contour detection inside ROI...`

**Straight Objects Detected Poorly (Diagonal Works Fine)**
- **Solution**: Sobel edge detection with coherence analysis
- Directional morphology prevents internal feature detection
- Works equally well on all orientations

### Database Issues

**Connection Failed**
- App continues without database
- Check `.env` configuration
- Verify PostgreSQL is running: `pg_ctl status`

## 📝 License

Proprietary - PT Porto Indonesia Sejahtera

## 🤝 Support

For issues and feature requests, contact the IT Departemen team.

---

**Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready
