"""
Tabel 4.8 Hasil Perhitungan Nilai Pusat Klaster
Pusat klaster FCM (R, F, M ternormalisasi) untuk k = 2 sampai k = 5.
Jalankan:  python "Pengujian Bab 4/Tabel 4.8/tabel_4_8.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

rfm, X = B.ambil_rfm()
hasil = B.hitung_fcm_semua(X)

R = [r.recency for r in rfm]
F = [r.frequency for r in rfm]
M = [r.monetary for r in rfm]
asli = lambda v, a: v * (max(a) - min(a)) + min(a)  # kebalikan normalisasi Min-Max

rows, span, rows_asli, span_asli = [], [], [], []
for k, h in hasil.items():
    awal = len(rows) + 1
    for i, idx in enumerate(B.urutan_recency(h["V"])):
        vr, vf, vm = h["V"][idx]
        rows.append([str(k) if i == 0 else "", f"V{i + 1}", B.desimal(vr), B.desimal(vf), B.desimal(vm)])
        rows_asli.append([str(k) if i == 0 else "", f"V{i + 1}", B.bulat(asli(vr, R)), B.desimal(asli(vf, F), 1),
                          B.desimal(asli(vm, M) / 1e6, 2)])
    span.append(((0, awal), (0, len(rows))))

isi = [B.judul("Tabel 4.8 Hasil Perhitungan Nilai Pusat Klaster"),
       B.tabel(["Jumlah Klaster (k)", "Klaster", "Pusat R", "Pusat F", "Pusat M"], rows, [3.4, 2.6, 3.3, 3.3, 3.3],
               span=span)]
isi += B.catatan("Pusat klaster dalam skala ternormalisasi (0–1). V1, V2, ... diurutkan dari pusat Recency terkecil.")
isi += [B.PageBreak(), B.Paragraph("Informasi tambahan: pusat klaster dikembalikan ke skala asli", B.SUBJUDUL),
        B.tabel(["Jumlah Klaster (k)", "Klaster", "Recency (hari)", "Frequency (faktur)", "Monetary (juta Rp)"],
                rows_asli, [3.4, 2.6, 3.3, 3.3, 3.3], span=span)]
isi += B.catatan("Nilai asli = nilai ternormalisasi × (maksimum − minimum) + minimum, dengan minimum dan maksimum "
                 "dari Tabel 4.6. Pusat klaster adalah rata-rata berbobot derajat keanggotaan, sehingga dapat "
                 "berbeda dengan median.")
B.simpan_pdf(SINI / "Tabel 4.8.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
