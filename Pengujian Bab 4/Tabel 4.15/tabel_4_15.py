"""
Tabel 4.15 Pelanggan yang Terdeteksi sebagai Outlier
z-score (rumus 2.19, simpangan baku sampel) pada nilai R, F, M sebelum normalisasi; outlier = |z| > 3
pada minimal satu atribut. Analisis di luar sistem, database tidak diubah.
Jalankan:  python "Pengujian Bab 4/Tabel 4.15/tabel_4_15.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import pandas as pd  # noqa: E402

BATAS_Z = 3

rfm, _ = B.ambil_rfm()
df = pd.DataFrame({"nama": [r.customer.customer_name for r in rfm], "R": [r.recency for r in rfm],
                   "F": [r.frequency for r in rfm], "M": [r.monetary for r in rfm]})
z = (df[["R", "F", "M"]] - df[["R", "F", "M"]].mean()) / df[["R", "F", "M"]].std(ddof=1)
outlier = df[(z.abs() > BATAS_Z).any(axis=1)].assign(zR=z["R"], zF=z["F"], zM=z["M"]).sort_values("zM", ascending=False)

def tandai(v):
    teks = B.desimal(v, 2)
    return f"<b>{teks}</b>" if abs(v) > BATAS_Z else teks

rows = [[r["nama"], tandai(r["zR"]), tandai(r["zF"]), tandai(r["zM"])] for _, r in outlier.iterrows()]
isi = [B.judul("Tabel 4.15 Pelanggan yang Terdeteksi sebagai Outlier"),
       B.tabel(["Nama Pelanggan", "Z Recency", "Z Frequency", "Z Monetary"], rows, [7, 3, 3, 3], rata_kiri=(0,))]
isi += B.catatan(
    f"Cetak tebal = |z| &gt; {BATAS_Z}. Jumlah pelanggan diperiksa: {len(df)}; outlier: {len(outlier)}. "
    f"|z| maksimum per atribut: Recency {B.desimal(z['R'].abs().max(), 2)}, Frequency "
    f"{B.desimal(z['F'].abs().max(), 2)}, Monetary {B.desimal(z['M'].abs().max(), 2)}. Outlier pada Frequency: "
    f"{int((z['F'].abs() > BATAS_Z).sum())} pelanggan; pada Monetary: {int((z['M'].abs() > BATAS_Z).sum())} pelanggan.")
isi += [B.Spacer(1, 12), B.Paragraph("Informasi tambahan: nilai RFM asli pelanggan outlier", B.SUBJUDUL),
        B.tabel(["Nama Pelanggan", "Recency (hari)", "Frequency (faktur)", "Monetary (Rp)"],
                [[r["nama"], B.bulat(r["R"]), B.bulat(r["F"]), B.bulat(r["M"])] for _, r in outlier.iterrows()],
                [7, 3, 3, 3.5], rata_kiri=(0,))]
B.simpan_pdf(SINI / "Tabel 4.15.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
