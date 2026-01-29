# QC Detector System

A **Quality Control Detection System** for automated measurement and inspection of products (primarily sandals/footwear). Built with Python, OpenCV for computer vision, and PySide6 for a modern desktop GUI.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-red.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-orange.svg)



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
  - **YOLOv8-seg (AI - Recommended)** - Deep learning segmentation with hybrid ROI approach
  - **FastSAM (AI)** - Fast Segment Anything Model for universal object detection

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

## 🚀 What's New

### Latest Updates (January 2026)

#### 🔬 Metrology-Grade Detection Pipeline
- **YOLO ROI + Precision Contour Hybrid**: AI finds the object, traditional CV measures it with precision
- **Edge-First Approach**: Replaces color-based "object vs background" with explicit edge detection
- **Sobel-Based Edge Detection**: Sub-pixel accurate boundary detection (replaces noisy Canny)
- **Adaptive Logic**: Different processing for white vs dark objects

#### 📐 Advanced Measurement Features
- **Gradient Direction Coherence**: Boosts weak but aligned edges for better boundary detection
- **Directional Morphology**: Horizontal/vertical kernels prevent edge inflation
- **PCA-Based Endpoints**: Principal component analysis for precise length measurement
- **Inner Contour Enforcement**: Metrology trick for consistent precision

#### 🎨 Object Detection Improvements
- **Explicit White Object Detection**: HSV + LAB color space analysis (no more "everything not green")
- **Curved Edge Precision**: Natural curve preservation without rigid polygon approximation
- **Orientation Independence**: Works on diagonal and straight objects equally well

## 📋 System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **Camera**: USB webcam or IP camera (RTSP supported)
- **Database**: PostgreSQL (optional, for result storage)
- **AI Models** (optional): 
  - YOLOv8-seg (recommended for best accuracy)
  - FastSAM

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
# For YOLOv8-seg (best for precision)
pip install ultralytics

# Models will auto-download on first use
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

#### 🟢 YOLO-Seg (AI - Recommended)
Best for: All object types, especially white/light colored
- **Hybrid Approach**: AI finds ROI → Contour measures precisely
- Handles all colors equally well
- Metrology-grade edge detection with Sobel gradients
- Sub-pixel accuracy with PCA-based endpoints
- Slightly slower but much more accurate

#### 🟡 FastSAM (AI)
Best for: Unknown object types
- Universal object segmentation
- Good for diverse product types
- Similar to YOLO-Seg but more general-purpose

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

## ⚙️ Configuration Files

Located in `output/settings/`:

| File | Purpose |
|------|---------|
| `app_settings.json` | Camera, calibration, PLC, and detection method settings |
| `profiles.json` | Product measurement profiles with tolerances |
| `presets.json` | Camera presets (RTSP configurations) |
| `result.json` | Measurement results log |

## 🔬 Technical Details

### Detection Pipeline (YOLO-Seg)

```
1. YOLO Detection
   ↓
2. Extract ROI (bounding box + 5% margin)
   ↓
3. Explicit White Object Detection (HSV + LAB)
   ↓
4. Sobel Edge Detection (gradient magnitude)
   ↓
5. Gradient Direction Coherence Analysis
   ↓
6. Adaptive Masking (white: edges only, dark: LAB + edges)
   ↓
7. Directional Edge Bridging (H/V kernels)
   ↓
8. Inner Contour Enforcement (1px erosion)
   ↓
9. PCA-Based Principal Axis Detection
   ↓
10. Linear Regression on Endpoints
    ↓
11. Final Measurement (mm)
```

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
- **Solution**: Use **YOLO-Seg (AI - Recommended)** detection method
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

## 📊 Performance

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| Standard | ⚡⚡⚡ Fast | Good | Dark objects, controlled lighting |
| YOLO-Seg | ⚡⚡ Medium | Excellent ⭐ | All colors, precision needed |
| FastSAM | ⚡ Slower | Very Good | Diverse object types |

## 🎓 Best Practices

1. **Use YOLO-Seg for Production**: Best accuracy for all object types
2. **Calibrate Regularly**: Check ArUco calibration each session
3. **Consistent Lighting**: Use uniform lighting for best results
4. **Green Background**: Helps with all detection methods
5. **Clean Lens**: Keep camera lens clean for sharp edges

## 📝 License

Proprietary - PT Porto Indonesia Sejahtera

## 🤝 Support

For issues and feature requests, contact the IT Development team.

---

## 🔍 Advanced Features

### Gradient Direction Coherence
Analyzes local gradient alignment to distinguish true object boundaries from noise:
- Calculates gradient direction at each pixel
- Measures coherence with neighboring gradients
- Boosts edges with >60% coherence by 1.8x
- Suppresses isolated noise pixels

### PCA-Based Measurement
Uses Principal Component Analysis for precise length measurement:
- Finds principal axis of the contour
- Projects all points onto this axis
- Uses linear regression on 5% tail regions
- Extrapolates to true endpoints

### Directional Morphology
Prevents edge inflation during gap closing:
- Horizontal kernel (5×1) for horizontal gaps
- Vertical kernel (1×5) for vertical gaps
- Sequential application preserves boundary location
- Avoids isotropic dilation that cuts edges

---

**Version**: 2.0  
**Last Updated**: January 2026  
**Status**: Production Ready