import pandas as pd

# Define the exhaustive list of test cases
data = [
    # --- 1. STARTUP & INITIALIZATION ---
    {
        "ID": 1, "Scenario": "Startup - Positif", "Test Case": "Menjalankan aplikasi dengan env lengkap",
        "Pre-Condition": "Sistem siap", "Langkah": "1. Run main.py", "Data": ".env benar",
        "Hasil": "App terbuka normal", "Post": "Main Menu", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 2, "Scenario": "Startup - Negatif", "Test Case": "Menjalankan aplikasi tanpa .env",
        "Pre-Condition": "File .env dihapus", "Langkah": "1. Run main.py", "Data": "No .env",
        "Hasil": "App tetap buka (default)", "Post": "Warning Log", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 3, "Scenario": "Startup - Edge", "Test Case": "Versi Python tidak kompatibel",
        "Pre-Condition": "Python 2.x", "Langkah": "1. Run main.py", "Data": "Python 2",
        "Hasil": "Error syntax / exit", "Post": "Terminated", "P": "", "F": "", "Rem": ""
    },

    # --- 2. DATABASE ---
    {
        "ID": 4, "Scenario": "DB - Positif", "Test Case": "Koneksi Postgre Sukses",
        "Pre-Condition": "Service On", "Langkah": "1. Cek log startup", "Data": "Creds OK",
        "Hasil": "DB Pool Init Sukses", "Post": "DB State: Active", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 5, "Scenario": "DB - Negatif", "Test Case": "Koneksi Postgre Gagal (Wrong Pass)",
        "Pre-Condition": "Pass .env salah", "Langkah": "1. Cek log startup", "Data": "Wrong Pass",
        "Hasil": "OperationalError logged", "Post": "DB State: Failed", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 6, "Scenario": "DB - Edge", "Test Case": "DB Terputus saat Runtime",
        "Pre-Condition": "Service dimatikan paksa", "Langkah": "1. Coba klik refresh SKU", "Data": "Runtime disconnect",
        "Hasil": "Error ditangkap (psycopg2)", "Post": "Graceful failure", "P": "", "F": "", "Rem": ""
    },

    # --- 3. NAVIGATION ---
    {
        "ID": 7, "Scenario": "Nav - Positif", "Test Case": "Akses layar Live",
        "Pre-Condition": "Menu Utama", "Langkah": "1. Klik 'Measure Live'", "Data": "Click",
        "Hasil": "Pindah ke Live Screen", "Post": "Live Screen", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 8, "Scenario": "Nav - Negatif", "Test Case": "Klik berulang sangat cepat",
        "Pre-Condition": "Menu Utama", "Langkah": "1. Spam klik tombol 10x", "Data": "Rapid",
        "Hasil": "Hanya buka 1 instance", "Post": "Stable", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 9, "Scenario": "Nav - Edge", "Test Case": "Pindah layar saat model sedang loading",
        "Pre-Condition": "AI Loading", "Langkah": "1. Klik tombol pindah layar", "Data": "Mid-load",
        "Hasil": "Menyelesaikan load / Terminate aman", "Post": "Layar tujuan", "P": "", "F": "", "Rem": ""
    },

    # --- 4. CAMERA FEED ---
    {
        "ID": 10, "Scenario": "Cam - Positif", "Test Case": "Init Kamera USB",
        "Pre-Condition": "USB Plugged", "Langkah": "1. Pilih Index 0", "Data": "ID 0",
        "Hasil": "Feed muncul lancar", "Post": "Streaming", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 11, "Scenario": "Cam - Negatif", "Test Case": "Pilih Index kamera gaib",
        "Pre-Condition": "Hanya ada 1 cam", "Langkah": "1. Masukkan Index 99", "Data": "ID 99",
        "Hasil": "Feed hitam / Pesan error", "Post": "No Feed", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 12, "Scenario": "Cam - Edge", "Test Case": "Kamera dicabut saat streaming",
        "Pre-Condition": "Streaming aktif", "Langkah": "1. Cabut kabel USB", "Data": "HW Removal",
        "Hasil": "Log: Camera Lost. App OK", "Post": "No Feed", "P": "", "F": "", "Rem": ""
    },

    # --- 5. IP CAMERA ---
    {
        "ID": 13, "Scenario": "IPCam - Positif", "Test Case": "Init RTSP Stream",
        "Pre-Condition": "IP Cam configured", "Langkah": "1. Pilih IP Camera", "Data": "RTSP Valid",
        "Hasil": "Feed IP Cam muncul", "Post": "Streaming", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 14, "Scenario": "IPCam - Negatif", "Test Case": "RTSP URL Salah/Mati",
        "Pre-Condition": "URL Invalid", "Langkah": "1. Pilih IP Camera", "Data": "Wrong RTSP",
        "Hasil": "Timeout / Frame hitam", "Post": "Retry loop", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 15, "Scenario": "IPCam - Edge", "Test Case": "Bandwidth limit (Laggy)",
        "Pre-Condition": "Network lemot", "Langkah": "1. Jalankan stream", "Data": "Slow Net",
        "Hasil": "App tetap jalan (FPS drop)", "Post": "Laggy feed", "P": "", "F": "", "Rem": ""
    },

    # --- 6. AI INFERENCE (YOLO) ---
    {
        "ID": 16, "Scenario": "YOLO - Positif", "Test Case": "Deteksi Sandal Terang",
        "Pre-Condition": "Lampu terang", "Langkah": "1. Sandal di ROI", "Data": "YOLO v8",
        "Hasil": "Bbox akurat (Confidence > 0.8)", "Post": "Detected", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 17, "Scenario": "YOLO - Negatif", "Test Case": "Deteksi di tempat gelap gulita",
        "Pre-Condition": "Lampu mati", "Langkah": "1. Sandal di ROI", "Data": "Dark",
        "Hasil": "Tidak deteksi (No Bbox)", "Post": "No Output", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 18, "Scenario": "YOLO - Edge", "Test Case": "Sandal Terpotong ROI",
        "Pre-Condition": "Sandal di pinggir", "Langkah": "1. Letakkan separuh sandal", "Data": "Partial",
        "Hasil": "Deteksi bagian yang ada", "Post": "Partial Bbox", "P": "", "F": "", "Rem": ""
    },

    # --- 7. AI INFERENCE (FASTSAM) ---
    {
        "ID": 19, "Scenario": "SAM - Positif", "Test Case": "Segmentasi Detail",
        "Pre-Condition": "SAM Selected", "Langkah": "1. Sandal di ROI", "Data": "FastSAM",
        "Hasil": "Mask menutupi sandal pas", "Post": "Mask Overlay", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 20, "Scenario": "SAM - Negatif", "Test Case": "Banyak kebisingan visual",
        "Pre-Condition": "Background berantakan", "Langkah": "1. Sandal di ROI", "Data": "Noisy BG",
        "Hasil": "Mask bocor ke BG", "Post": "Incorrect Mask", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 21, "Scenario": "SAM - Edge", "Test Case": "Objek bertumpuk",
        "Pre-Condition": "2 sandal tumpuk", "Langkah": "1. Cek segmentasi", "Data": "Overlap",
        "Hasil": "Hanya deteksi 1 / gabung", "Post": "Unclear mask", "P": "", "F": "", "Rem": ""
    },

    # --- 8. CALIBRATION ---
    {
        "ID": 22, "Scenario": "Calib - Positif", "Test Case": "Update mm/px Normal",
        "Pre-Condition": "Input valid", "Langkah": "1. Masukkan 0.25", "Data": "0.25",
        "Hasil": "Ukuran mm berubah benar", "Post": "Saved", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 23, "Scenario": "Calib - Negatif", "Test Case": "Input data non-angka",
        "Pre-Condition": "Input String", "Langkah": "1. Masukkan 'abc'", "Data": "'abc'",
        "Hasil": "Sistem tolak / Reset ke lama", "Post": "Safe", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 24, "Scenario": "Calib - Edge", "Test Case": "Input angka sangat kecil",
        "Pre-Condition": "Zero limit", "Langkah": "1. Masukkan 0.0000001", "Data": "Tiny Float",
        "Hasil": "Aplikasi tetap hitung (Float64)", "Post": "Precise", "P": "", "F": "", "Rem": ""
    },

    # --- 9. ARUCO ---
    {
        "ID": 25, "Scenario": "Aruco - Positif", "Test Case": "Deteksi ArUco jelas",
        "Pre-Condition": "Marker depan", "Langkah": "1. Klik Calibrate Aruco", "Data": "ID 0",
        "Hasil": "mm/px hitung otomatis", "Post": "Calibrated", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 26, "Scenario": "Aruco - Negatif", "Test Case": "Marker terbalik / kotor",
        "Pre-Condition": "Marker rusak", "Langkah": "1. Klik Calibrate Aruco", "Data": "Dirty Marker",
        "Hasil": "Gagal deteksi / Pesan error", "Post": "No Update", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 27, "Scenario": "Aruco - Edge", "Test Case": "Batch banyak marker",
        "Pre-Condition": "Ada 8 marker", "Langkah": "1. Jalankan deteksi", "Data": "8 Markers",
        "Hasil": "Hitung rata-rata mm/px", "Post": "Calibrated", "P": "", "F": "", "Rem": ""
    },

    # --- 10. CAPTURE ---
    {
        "ID": 28, "Scenario": "Capt - Positif", "Test Case": "Manual Save",
        "Pre-Condition": "Folder Ready", "Langkah": "1. Klik Capture", "Data": "Click",
        "Hasil": "File tersimpan di disk", "Post": "JPG exists", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 29, "Scenario": "Capt - Negatif", "Test Case": "Disk Penuh",
        "Pre-Condition": "Disk 0 bytes", "Langkah": "1. Klik Capture", "Data": "Full Disk",
        "Hasil": "Log: Write Failed (OSError)", "Post": "No file", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 30, "Scenario": "Capt - Edge", "Test Case": "Capture saat kamera macet",
        "Pre-Condition": "Freeze frame", "Langkah": "1. Klik Capture", "Data": "Freeze",
        "Hasil": "Simpan frame terakhir", "Post": "Static JPG", "P": "", "F": "", "Rem": ""
    },

    # --- 11. CONSISTENCY TEST ---
    {
        "ID": 31, "Scenario": "Consist - Positif", "Test Case": "Tes 100x Tanpa Putus",
        "Pre-Condition": "Normal setup", "Langkah": "1. Jalankan test 100x", "Data": "N=100",
        "Hasil": "Selesai 100% tanpa crash", "Post": "Report ready", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 32, "Scenario": "Consist - Negatif", "Test Case": "Input jumlah < minimum",
        "Pre-Condition": "Limit test", "Langkah": "1. Masukkan -5", "Data": "N=-5",
        "Hasil": "Divalidasi ke default (10)", "Post": "Safe run", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 33, "Scenario": "Consist - Edge", "Test Case": "Kamera putus di tengah tes",
        "Pre-Condition": "Kamera lepas di ke-50", "Langkah": "1. Biarkan jalan", "Data": "Mid-Test Disconnect",
        "Hasil": "Test stop / Log error", "Post": "Partial Result", "P": "", "F": "", "Rem": ""
    },

    # --- 12. PLC MODBUS ---
    {
        "ID": 34, "Scenario": "PLC - Positif", "Test Case": "Koneksi Serial Stabil",
        "Pre-Condition": "HW Ready", "Langkah": "1. Start PLC", "Data": "COM3",
        "Hasil": "Label: Connected", "Post": "Polling active", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 35, "Scenario": "PLC - Negatif", "Test Case": "Port serial salah / dipakai",
        "Pre-Condition": "Port closed", "Langkah": "1. Start PLC", "Data": "Wrong COM",
        "Hasil": "Log: Connection Refused", "Post": "State: Red", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 36, "Scenario": "PLC - Edge", "Test Case": "Trigger 1 terus-menerus",
        "Pre-Condition": "Sinyal nyangkut", "Langkah": "1. Biarkan 1 terus", "Data": "Value 1",
        "Hasil": "Hanya capture 1x (Rising Only)", "Post": "No Multi-Fire", "P": "", "F": "", "Rem": ""
    },

    # --- 13. SKU & SCHEDULER ---
    {
        "ID": 37, "Scenario": "SKU - Positif", "Test Case": "Search SKU Valid",
        "Pre-Condition": "JSON Loaded", "Langkah": "1. Ketik sandal", "Data": "'sandal'",
        "Hasil": "List terfilter", "Post": "Filtered UI", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 38, "Scenario": "SKU - Negatif", "Test Case": "Search gaib",
        "Pre-Condition": "JSON Loaded", "Langkah": "1. Ketik 'xyz123'", "Data": "'xyz123'",
        "Hasil": "List kosong", "Post": "Empty UI", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 39, "Scenario": "SKU - Edge", "Test Case": "Scheduler jalan saat sync",
        "Pre-Condition": "Sync sedang aktif", "Langkah": "1. Tunggu timer berikutnya", "Data": "Double Timer",
        "Hasil": "Skip jika masih running", "Post": "Singleton execution", "P": "", "F": "", "Rem": ""
    },

    # --- 14. UI RESILIENCE ---
    {
        "ID": 40, "Scenario": "UI - Positif", "Test Case": "Resize Jendela",
        "Pre-Condition": "Live Feed", "Langkah": "1. Tarik sudut window", "Data": "Drag",
        "Hasil": "Element tertata ulang", "Post": "Responsive", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 41, "Scenario": "UI - Negatif", "Test Case": "Minimize saat capture",
        "Pre-Condition": "Mid-capture", "Langkah": "1. Klik minimize", "Data": "Minimize",
        "Hasil": "Proses background lanjut", "Post": "Task Complete", "P": "", "F": "", "Rem": ""
    },
    {
        "ID": 42, "Scenario": "UI - Edge", "Test Case": "Ganti Tema (Dark/Light)",
        "Pre-Condition": "Akses theme settings", "Langkah": "1. Klik toggle tema", "Data": "Mode change",
        "Hasil": "Warna update tanpa crash", "Post": "Updated Theme", "P": "", "F": "", "Rem": ""
    }
]

