import pandas as pd
import os
import math

print("--- MEMECAH FILE RAKSASA MENJADI KECIL ---")

# Konfigurasi
input_file = 'sppt_ready.csv'
output_folder = 'data_chunks' # Kita taruh di folder khusus biar rapi
max_rows_per_file = 200000 # Sekitar 200rb baris per file (aman < 25MB)

if not os.path.exists(input_file):
    print(f"Error: File {input_file} tidak ditemukan.")
    exit()

# Buat folder output
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Baca file
print("Membaca file besar (mohon tunggu)...")
df = pd.read_csv(input_file, low_memory=False)
total_rows = len(df)
print(f"Total Baris: {total_rows:,}")

# Hitung jumlah pecahan
num_chunks = math.ceil(total_rows / max_rows_per_file)
print(f"Akan dipecah menjadi {num_chunks} file kecil...")

# Proses Pemecahan
for i in range(num_chunks):
    start_idx = i * max_rows_per_file
    end_idx = min((i + 1) * max_rows_per_file, total_rows)
    
    # Ambil potongan data
    chunk = df.iloc[start_idx:end_idx]
    
    # Nama file: data_part_01.csv, data_part_02.csv, dst
    filename = f"data_part_{i+1:02d}.csv"
    filepath = os.path.join(output_folder, filename)
    
    chunk.to_csv(filepath, index=False)
    print(f"   -> Tersimpan: {filename} ({len(chunk):,} baris)")

print("\n[SELESAI] Semua file tersimpan di folder 'data_chunks'.")
print("HAPUS file 'sppt_ready.csv' dan 'sppt_ready.csv.zip' sekarang agar tidak berat!")