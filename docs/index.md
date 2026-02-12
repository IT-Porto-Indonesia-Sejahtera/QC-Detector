# QC Detector System

A **Quality Control Detection System** for automated measurement and inspection of products (primarily sandals/footwear). Built with Python, OpenCV for computer vision, and PySide6 for a modern desktop GUI.

---

## Core Capabilities

- :material-camera: **Live Camera Measurement** — Real-time object detection and measurement from USB or IP cameras
- :material-image: **Photo Measurement** — Analyze and measure objects from static images
- :material-video: **Video Measurement** — Process video files for batch measurements
- :material-tag: **Product Profiles** — Manage product SKUs with expected dimensions and tolerances
- :material-robot-industrial: **PLC Integration** — Modbus RTU communication for industrial automation triggers
- :material-database: **Database Support** — PostgreSQL backend for storing measurement results

## Detection Methods

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| Standard (Contour) | ⚡⚡⚡ Fast | Good | Dark objects, controlled lighting |
| FastSAM (AI) | ⚡⚡ Medium | Very Good | Diverse object types |
| YOLO-Seg (AI) | ⚡⚡ Medium | Excellent ⭐ | All colors (more contrast), precision needed |
| Advanced (YOLOv8x + SAM) | ⚡ Slower (GPU recommended) | Best ⭐⭐ | Difficult objects (low contrast), maximum quality |

## Quick Start

```bash
git clone https://github.com/IT-Porto-Indonesia-Sejahtera/QC-Detector.git
cd QC-Detector
pip install -r requirements.txt
python main.py
```

See the [Getting Started](getting-started.md) guide for detailed installation instructions.

## Project Structure

```
QC-Detector/
├── main.py                      # Application entry point
├── app/                         # GUI application (PySide6)
│   ├── main_windows.py          # Main window controller
│   ├── pages/                   # Screen components
│   ├── widgets/                 # Reusable UI components
│   └── utils/                   # UI utilities
├── model/                       # Computer vision & measurement
│   ├── measurement.py           # Core measurement logic
│   ├── advanced_inference.py    # YOLOv8x + SAM pipeline
│   ├── yolo_inference.py        # YOLOv8-seg integration
│   ├── fastsam_inference.py     # FastSAM integration
│   └── measure_live_sandals.py  # Live camera measurement
├── backend/                     # Backend services
│   ├── DB.py                    # PostgreSQL database
│   ├── aruco_utils.py           # ArUco marker detection
│   └── get_product_sku.py       # Product SKU management
└── tests/                       # Unit tests
```

---

**Version**: 1.0 | **Last Updated**: February 2026 | **Status**: Production Ready

*Proprietary — PT Porto Indonesia Sejahtera*
