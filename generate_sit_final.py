import pandas as pd

# Define the data based on the screenshot format
data = [
    # --- STARTUP ---
    {
        "Test Case ID": 1, "Test Case Scenario": "App Startup", "Test Case": "Verify system initialization",
        "Pre-Conditions": "App is closed", "Test Steps": "1. Run main.py or start_app.command",
        "Test Data": "OS: macOS/Windows", "Expected Results": "App opens without errors. Splash/Menu appears.",
        "Post-Condition": "Stay on Main Menu", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 2, "Test Case Scenario": "App Startup", "Test Case": "Verify Database Connection",
        "Pre-Conditions": "PostgreSQL service running", "Test Steps": "1. Observe terminal logs on startup",
        "Test Data": ".env configuration", "Expected Results": "Log shows '[DB] Database connection pool initialized'",
        "Post-Condition": "DB connected", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 3, "Test Case Scenario": "App Startup", "Test Case": "Verify AI Model Warmup",
        "Pre-Conditions": "App starting", "Test Steps": "1. Wait for 5-10 seconds",
        "Test Data": "YOLO/SAM weights", "Expected Results": "Log shows '[Startup] Background AI model warmup started'",
        "Post-Condition": "Models ready in memory", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- NAVIGATION ---
    {
        "Test Case ID": 4, "Test Case Scenario": "Navigation", "Test Case": "Switch between screens",
        "Pre-Conditions": "On Main Menu", "Test Steps": "1. Click all buttons (Live, Photo, Dataset, Settings)",
        "Test Data": "N/A", "Expected Results": "System navigates to target screen and back button works.",
        "Post-Condition": "Return to Menu successfully", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CAMERA & DETECTION ---
    {
        "Test Case ID": 5, "Test Case Scenario": "Camera Feed", "Test Case": "Initialize Camera Index 0",
        "Pre-Conditions": "USB Camera connected", "Test Steps": "1. Go to Live Camera\n2. Select Index 0",
        "Test Data": "Camera 0", "Expected Results": "Live feed appears clearly within the placeholder.",
        "Post-Condition": "Feed running", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 6, "Test Case Scenario": "Camera Feed", "Test Case": "Initialize IP Camera",
        "Pre-Conditions": "IP Camera URL configured in app_settings.json", "Test Steps": "1. Go to Live Camera\n2. Select IP Camera",
        "Test Data": "rtsp://admin:pass@ip:554", "Expected Results": "RTSP stream opens and displays feed.",
        "Post-Condition": "Network stream active", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 7, "Test Case Scenario": "Inference", "Test Case": "YOLO v8 Detection",
        "Pre-Conditions": "Feed running, Sandal in ROI", "Test Steps": "1. Select YOLO v8 from Model selector",
        "Test Data": "Object: Sandal", "Expected Results": "Bounding box appears around the sandal with 'sandal' label.",
        "Post-Condition": "Bounding box visible", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 8, "Test Case Scenario": "Inference", "Test Case": "FastSAM Segmentation",
        "Pre-Conditions": "Feed running, Sandal in ROI", "Test Steps": "1. Select FastSAM from Model selector",
        "Test Data": "Object: Sandal", "Expected Results": "Transparent mask overlay appears covering the sandal area precisely.",
        "Post-Condition": "Mask visible", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CALIBRATION ---
    {
        "Test Case ID": 9, "Test Case Scenario": "Calibration", "Test Case": "Manual mm/px Update",
        "Pre-Conditions": "Settings screen open", "Test Steps": "1. Input 0.231 manually\n2. Save",
        "Test Data": "Value: 0.231", "Expected Results": "Measurements on live screen change based on new ratio.",
        "Post-Condition": "Ratio updated in memory", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 10, "Test Case Scenario": "Calibration", "Test Case": "ArUco Detection for mm/px",
        "Pre-Conditions": "Calibration sheet placed under camera", "Test Steps": "1. Click 'Detect ArUco' (if on screen)\n2. Observe mm/px calculate",
        "Test Data": "ArUco Marker ID 0", "Expected Results": "System detects markers and calculates mm/px automated.",
        "Post-Condition": "Ratio calibrated", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 11, "Test Case Scenario": "Distortion", "Test Case": "Toggle Undistort Map",
        "Pre-Conditions": "Settings screen open", "Test Steps": "1. Toggle 'Enable Undistort'\n2. Click Save",
        "Test Data": "Matrix params", "Expected Results": "Live image edges flatten out. No significant frame drop.",
        "Post-Condition": "Image transformation applied", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- DATASET CAPTURE ---
    {
        "Test Case ID": 12, "Test Case Scenario": "Manual Capture", "Test Case": "Save Raw Image",
        "Pre-Conditions": "Dataset screen open, feed active", "Test Steps": "1. Click Capture Image (Manual)",
        "Test Data": "Dir: output/dataset", "Expected Results": "New .jpg file created in designated folder.",
        "Post-Condition": "File exists on disk", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 13, "Test Case Scenario": "Manual Capture", "Test Case": "Save with Overlay",
        "Pre-Conditions": "'Save Measurement Overlay' checked", "Test Steps": "1. Click Capture Image (Manual)",
        "Test Data": "Output: measured_xxx.jpg", "Expected Results": "Saved image contains blue boxes and text measurements.",
        "Post-Condition": "Overlay image saved", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 14, "Test Case Scenario": "Consistency", "Test Case": "Automated 100-frame Test",
        "Pre-Conditions": "Sandal statically placed", "Test Steps": "1. Click Test Consistency\n2. Set attempts: 100",
        "Test Data": "N: 100", "Expected Results": "Process runs to completion. Progress bar updates correctly.",
        "Post-Condition": "Test finished", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 15, "Test Case Scenario": "Consistency", "Test Case": "Export to Excel",
        "Pre-Conditions": "Consistency test finished", "Test Steps": "1. Verify presence of .xlsx file in output folder",
        "Test Data": "Filename: consist_test_xxx.xlsx", "Expected Results": "Excel file opens with valid measurement data rows.",
        "Post-Condition": "Data report ready", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- PLC INTEGRATION ---
    {
        "Test Case ID": 16, "Test Case Scenario": "PLC Connect", "Test Case": "Verify Modbus RTU Init",
        "Pre-Conditions": "PLC Serial cable connected", "Test Steps": "1. Configure COM Port in settings\n2. Click Start PLC",
        "Test Data": "COM3, 9600, E81", "Expected Results": "Indicator shows 'PLC: Connected'. Status label at top is green.",
        "Post-Condition": "Polling thread active", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 17, "Test Case Scenario": "PLC Trigger", "Test Case": "Rising Edge Automatic Capture",
        "Pre-Conditions": "PLC connected, trigger enabled", "Test Steps": "1. Toggle PLC value 0 -> 1",
        "Test Data": "Register 12", "Expected Results": "System ignores value 0, then captures image immediately on 1.",
        "Post-Condition": "Single capture event", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- SKU & PROFILE ---
    {
        "Test Case ID": 18, "Test Case Scenario": "SKU Management", "Test Case": "Search SKU by Keyword",
        "Pre-Conditions": "Profiles page open", "Test Steps": "1. Enter 'Sandal' in search box",
        "Test Data": "Query: 'Sandal'", "Expected Results": "List filters to only show profiles containing 'Sandal'.",
        "Post-Condition": "List filtered", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 19, "Test Case Scenario": "SKU Management", "Test Case": "Load Profile Parameters",
        "Pre-Conditions": "Profile selected", "Test Steps": "1. Click Select profile\n2. Navigate back to Live screen",
        "Test Data": "Profile: SANDAL-X-42", "Expected Results": "Live screen shows parameters (tolerance, size) from selected SKU.",
        "Post-Condition": "Parameters applied", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- ERROR HANDLING ---
    {
        "Test Case ID": 20, "Test Case Scenario": "Edge Case", "Test Case": "Handle Camera Removal",
        "Pre-Conditions": "Feed active", "Test Steps": "1. Unplug camera USB cable",
        "Test Data": "HW Disconnect", "Expected Results": "App remains stable. Shows error message or 'No Camera'. Thread terminates safely.",
        "Post-Condition": "App stable", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 21, "Test Case Scenario": "Edge Case", "Test Case": "Handle Database Offline",
        "Pre-Conditions": "DB Service stopped", "Test Steps": "1. Attempt to fetch SKUs",
        "Test Data": "Net Timeout", "Expected Results": "App shows 'Connection Failed' but doesn't crash. Falls back to local JSON cache.",
        "Post-Condition": "Fallback active", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    }
]

df = pd.DataFrame(data)

# Create a writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_Final.xlsx"
writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
df.to_excel(writer, index=False, sheet_name='SIT_Test_Cases')

# Formatting
workbook = writer.book
worksheet = writer.sheets['SIT_Test_Cases']

# Header format (Dark Blue / Cyan base as per screenshot)
header_format = workbook.add_format({
    'bold': True, 'bg_color': '#00334E', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
})

# Sub-header format for Passed/Failed
result_header_format = workbook.add_format({
    'bold': True, 'bg_color': '#00334E', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9
})

cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
})

# Adjust columns
widths = [5, 20, 25, 25, 45, 25, 35, 25, 20, 8, 8, 15, 20]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Write headers manually to handle the "Result" merge if needed (though keeping it simple for now)
# For the exact look, we follow the screenshot's columns
columns = df.columns.tolist()
for col_num, value in enumerate(columns):
    worksheet.write(0, col_num, value, header_format)

# Apply data format
for row in range(len(df)):
    for col in range(len(df.columns)):
        worksheet.write(row + 1, col, df.iloc[row, col], cell_format)

# Highlight some rows if needed (e.g. green ones from screenshot)
highlight_format = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1, 'text_wrap': True, 'valign': 'top'})
# Example: Highlight row 14 (Index 13) like in screenshot
# worksheet.set_row(14, None, highlight_format)

# Freeze panes
worksheet.freeze_panes(1, 0)

writer.close()
print(f"Final SIT document generated successfully at: {output_file}")
