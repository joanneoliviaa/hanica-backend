"""
Menjalankan semua script Tabel 4.5 sampai Tabel 4.16, Gambar 4.1, dan Gambar 4.2 sekaligus.
Jalankan dari folder Aplikasi (venv aktif, PostgreSQL menyala):
    python "Pengujian Bab 4/jalankan_semua.py"
Setiap PDF tersimpan di subfolder tabel/gambarnya masing-masing.
Bisa juga hanya sebagian, misalnya:  python "Pengujian Bab 4/jalankan_semua.py" "Tabel 4.7" "Gambar 4.2"
"""
import subprocess
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
DAFTAR = [f"Tabel 4.{n}" for n in range(5, 17)] + ["Gambar 4.1", "Gambar 4.2"]
pilihan = sys.argv[1:] or DAFTAR

gagal = []
for nomor in pilihan:
    if nomor[0].isdigit():         
        nomor = f"Tabel {nomor}"
    jenis, angka = nomor.split(" ")
    script = SINI / nomor / f"{jenis.lower()}_{angka.replace('.', '_')}.py"
    print(f"\n==================== {nomor} ====================")
    if not script.exists():
        print(f"Script tidak ditemukan: {script}")
        gagal.append(nomor)
        continue
    hasil = subprocess.run([sys.executable, str(script)])
    if hasil.returncode != 0:
        gagal.append(nomor)

print("\n==================== Ringkasan ====================")
print(f"Berhasil: {len(pilihan) - len(gagal)} dari {len(pilihan)}")
if gagal:
    print("Gagal   :", ", ".join(gagal))
