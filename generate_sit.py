import pandas as pd

# Define the data for the detailed SIT
data = [
    # 1. Core Navigation & UI Response
    {
        "No": 1, "Module": "Navigation", "Test Case ID": "TC-NAV-01",
        "Test Scenario": "Verify navigation to all major screens from the Main Menu",
        "Test Case Name": "Main Menu Full Navigation",
        "Pre-requisites": "App is running and showing Main Menu",
        "Test Steps": "1. Click 'Measure by Photo'\n2. Click Back\n3. Click 'Measure by Live'\n4. Click Back\n5. Click 'Manage Profiles'\n6. Click Back\n7. Click 'General Settings'\n8. Click Back",
        "Expected Result": "System navigates correctly to each screen and returns to Main Menu seamlessly. UI remains responsive without freezes.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 2, "Module": "Navigation", "Test Case ID": "TC-NAV-02",
        "Test Scenario": "Verify UI Scaling on different window sizes",
        "Test Case Name": "Responsive UI Scaling",
        "Pre-requisites": "App is running",
        "Test Steps": "1. Resize application window to minimum size\n2. Maximize application window\n3. Verify elements are still readable and buttons are clickable",
        "Expected Result": "UI elements scale according to window size using UIScaling utility. Buttons remain accessible.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },

    # 2. Camera & Detection
    {
        "No": 3, "Module": "Detection", "Test Case ID": "TC-DET-01",
        "Test Scenario": "Verify camera initialization and switching",
        "Test Case Name": "Camera Source Switch",
        "Pre-requisites": "Multiple cameras or IP camera configured",
        "Test Steps": "1. Navigate to Live Camera\n2. Change camera source from dropdown (e.g., Index 0 to Index 1 or IP Camera)\n3. Verify feed is updated",
        "Expected Result": "Old camera thread stops and new camera thread starts successfully. Feed displays correctly.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 4, "Module": "Detection", "Test Case ID": "TC-DET-02",
        "Test Scenario": "Verify AI Model selection and inference",
        "Test Case Name": "Detection Model Validation",
        "Pre-requisites": "Camera feed running",
        "Test Steps": "1. Select 'YOLO v8'\n2. Place sandal in ROI\n3. Observe bounding box\n4. Select 'FastSAM'\n5. Observe segmentation mask",
        "Expected Result": "YOLO shows bounding box for 'sandal'. FastSAM shows precise mask for measurements.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 5, "Module": "Detection", "Test Case ID": "TC-DET-03",
        "Test Scenario": "Verify system behavior when camera is disconnected",
        "Test Case Name": "Camera Disconnection Handling",
        "Pre-requisites": "Live feed running",
        "Test Steps": "1. Physically disconnect camera\n2. Observe UI and logs",
        "Expected Result": "System shows 'No cameras found' or a frozen frame but does not crash. Logs record the error.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },

    # 3. Dataset Capture & Consistency
    {
        "No": 6, "Module": "Dataset", "Test Case ID": "TC-DAT-01",
        "Test Scenario": "Verify manual capture with overlay",
        "Test Case Name": "Manual Snapshot with Bbox",
        "Pre-requisites": "Capture Dataset screen open, 'Save Measurement Result' checked",
        "Test Steps": "1. Click 'Capture Image (Manual)'\n2. Navigate to 'output/dataset'\n3. Open saved image",
        "Expected Result": "Image is saved as .jpg. Image contains detection overlay (boxes/measurements).",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 7, "Module": "Dataset", "Test Case ID": "TC-DAT-02",
        "Test Scenario": "Verify Consistency Test with CSV export",
        "Test Case Name": "Automated Repeatability Test",
        "Pre-requisites": "Capture Dataset screen open",
        "Test Steps": "1. Click 'Test Consistency'\n2. Set attempts to '50'\n3. Set model to 'YOLO'\n4. Wait for completion\n5. Open generated Excel/CSV file",
        "Expected Result": "CSV/Excel contains 50 rows of data. Columns include Timestamp, Model, Size L, Size R, mm/px, and Result.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },

    # 4. Settings & Calibration (Detailed)
    {
        "No": 8, "Module": "Settings", "Test Case ID": "TC-SET-01",
        "Test Scenario": "Verify ROI Crop and Rotation persistence",
        "Test Case Name": "Calibration Settings Persistence",
        "Pre-requisites": "General Settings screen open",
        "Test Steps": "1. Adjust ROI sliders for X, Y, W, H\n2. Set Rotation to 180\n3. Click Save\n4. Restart App\n5. Verify settings remain as adjusted",
        "Expected Result": "Settings are saved to 'app_settings.json' and reloaded correctly on startup.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": "Check JSON file manually if possible."
    },
    {
        "No": 9, "Module": "Settings", "Test Case ID": "TC-SET-02",
        "Test Scenario": "Verify Lens Distortion Correction",
        "Test Case Name": "Distortion Map Application",
        "Pre-requisites": "Calibration matrix available",
        "Test Steps": "1. Toggle 'Undistort Image' in settings\n2. Observe live feed for edge flattening",
        "Expected Result": "Live feed edges appear straighter when undistorted. Frame rate remains stable.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },

    # 5. PLC Integration (Edge Cases)
    {
        "No": 10, "Module": "PLC", "Test Case ID": "TC-PLC-01",
        "Test Scenario": "Verify PLC Modbus connectivity",
        "Test Case Name": "Modbus RTU Handshake",
        "Pre-requisites": "PLC connected via serial-USB",
        "Test Steps": "1. Enter Serial Port (e.g. /dev/ttyUSB0)\n2. Click 'Start PLC'\n3. Verify indicator turns green",
        "Expected Result": "indicator shows 'PLC: Connected'. Registers are being read at 100ms intervals.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 11, "Module": "PLC", "Test Case ID": "TC-PLC-02",
        "Test Scenario": "Verify Signal Trigger (0 to 1)",
        "Test Case Name": "Rising Edge Capture Trigger",
        "Pre-requisites": "PLC connected, Dataset screen open",
        "Test Steps": "1. Simulate value 1 in PLC register 12\n2. Verify system captures image automatically",
        "Expected Result": "Rising edge (0->1) triggers self.capture_image() immediately.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 12, "Module": "PLC", "Test Case ID": "TC-PLC-03",
        "Test Scenario": "Verify behavior on PLC Disconnection",
        "Test Case Name": "PLC Serial Error Handling",
        "Pre-requisites": "PLC connected",
        "Test Steps": "1. Unplug PLC cable\n2. Observe status indicator",
        "Expected Result": "Indicator turns red, shows 'PLC: Connection error'. App does not crash.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },

    # 6. Database & SKU Management
    {
        "No": 13, "Module": "Database", "Test Case ID": "TC-DB-01",
        "Test Scenario": "Verify Database Connection Pool",
        "Test Case Name": "DB Pool Initialization",
        "Pre-requisites": "PostgreSQL instance running",
        "Test Steps": "1. Start App\n2. Check terminal logs for '[DB] Database connection pool initialized'",
        "Expected Result": "System connects to DB using .env credentials. Pool size is within limits (1-5).",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 14, "Module": "Database", "Test Case ID": "TC-DB-02",
        "Test Scenario": "Verify behavior when Database is Offline",
        "Test Case Name": "Graceful DB Failure",
        "Pre-requisites": "Database service stopped",
        "Test Steps": "1. Start App\n2. Attempt to search for SKUs",
        "Expected Result": "App stays open. Shows 'Empty result' or warning logger. App continues with local 'skus.json' if available.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    },
    {
        "No": 15, "Module": "SKU", "Test Case ID": "TC-SKU-01",
        "Test Scenario": "Verify SKU background fetch scheduler",
        "Test Case Name": "Scheduled Data Update",
        "Pre-requisites": "Scheduler mode set to 'interval' (1 min) in settings",
        "Test Steps": "1. Wait 60 seconds\n2. Verify file 'output/settings/skus.json' modification time",
        "Expected Result": "ProductSKUWorker runs automatically every minute and saves data to local JSON disk.",
        "Actual Result": "", "Status": "", "Evidence": "", "Notes": ""
    }
]

df = pd.DataFrame(data)

# Create a writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_Detailed.xlsx"
writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
df.to_excel(writer, index=False, sheet_name='SIT_Detailed')

# Formatting
workbook = writer.book
worksheet = writer.sheets['SIT_Detailed']

# Define formats
header_format = workbook.add_format({
    'bold': True, 'bg_color': '#263238', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter'
})

cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
})

alt_cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#ECEFF1'
})

# Write the column headers with formatting
for col_num, value in enumerate(df.columns.values):
    worksheet.write(0, col_num, value, header_format)

# Set column widths
widths = [5, 12, 12, 40, 30, 30, 50, 40, 20, 10, 15, 20]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Apply data format with alternating colors
for row in range(len(df)):
    fmt = cell_format if row % 2 == 0 else alt_cell_format
    for col in range(len(df.columns)):
        worksheet.write(row + 1, col, df.iloc[row, col], fmt)

# Freeze top row
worksheet.freeze_panes(1, 0)

writer.close()
print(f"Detailed SIT document generated successfully at: {output_file}")
