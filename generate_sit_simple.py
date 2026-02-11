import pandas as pd

# Define simplified flow-based test cases (True/False)
data = [
    # --- 1. MEMBUKA APLIKASI ---
    {
        "ID": 1, "Scenario": "Buka Aplikasi (Sukses)", "Test Case": "Menjalankan aplikasi sampai masuk menu utama",
        "Pre-Condition": "Aplikasi siap", "Langkah": "1. Klik icon aplikasi / jalankan perintah start", "Data": "Normal",
        "Hasil": "Layar menu utama muncul dengan benar", "Post": "Siap digunakan", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 2, "Scenario": "Buka Aplikasi (Gagal)", "Test Case": "Menjalankan aplikasi saat database mati",
        "Pre-Condition": "Database tidak aktif", "Langkah": "1. Jalankan aplikasi", "Data": "DB Offline",
        "Hasil": "App tetap buka tapi ada peringatan koneksi gagal", "Post": "Mode terbatas", "P": "", "F": "", "Rem": "Skenario FALSE"
    },

    # --- 2. PILIH PRODUK (SKU) ---
    {
        "ID": 3, "Scenario": "Pilih Produk (Sukses)", "Test Case": "Mencari dan memilih tipe sandal",
        "Pre-Condition": "Di layar Manage Profiles", "Langkah": "1. Ketik nama sandal\n2. Klik Pilih", "Data": "Nama Sandal",
        "Hasil": "Nama sandal terpilih muncul di bagian atas", "Post": "Parameter terpasang", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 4, "Scenario": "Pilih Produk (Gagal)", "Test Case": "Mencari produk yang tidak ada di daftar",
        "Pre-Condition": "Di layar Manage Profiles", "Langkah": "1. Ketik nama asal-asalan", "Data": "xyz123",
        "Hasil": "Daftar kosong, tidak ada yang bisa dipilih", "Post": "Tetap di layar", "P": "", "F": "", "Rem": "Skenario FALSE"
    },

    # --- 3. MENJALANKAN KAMERA ---
    {
        "ID": 5, "Scenario": "Cek Kamera (Sukses)", "Test Case": "Menampilkan gambar dari kamera USB",
        "Pre-Condition": "Kamera terpasang", "Langkah": "1. Masuk ke menu Live Camera", "Data": "Kamera USB",
        "Hasil": "Video dari kamera muncul lancar", "Post": "Siap ukur", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 6, "Scenario": "Cek Kamera (Gagal)", "Test Case": "Kamera dicabut saat sedang digunakan",
        "Pre-Condition": "Video sedang tampil", "Langkah": "1. Cabut kabel kamera", "Data": "Cabut Kabel",
        "Hasil": "Gambar berhenti/macet dan muncul pesan error", "Post": "Kamera mati", "P": "", "F": "", "Rem": "Skenario FALSE"
    },

    # --- 4. DETEKSI & UKUR ---
    {
        "ID": 7, "Scenario": "Deteksi Sandal (Sukses)", "Test Case": "Mendeteksi sandal di posisi yang benar",
        "Pre-Condition": "Sandal di dalam kotak biru (ROI)", "Langkah": "1. Letakkan sandal dengan rapi", "Data": "Sandal Bersih",
        "Hasil": "Kotak deteksi muncul tepat di sekeliling sandal", "Post": "Hasil ukur tampil", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 8, "Scenario": "Deteksi Sandal (Gagal)", "Test Case": "Mencoba deteksi di tempat gelap",
        "Pre-Condition": "ROI dalam kondisi gelap", "Langkah": "1. Matikan lampu", "Data": "Minim Cahaya",
        "Hasil": "Sistem tidak bisa menemukan sandal", "Post": "Tidak ada kotak", "P": "", "F": "", "Rem": "Skenario FALSE"
    },

    # --- 5. SIMPAN HASIL ---
    {
        "ID": 9, "Scenario": "Simpan Foto (Sukses)", "Test Case": "Menyimpan foto hasil pengukuran",
        "Pre-Condition": "Hasil ukur sudah muncul", "Langkah": "1. Klik tombol Capture / Simpan", "Data": "Klik Simpan",
        "Hasil": "Muncul pesan 'Berhasil Simpan' dan file ada di folder", "Post": "Data tersimpan", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 10, "Scenario": "Simpan Foto (Gagal)", "Test Case": "Folder penyimpanan penuh atau tidak ada",
        "Pre-Condition": "Folder dihapus manual", "Langkah": "1. Klik Simpan", "Data": "Folder Hilang",
        "Hasil": "Muncul pesan 'Gagal Simpan'", "Post": "Data tidak hilang", "P": "", "F": "", "Rem": "Skenario FALSE"
    },

    # --- 6. TRIGGER OTOMATIS (PLC) ---
    {
        "ID": 11, "Scenario": "Foto Otomatis (Sukses)", "Test Case": "Trigger dari mesin (PLC) berfungsi",
        "Pre-Condition": "Mode otomatis ON", "Langkah": "1. Barang lewat di depan sensor", "Data": "Sinyal Mesin",
        "Hasil": "Aplikasi otomatis ambil foto tanpa diklik", "Post": "Foto tersimpan", "P": "", "F": "", "Rem": "Skenario TRUE"
    },
    {
        "ID": 12, "Scenario": "Foto Otomatis (Gagal)", "Test Case": "Mesin kirim sinyal tapi kabel serial lepas",
        "Pre-Condition": "Kabel PLC lepas", "Langkah": "1. Jalankan mesin", "Data": "Kabel Lepas",
        "Hasil": "Aplikasi tidak merespon (tidak ambil foto)", "Post": "Status PLC: OFF", "P": "", "F": "", "Rem": "Skenario FALSE"
    }
]

df = pd.DataFrame(data)

# Map to template headers
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

# Create writer
output_file = "/Users/porto-mac/Documents/GitHub/QC-Detector/SIT_QC_Detector_Alur_Simple.xlsx"
writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
final_df.to_excel(writer, index=False, sheet_name='SIT_Simple')

workbook = writer.book
worksheet = writer.sheets['SIT_Simple']

# Header Format
header_format = workbook.add_format({
    'bold': True, 'bg_color': '#00334E', 'font_color': 'white',
    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
})

# Row Formats
true_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#E8F5E9'})
false_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'font_size': 10, 'bg_color': '#FFEBEE'})

# Adjust columns
widths = [5, 20, 30, 25, 35, 20, 35, 20, 20, 8, 8, 15, 15]
for i, w in enumerate(widths):
    worksheet.set_column(i, i, w)

# Write headers
for col_num, value in enumerate(final_df.columns.values):
    worksheet.write(0, col_num, value, header_format)

# Write and Color rows
for idx, row_data in final_df.iterrows():
    fmt = true_format if "(Sukses)" in str(row_data["Test Case Scenario"]) else false_format
    for col_num, value in enumerate(row_data):
        worksheet.write(idx + 1, col_num, value, fmt)

worksheet.freeze_panes(1, 0)
writer.close()
print(f"Simplified flow SIT generated at: {output_file}")