df = pd.DataFrame(data)

# Map columns to the requested template headers
template_data = []
for item in data:
    row = {
        "Test Case ID": item["ID"],
        "Test Case Scenario": item["Scenario"],
        "Test Case": item["Test Case"],
        "Pre-Conditions": item["Pre-Condition"],
        "Test Steps": item["Langkah"],
        "Test Data": item["Data"],
        "Expected Results": item["Hasil"],
        "Post-Condition": item["Post"],
        "Actual Results": "",
        "Passed": item["P"],
        "Failed": item["F"],
        "Remarks": item["Rem"],
        "Dokumentasi": ""
    }
    template_data.append(row)

final_df = pd.DataFrame(template_data)

# Create a writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_EXHAUSTIVE.xlsx"
writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
final_df.to_excel(writer, index=False, sheet_name='SIT_Exhaustive')

# Formatting
workbook = writer.book
worksheet = writer.sheets['SIT_Exhaustive']

# Header format
header_format = workbook.add_format({
    'bold': True, 'bg_color': '#00334E', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
})

cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
})

# Color formats for rows
pos_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#E8F5E9'})
neg_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#FFEBEE'})
edge_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#FFF3E0'})

# Adjust columns
widths = [5, 20, 30, 25, 45, 25, 35, 25, 20, 8, 8, 15, 20]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Write headers
for col_num, value in enumerate(final_df.columns.values):
    worksheet.write(0, col_num, value, header_format)

# Apply and color data
for row_idx, row_data in final_df.iterrows():
    scenario = str(row_data["Test Case Scenario"])
    if "Positif" in scenario:
        fmt = pos_format
    elif "Negatif" in scenario:
        fmt = neg_format
    else: # Edge
        fmt = edge_format
        
    for col_num, value in enumerate(row_data):
        worksheet.write(row_idx + 1, col_num, value, fmt)

# Freeze panes
worksheet.freeze_panes(1, 0)

writer.close()
print(f"Exhaustive SIT document generated at: {output_file}")
