import pandas as pd

# Define the data in Indonesian based on the exact screenshot format
data = [
    # --- STARTUP ---
    {
        "Test Case ID": 1, "Test Case Scenario": "Startup Aplikasi", "Test Case": "Verifikasi inisialisasi sistem",
        "Pre-Conditions": "Aplikasi tertutup", "Test Steps": "1. Jalankan main.py atau start_app.command",
        "Test Data": "OS: macOS/Windows", "Expected Results": "Aplikasi terbuka tanpa error. Menu utama muncul.",
        "Post-Condition": "Berada di Main Menu", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 2, "Test Case Scenario": "Startup Aplikasi", "Test Case": "Verifikasi Koneksi Database",
        "Pre-Conditions": "Layanan PostgreSQL berjalan", "Test Steps": "1. Perhatikan terminal log saat startup",
        "Test Data": "Konfigurasi .env", "Expected Results": "Log menunjukkan '[DB] Database connection pool initialized'",
        "Post-Condition": "DB terhubung", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 3, "Test Case Scenario": "Startup Aplikasi", "Test Case": "Verifikasi AI Model Warmup",
        "Pre-Conditions": "Aplikasi sedang memulai", "Test Steps": "1. Tunggu 5-10 detik",
        "Test Data": "YOLO/SAM weights", "Expected Results": "Log menunjukkan '[Startup] Background AI model warmup started'",
        "Post-Condition": "Model siap di memori", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- NAVIGATION ---
    {
        "Test Case ID": 4, "Test Case Scenario": "Navigasi", "Test Case": "Pindah antar layar/screen",
        "Pre-Conditions": "Di Main Menu", "Test Steps": "1. Klik semua tombol (Live, Photo, Dataset, Settings)",
        "Test Data": "N/A", "Expected Results": "Sistem berpindah ke layar tujuan dan tombol back berfungsi dengan baik.",
        "Post-Condition": "Kembali ke Menu dengan sukses", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CAMERA & DETECTION ---
    {
        "Test Case ID": 5, "Test Case Scenario": "Kamera Feed", "Test Case": "Inisialisasi Kamera Index 0",
        "Pre-Conditions": "Kamera USB terhubung", "Test Steps": "1. Masuk ke Live Camera\n2. Pilih Index 0",
        "Test Data": "Kamera 0", "Expected Results": "Live feed muncul dengan jelas di placeholder.",
        "Post-Condition": "Feed berjalan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 6, "Test Case Scenario": "Kamera Feed", "Test Case": "Inisialisasi IP Camera",
        "Pre-Conditions": "URL IP Camera terkonfigurasi di app_settings.json", "Test Steps": "1. Masuk ke Live Camera\n2. Pilih IP Camera",
        "Test Data": "rtsp://admin:pass@ip:554", "Expected Results": "RTSP stream terbuka dan menampilkan feed.",
        "Post-Condition": "Network stream aktif", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 7, "Test Case Scenario": "Inference AI", "Test Case": "Deteksi YOLO v8",
        "Pre-Conditions": "Feed berjalan, Sandal berada di ROI", "Test Steps": "1. Pilih YOLO v8 dari selector Model",
        "Test Data": "Objek: Sandal", "Expected Results": "Bounding box muncul di sekitar sandal dengan label 'sandal'.",
        "Post-Condition": "Bounding box terlihat", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 8, "Test Case Scenario": "Inference AI", "Test Case": "Segmentasi FastSAM",
        "Pre-Conditions": "Feed berjalan, Sandal berada di ROI", "Test Steps": "1. Pilih FastSAM dari selector Model",
        "Test Data": "Objek: Sandal", "Expected Results": "Overlay mask transparan muncul menutupi area sandal dengan presisi.",
        "Post-Condition": "Mask terlihat", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- CALIBRATION ---
    {
        "Test Case ID": 9, "Test Case Scenario": "Kalibrasi", "Test Case": "Update Manual mm/px",
        "Pre-Conditions": "Layar Settings terbuka", "Test Steps": "1. Input nilai 0.231 secara manual\n2. Simpan",
        "Test Data": "Nilai: 0.231", "Expected Results": "Pengukuran di layar live berubah berdasarkan rasio baru.",
        "Post-Condition": "Rasio terupdate di memori", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 10, "Test Case Scenario": "Kalibrasi", "Test Case": "Deteksi ArUco untuk mm/px",
        "Pre-Conditions": "Kertas kalibrasi diletakkan di bawah kamera", "Test Steps": "1. Klik 'Detect ArUco'\n2. Perhatikan kalkulasi mm/px",
        "Test Data": "ArUco Marker ID 0", "Expected Results": "Sistem mendeteksi marker dan mengkalkulasi mm/px secara otomatis.",
        "Post-Condition": "Rasio terkalibrasi", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 11, "Test Case Scenario": "Distorsi Lensa", "Test Case": "Toggle Undistort Map",
        "Pre-Conditions": "Layar Settings terbuka", "Test Steps": "1. Aktifkan 'Enable Undistort'\n2. Klik Simpan",
        "Test Data": "Parameter Matrix", "Expected Results": "Pinggiran gambar live menjadi lurus. Tidak ada penurunan FPS yang signifikan.",
        "Post-Condition": "Transformasi gambar diterapkan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- DATASET CAPTURE ---
    {
        "Test Case ID": 12, "Test Case Scenario": "Manual Capture", "Test Case": "Simpan Gambar Raw",
        "Pre-Conditions": "Layar Dataset terbuka, feed aktif", "Test Steps": "1. Klik Capture Image (Manual)",
        "Test Data": "Folder: output/dataset", "Expected Results": "File .jpg baru tercipta di folder yang ditentukan.",
        "Post-Condition": "File ada di disk", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 13, "Test Case Scenario": "Manual Capture", "Test Case": "Simpan dengan Overlay",
        "Pre-Conditions": "'Save Measurement Overlay' tercentang", "Test Steps": "1. Klik Capture Image (Manual)",
        "Test Data": "Output: measured_xxx.jpg", "Expected Results": "Gambar yang disimpan berisi kotak biru dan teks pengukuran.",
        "Post-Condition": "Gambar overlay tersimpan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 14, "Test Case Scenario": "Konsistensi", "Test Case": "Tes Otomatis 100-frame",
        "Pre-Conditions": "Sandal diletakkan secara statis", "Test Steps": "1. Klik Test Consistency\n2. Set jumlah percobaan: 100",
        "Test Data": "N: 100", "Expected Results": "Proses berjalan hingga selesai. Progress bar terupdate dengan benar.",
        "Post-Condition": "Tes selesai", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 15, "Test Case Scenario": "Konsistensi", "Test Case": "Export ke Excel",
        "Pre-Conditions": "Tes konsistensi selesai", "Test Steps": "1. Verifikasi keberadaan file .xlsx di folder output",
        "Test Data": "Filename: consist_test_xxx.xlsx", "Expected Results": "File Excel terbuka dengan baris data pengukuran yang valid.",
        "Post-Condition": "Laporan data siap", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- PLC INTEGRATION ---
    {
        "Test Case ID": 16, "Test Case Scenario": "Koneksi PLC", "Test Case": "Verifikasi Inisialisasi Modbus RTU",
        "Pre-Conditions": "Kabel serial PLC terhubung", "Test Steps": "1. Konfigurasi COM Port di settings\n2. Klik Start PLC",
        "Test Data": "COM3, 9600, E81", "Expected Results": "Indikator menunjukkan 'PLC: Connected'. Label status di atas berwarna hijau.",
        "Post-Condition": "Polling thread aktif", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 17, "Test Case Scenario": "Trigger PLC", "Test Case": "Automatic Capture via Rising Edge",
        "Pre-Conditions": "PLC terhubung, trigger aktif", "Test Steps": "1. Ubah nilai PLC 0 -> 1",
        "Test Data": "Register 12", "Expected Results": "Sistem mengabaikan nilai 0, lalu mengambil gambar segera saat menjadi 1.",
        "Post-Condition": "Event pengambilan tunggal", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- SKU & PROFILE ---
    {
        "Test Case ID": 18, "Test Case Scenario": "Manajemen SKU", "Test Case": "Cari SKU berdasarkan Keyword",
        "Pre-Conditions": "Halaman Profiles terbuka", "Test Steps": "1. Masukkan 'Sandal' di kotak pencarian",
        "Test Data": "Query: 'Sandal'", "Expected Results": "Daftar terfilter hanya menampilkan profil yang mengandung kata 'Sandal'.",
        "Post-Condition": "Daftar terfilter", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 19, "Test Case Scenario": "Manajemen SKU", "Test Case": "Load Parameter Profil",
        "Pre-Conditions": "Profil terpilih", "Test Steps": "1. Klik Select profile\n2. Kembali ke layar Live",
        "Test Data": "Profile: SANDAL-X-42", "Expected Results": "Layar Live menampilkan parameter (toleransi, ukuran) dari SKU terpilih.",
        "Post-Condition": "Parameter diterapkan", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },

    # --- ERROR HANDLING ---
    {
        "Test Case ID": 20, "Test Case Scenario": "Kasus Khusus", "Test Case": "Menangani Pencabutan Kamera",
        "Pre-Conditions": "Feed aktif", "Test Steps": "1. Cabut kabel USB kamera",
        "Test Data": "HW Disconnect", "Expected Results": "Aplikasi tetap stabil. Muncul pesan error atau 'No Camera'. Thread berhenti dengan aman.",
        "Post-Condition": "App stabil", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    },
    {
        "Test Case ID": 21, "Test Case Scenario": "Kasus Khusus", "Test Case": "Menangani Database Offline",
        "Pre-Conditions": "Layanan DB dimatikan", "Test Steps": "1. Coba ambil data SKU",
        "Test Data": "Net Timeout", "Expected Results": "Aplikasi menunjukkan 'Connection Failed' tapi tidak crash. Menggunakan cache JSON lokal.",
        "Post-Condition": "Fallback aktif", "Actual Results": "", "Passed": "", "Failed": "", "Remarks": "", "Dokumentasi": ""
    }
]

df = pd.DataFrame(data)

# Create a writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_Final_ID.xlsx"
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

cell_format = workbook.add_format({
    'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10
})

# Adjust columns
widths = [5, 20, 25, 25, 45, 25, 35, 25, 20, 8, 8, 15, 20]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Write headers
columns = df.columns.tolist()
for col_num, value in enumerate(columns):
    worksheet.write(0, col_num, value, header_format)

# Apply data format
for row in range(len(df)):
    for col in range(len(df.columns)):
        worksheet.write(row + 1, col, df.iloc[row, col], cell_format)

# Freeze panes
worksheet.freeze_panes(1, 0)

writer.close()
print(f"Bahasa Indonesia SIT document generated successfully at: {output_file}")
