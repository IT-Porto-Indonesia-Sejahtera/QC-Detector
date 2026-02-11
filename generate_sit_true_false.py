import pandas as pd

# Define the data with True/False (Positive/Negative) scenarios
data = [
    # --- STARTUP & CONFIG (Positif/Negatif) ---
    {
        "Test Case ID": 1, "Test Case Scenario": "Startup Aplikasi (P)", "Test Case": "Verifikasi inisialisasi sistem sukses",
        "Pre-Conditions": "Aplikasi tertutup", "Test Steps": "1. Jalankan aplikasi",
        "Test Data": "Environment normal", "Expected Results": "Layar menu utama muncul dalam < 5 detik.",
        "Post-Condition": "Sistem siap", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 2, "Test Case Scenario": "Startup Aplikasi (N)", "Test Case": "Koneksi Database Gagal",
        "Pre-Conditions": "Layanan DB dimatikan", "Test Steps": "1. Jalankan aplikasi",
        "Test Data": "DB Offline", "Expected Results": "Aplikasi tetap terbuka tapi log menunjukkan 'Database connection failed'. Fitur SKU fallback ke lokal.",
        "Post-Condition": "Mode offline aktif", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 3, "Test Case Scenario": "Startup Aplikasi (N)", "Test Case": "File .env Hilang",
        "Pre-Conditions": "File .env dihapus/diganti nama", "Test Steps": "1. Jalankan aplikasi",
        "Test Data": "Missing .env", "Expected Results": "Aplikasi menggunakan nilai default. Log menunjukkan peringatan env tidak ditemukan.",
        "Post-Condition": "Sistem tetap berjalan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CAMERA & FEED (Positif/Negatif) ---
    {
        "Test Case ID": 4, "Test Case Scenario": "Kamera Feed (P)", "Test Case": "Koneksi Kamera USB Sukses",
        "Pre-Conditions": "Webcam terhubung", "Test Steps": "1. Pilih Index 0",
        "Test Data": "Device 0", "Expected Results": "Gambar muncul tanpa lag/delay.",
        "Post-Condition": "Live feed berjalan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 5, "Test Case Scenario": "Kamera Feed (N)", "Test Case": "IP Camera URL Salah",
        "Pre-Conditions": "URL RTSP salah/tidak valid", "Test Steps": "1. Pilih IP Camera",
        "Test Data": "rtsp://wrong_url", "Expected Results": "Feed tetap hitam. Log menunjukkan video capture timeout/error.",
        "Post-Condition": "Aplikasi tidak crash", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 6, "Test Case Scenario": "Kamera Feed (N)", "Test Case": "Kamera Dicabut Saat Berjalan",
        "Pre-Conditions": "Feed sedang aktif", "Test Steps": "1. Cabut kabel USB kamera",
        "Test Data": "Hardware removal", "Expected Results": "Thread kamera berhenti secara aman. Pesan error muncul di terminal.",
        "Post-Condition": "Sistem stabil", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- DETECTION & MODEL (Positif/Negatif) ---
    {
        "Test Case ID": 7, "Test Case Scenario": "Inference AI (P)", "Test Case": "Deteksi Sandal Normal",
        "Pre-Conditions": "Sandal di dalam ROI", "Test Steps": "1. Jalankan YOLO v8",
        "Test Data": "Objek bersih", "Expected Results": "Kotak deteksi menempel pada objek dengan presisi tinggi.",
        "Post-Condition": "Deteksi berhasil", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 8, "Test Case Scenario": "Inference AI (N)", "Test Case": "ROI Kosong (Tanpa Objek)",
        "Pre-Conditions": "Tidak ada benda di ROI", "Test Steps": "1. Jalankan YOLO v8",
        "Test Data": "Meja kosong", "Expected Results": "Sistem tidak menampilkan kotak deteksi (No detection).",
        "Post-Condition": "Hasil nol", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 9, "Test Case Scenario": "Inference AI (N)", "Test Case": "Objek Terhalang (Occlusion)",
        "Pre-Conditions": "Sandal ditutupi sebagian oleh tangan", "Test Steps": "1. Jalankan YOLO v8",
        "Test Data": "50% terhalang", "Expected Results": "Sistem tetap mendeteksi bagian yang terlihat atau memberikan label confidence rendah.",
        "Post-Condition": "Deteksi parsial", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CALIBRATION (Positif/Negatif/Edge) ---
    {
        "Test Case ID": 10, "Test Case Scenario": "Kalibrasi (P)", "Test Case": "Update Rasio Valid",
        "Pre-Conditions": "Akses Settings", "Test Steps": "1. Input nilai 0.150",
        "Test Data": "Float valid", "Expected Results": "Output ukuran (mm) terupdate seketika.",
        "Post-Condition": "Akurat", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 11, "Test Case Scenario": "Kalibrasi (N)", "Test Case": "Input Nilai Nol/Negatif",
        "Pre-Conditions": "Akses Settings", "Test Steps": "1. Input 0 atau -1.0",
        "Test Data": "Invalid input", "Expected Results": "Aplikasi mengabaikan input atau kembali ke nilai sebelumnya agar tidak terjadi pembagian dengan nol.",
        "Post-Condition": "Sistem proteksi", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 12, "Test Case Scenario": "Kalibrasi (Edge)", "Test Case": "ArUco Marker Terpotong",
        "Pre-Conditions": "Marker diletakkan di pinggir ROI", "Test Steps": "1. Klik Deteksi ArUco",
        "Test Data": "Marker 75% masuk", "Expected Results": "Jika marker tidak utuh, sistem memberikan pesan 'Marker not found'.",
        "Post-Condition": "Gagal deteksi tenang", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CAPTURE & DATASET (Positif/Negatif) ---
    {
        "Test Case ID": 13, "Test Case Scenario": "Dataset (P)", "Test Case": "Capture Sukses (Disk Aman)",
        "Pre-Conditions": "Ruang disk cukup", "Test Steps": "1. Klik Manual Capture",
        "Test Data": "Internal Disk", "Expected Results": "File tersimpan dengan nama unik di folder dataset.",
        "Post-Condition": "Data tersimpan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 14, "Test Case Scenario": "Dataset (N)", "Test Case": "Folder Tujuan Tidak Ada / Read Only",
        "Pre-Conditions": "Path folder dihapus manual", "Test Steps": "1. Klik Manual Capture",
        "Test Data": "Invalid Path", "Expected Results": "Sistem secara otomatis membuat folder atau memberikan peringatan 'Save Failed'.",
        "Post-Condition": "Tidak ada file tersimpan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- PLC MODBUS (Positif/Negatif/Edge) ---
    {
        "Test Case ID": 15, "Test Case Scenario": "PLC Integration (P)", "Test Case": "Koneksi RTU Stabil",
        "Pre-Conditions": "PLC terhubung", "Test Steps": "1. Start Modbus Client",
        "Test Data": "COM/Baudrate OK", "Expected Results": "Heartbeat/polling berjalan lancar (Label hijau).",
        "Post-Condition": "Polling aktif", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 16, "Test Case Scenario": "PLC Integration (N)", "Test Case": "Port Serial Salah (In Use)",
        "Pre-Conditions": "Port dipakai aplikasi lain (misal: Arduino IDE)", "Test Steps": "1. Start Modbus Client",
        "Test Data": "Port Sibuk", "Expected Results": "Muncul pesan 'Permission denied' atau 'Access denied' di terminal/top bar.",
        "Post-Condition": "Koneksi ditolak", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 17, "Test Case Scenario": "PLC Integration (Edge)", "Test Case": "Sinyal Trigger Terlalu Cepat (Noise)",
        "Pre-Conditions": "Value berubah 0-1-0 dalam < 50ms", "Test Steps": "1. Simulasi pulse cepat di register",
        "Test Data": "Pulse 50ms", "Expected Results": "Sistem mungkin tidak menangkap trigger (tergantung poll interval 100ms) atau menangkap sekali dengan benar (de-bounce effect).",
        "Post-Condition": "Capture tunggal", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- SKU & SCHEDULER (Positif/Negatif) ---
    {
        "Test Case ID": 18, "Test Case Scenario": "Manajemen SKU (P)", "Test Case": "Sync Data Berhasil",
        "Pre-Conditions": "Internet stabil", "Test Steps": "1. Jalankan scheduler sync",
        "Test Data": "Network OK", "Expected Results": "skus.json diperbarui dengan timestamp terbaru.",
        "Post-Condition": "Data terbaru tersimpan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 19, "Test Case Scenario": "Manajemen SKU (N)", "Test Case": "No Internet (Sync Gagal)",
        "Pre-Conditions": "Koneksi internet diputus", "Test Steps": "1. Tunggu waktu interval sync",
        "Test Data": "Offline", "Expected Results": "Aplikasi tetap berjalan menggunakan skus.json lama yang tersimpan di disk.",
        "Post-Condition": "Menggunakan cache", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- EDGE CASES (UMUM) ---
    {
        "Test Case ID": 20, "Test Case Scenario": "Resilience", "Test Case": "Rapid Clicks (Double Trigger)",
        "Pre-Conditions": "Layar utama", "Test Steps": "1. Klik tombol 'Measure Live' berkali-kali sangat cepat",
        "Test Data": "Stress Click", "Expected Results": "Aplikasi hanya membuka satu instance layar dan tidak hang/lag.",
        "Post-Condition": "UI Stabil", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 21, "Test Case Scenario": "Resilience", "Test Case": "Maximize/Minimize Saat Loading",
        "Pre-Conditions": "Saat model AI sedang diload (awal)", "Test Steps": "1. Ubah ukuran jendela jendela",
        "Test Data": "Window resize", "Expected Results": "Aplikasi tetap merender frame kamera dengan proporsi yang benar.",
        "Post-Condition": "Scaling normal", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    }
]

df = pd.DataFrame(data)

# Create a writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_Final_TrueFalse.xlsx"
writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
df.to_excel(writer, index=False, sheet_name='SIT_True_False')

workbook = writer.book
worksheet = writer.sheets['SIT_True_False']

# Header format (Dark Blue / Cyan base as per screenshot)
header_format = workbook.add_format({
    'bold': True, 'bg_color': '#00334E', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
})

cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
})

# Format for Negatif Scenarios (Optional highlight - light red)
negative_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#FFEBEE'
})

# Adjust columns
widths = [5, 20, 25, 25, 45, 25, 35, 25, 20, 8, 8, 15, 20]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Write headers
for col_num, value in enumerate(df.columns.values):
    worksheet.write(0, col_num, value, header_format)

# Apply data format
for row_idx, row_data in df.iterrows():
    # Detect if it's a negative scenario to apply different format
    scenario_text = str(row_data["Test Case Scenario"])
    active_format = negative_format if "(N)" in scenario_text else cell_format
    
    for col_num, value in enumerate(row_data):
        worksheet.write(row_idx + 1, col_num, value, active_format)

# Freeze panes
worksheet.freeze_panes(1, 0)

writer.close()
print(f"True/False SIT document generated successfully at: {output_file}")
