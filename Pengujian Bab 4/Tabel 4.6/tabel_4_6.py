"""
Tabel 4.6 Statistik Deskriptif Nilai RFM Pelanggan
Membaca nilai RFM dari database aplikasi.
Jalankan:  python "Pengujian Bab 4/Tabel 4.6/tabel_4_6.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import pandas as pd  # noqa: E402

from catalog.models import Transaction  # noqa: E402

rfm, _ = B.ambil_rfm()
df = pd.DataFrame({
    "R": [r.recency for r in rfm], "F": [r.frequency for r in rfm], "M": [r.monetary for r in rfm],
    "Rn": [r.recency_norm for r in rfm], "Fn": [r.frequency_norm for r in rfm], "Mn": [r.monetary_norm for r in rfm],
})
tgl = pd.Series(list(Transaction.objects.values_list("transaction_date", flat=True)))
awal, akhir = pd.Timestamp(tgl.min()), pd.Timestamp(tgl.max())
acuan = akhir + pd.Timedelta(days=1)

def angka_rf(v):
    return B.bulat(v) if float(v).is_integer() else B.desimal(v, 2)

def angka_m(v):
    return B.bulat(v) if abs(v - round(v)) < 0.005 else B.desimal(v, 2)

rows = []
for nama, fungsi in [("Minimum", "min"), ("Maksimum", "max"), ("Rata-rata", "mean"), ("Median", "median")]:
    rows.append([nama, angka_rf(getattr(df["R"], fungsi)()), angka_rf(getattr(df["F"], fungsi)()),
                 angka_m(getattr(df["M"], fungsi)())])

cek = {
    "Recency ≥ 1 hari": (df["R"] >= 1).all(),
    "Frequency ≥ 1 faktur": (df["F"] >= 1).all(),
    "Monetary > Rp0": (df["M"] > 0).all(),
    "Seluruh nilai normalisasi berada pada rentang 0–1": df[["Rn", "Fn", "Mn"]].apply(lambda s: s.between(0, 1).all()).all(),
}

isi = [B.judul("Tabel 4.6 Statistik Deskriptif Nilai RFM Pelanggan"),
       B.tabel(["Statistik", "Recency (hari)", "Frequency (faktur)", "Monetary (Rp)"], rows, [3.5, 3.5, 3.8, 5.2])]
isi += B.catatan(
    f"Jumlah pelanggan: {len(df)}; jumlah faktur: {B.bulat(len(tgl))}; periode data: {awal:%d-%m-%Y} s.d. "
    f"{akhir:%d-%m-%Y}; tanggal acuan Recency: {acuan:%d-%m-%Y}.")
isi += [B.Spacer(1, 10), B.Paragraph("Pemeriksaan kriteria evaluasi", B.SUBJUDUL),
        B.tabel(["Kriteria", "Hasil"], [[k, "Terpenuhi" if v else "TIDAK terpenuhi"] for k, v in cek.items()],
                [11, 5], rata_kiri=(0,))]
B.simpan_pdf(SINI / "Tabel 4.6.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
