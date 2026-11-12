"""
Tabel 4.10 Nilai Indeks Validitas Klaster Setiap Jumlah Klaster
Silhouette Coefficient (fungsi aplikasi) + Davies-Bouldin Index dan Calinski-Harabasz Index (scikit-learn,
di luar sistem) pada label hasil FCM (derajat keanggotaan tertinggi).
Jalankan:  python "Pengujian Bab 4/Tabel 4.10/tabel_4_10.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

rfm, X = B.ambil_rfm()
hasil = B.hitung_fcm_semua(X)

nilai = {k: B.indeks_validitas(X, h["U"].argmax(axis=1)) for k, h in hasil.items()}
rows = [[str(k), B.desimal(v["silhouette"]), B.interpretasi_silhouette(v["silhouette"]), B.desimal(v["dbi"]),
         B.desimal(v["chi"], 2)] for k, v in nilai.items()]

k_sil = max(nilai, key=lambda k: nilai[k]["silhouette"])
k_dbi = min(nilai, key=lambda k: nilai[k]["dbi"])
k_chi = max(nilai, key=lambda k: nilai[k]["chi"])

isi = [B.judul("Tabel 4.10 Nilai Indeks Validitas Klaster Setiap Jumlah Klaster"),
       B.tabel(["Jumlah Klaster (k)", "Silhouette Coefficient", "Interpretasi", "DBI", "CHI"], rows,
               [3.2, 3.6, 3.4, 2.8, 2.8])]
isi += B.catatan(
    f"k optimal menurut Silhouette (tertinggi): k = {k_sil}; menurut DBI (terendah): k = {k_dbi}; "
    f"menurut CHI (tertinggi): k = {k_chi}. Interpretasi Silhouette mengikuti Tabel 4.3 "
    "(&gt; 0,70 kuat; &gt; 0,50–0,70 baik; &gt; 0,25–0,50 lemah; ≤ 0,25 buruk). DBI dan CHI dihitung dengan "
    "scikit-learn di luar sistem.")
B.simpan_pdf(SINI / "Tabel 4.10.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
