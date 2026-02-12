# ArUco Calibration

The QC Detector uses **ArUco markers** for automatic camera calibration, converting pixel measurements to real-world millimeters.

## How It Works

1. ArUco markers with known physical dimensions are placed in the camera's field of view
2. The system detects the markers and calculates their pixel size
3. By comparing pixel size to known physical size, it derives the **mm/pixel ratio**
4. All subsequent measurements use this ratio for real-world conversion

## Setup

### 1. Print ArUco Markers

Use the included calibration sheet (`aruco_calibration_A3_8markers.pdf`) or the single marker (`aruco_marker_id0_50mm.pdf`).

!!! important
    Print at **100% scale** (no scaling/fit-to-page) on A3 or A4 paper. The marker's physical size must match the configured size in settings.

### 2. Place in Camera View

Position the printed marker(s) within the camera's field of view, on the same plane as the objects being measured.

### 3. Configure Settings

Go to **Settings** and set:

- **Marker Size (mm)**: Physical size of each marker (default: `50.0 mm`)
- **Dictionary**: ArUco dictionary type (default: `DICT_4X4_250`)

### 4. Auto-Calibrate

The system automatically detects visible markers and calculates the mm/pixel ratio in real-time.

## Multi-Marker Calibration

When 2+ markers are detected, the system uses **inter-marker distance calculation** for higher precision:

1. Detects all visible marker centers
2. Calculates pixel distances between marker pairs
3. Compares with known physical distances from the calibration sheet layout
4. Averages multiple pair estimates for robust calibration

!!! tip "Precision Tip"
    Using 3+ markers significantly improves calibration accuracy by averaging out individual detection errors.

## Known Marker Positions (A3 Sheet)

| Marker ID | Position (mm) | Location |
|-----------|---------------|----------|
| 0 | (45.0, 252.0) | Row 1 Left |
| 1 | (210.0, 252.0) | Row 1 Center |
| 2 | (375.0, 252.0) | Row 1 Right |
| 3 | (45.0, 148.5) | Row 2 Left |
| 4 | (375.0, 148.5) | Row 2 Right |
| 5 | (45.0, 45.0) | Row 3 Left |
| 6 | (210.0, 45.0) | Row 3 Center |
| 7 | (375.0, 45.0) | Row 3 Right |
