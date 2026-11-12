"""
Tabel 4.7 Hasil Segmentasi Fuzzy C-Means untuk Setiap Jumlah Klaster
(grafik fungsi objektif per iterasi ada di folder Gambar 4.1)
FCM dijalankan ulang di memori dengan fungsi, parameter, dan seed yang sama dengan aplikasi.
Jalankan:  python "Pengujian Bab 4/Tabel 4.7/tabel_4_7.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

rfm, X = B.ambil_rfm()
hasil = B.hitung_fcm_semua(X)

rows = []
for k, h in hasil.items():
    r = h["riwayat"]
    rows.append([str(k), str(h["iterasi"]), B.desimal(h["P_akhir"]), B.desimal(abs(r[-1] - r[-2]), 6)])

kosong = sum(int((B.np.bincount(h["U"].argmax(axis=1), minlength=k) == 0).sum()) for k, h in hasil.items())
selisih_mu = max(float(B.np.abs(h["U"].sum(axis=1) - 1).max()) for h in hasil.values())
semua_konvergen = all(h["iterasi"] < B.fcm.MAX_ITER for h in hasil.values())

# ------------------------------------------------------------------ PDF
isi = [B.judul("Tabel 4.7 Hasil Segmentasi Fuzzy C-Means untuk Setiap Jumlah Klaster"),
       B.tabel(["Jumlah Klaster (k)", "Iterasi Hingga Konvergen", "Fungsi Objektif Akhir",
                "Selisih Fungsi Objektif Akhir |P<sub>t</sub> − P<sub>t−1</sub>|"], rows, [3.4, 3.8, 3.8, 5])]
isi += B.catatan(
    f"{len(rfm)} pelanggan; m = {B.desimal(B.fcm.M, 0)}; batas maksimum iterasi = {B.fcm.MAX_ITER}; "
    f"ξ = {B.desimal(B.fcm.EPSILON, 3)}; seed = {B.fcm.SEED}. Pemeriksaan: seluruh k konvergen sebelum batas "
    f"maksimum iterasi: {'Ya' if semua_konvergen else 'Tidak'}; klaster kosong: {kosong}; selisih maksimum jumlah "
    f"derajat keanggotaan tiap pelanggan terhadap 1: {selisih_mu:.1e}.")

B.simpan_pdf(SINI / "Tabel 4.7.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
