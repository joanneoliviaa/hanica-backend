"""
Tabel 4.16 Perbandingan Indeks Validitas Klaster dengan dan tanpa Outlier
Outlier (|z| > 3, sama dengan Tabel 4.15) dikeluarkan, RFM dihitung ulang (tanggal acuan dan normalisasi
Min-Max dari data yang tersisa), lalu FCM, Silhouette, DBI, dan CHI dijalankan ulang dengan parameter
dan urutan pelanggan yang sama dengan aplikasi. Analisis di luar sistem, database tidak diubah.
Jalankan:  python "Pengujian Bab 4/Tabel 4.16/tabel_4_16.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import pandas as pd  # noqa: E402

from catalog.models import Transaction  # noqa: E402

BATAS_Z = 3

rfm, X = B.ambil_rfm()
df = pd.DataFrame({"pelanggan": [r.customer_id for r in rfm], "nama": [r.customer.customer_name for r in rfm],
                   "R": [r.recency for r in rfm], "F": [r.frequency for r in rfm], "M": [r.monetary for r in rfm],
                   "terakhir": [pd.Timestamp(r.last_purchase_date) for r in rfm]})
z = (df[["R", "F", "M"]] - df[["R", "F", "M"]].mean()) / df[["R", "F", "M"]].std(ddof=1)
mask = ~(z.abs() > BATAS_Z).any(axis=1)
sisa = df[mask].copy()

# RFM ulang pada data tanpa outlier: tanggal acuan = sehari setelah transaksi terakhir yang tersisa
acuan = sisa["terakhir"].max() + pd.Timedelta(days=1)
sisa["R"] = (acuan - sisa["terakhir"]).dt.days
mm = lambda s: (s - s.min()) / (s.max() - s.min())
X2 = B.np.column_stack([mm(sisa[c]) for c in ("R", "F", "M")])

trx = pd.DataFrame(list(Transaction.objects.values_list("transaction_id", "customer_id")), columns=["t", "c"])
faktur_sisa = trx[trx["c"].isin(sisa["pelanggan"])]["t"].nunique()

dengan = {k: B.indeks_validitas(X, h["U"].argmax(axis=1)) for k, h in B.hitung_fcm_semua(X).items()}
hasil_tanpa = B.hitung_fcm_semua(X2)
tanpa = {k: B.indeks_validitas(X2, h["U"].argmax(axis=1)) for k, h in hasil_tanpa.items()}

rows = [[str(k), B.desimal(dengan[k]["silhouette"]), B.desimal(tanpa[k]["silhouette"]), B.desimal(dengan[k]["dbi"]),
         B.desimal(tanpa[k]["dbi"]), B.desimal(dengan[k]["chi"], 2), B.desimal(tanpa[k]["chi"], 2)] for k in dengan]


def k_opt(d):
    return (max(d, key=lambda k: d[k]["silhouette"]), min(d, key=lambda k: d[k]["dbi"]),
            max(d, key=lambda k: d[k]["chi"]))


kd, kt = k_opt(dengan), k_opt(tanpa)
isi = [B.judul("Tabel 4.16 Perbandingan Indeks Validitas Klaster dengan dan tanpa Outlier"),
       B.tabel(["k", "Silhouette (dengan)", "Silhouette (tanpa)", "DBI (dengan)", "DBI (tanpa)", "CHI (dengan)",
                "CHI (tanpa)"], rows, [1.2, 2.6, 2.6, 2.3, 2.3, 2.5, 2.5], ukuran=9.5)]
isi += B.catatan(
    f"Dengan outlier: {len(df)} pelanggan, {B.bulat(trx['t'].nunique())} faktur. Tanpa outlier: {len(sisa)} pelanggan, "
    f"{B.bulat(faktur_sisa)} faktur (tanggal acuan {acuan:%d-%m-%Y}).<br/>"
    f"k optimal dengan outlier — Silhouette: {kd[0]}, DBI: {kd[1]}, CHI: {kd[2]}. "
    f"k optimal tanpa outlier — Silhouette: {kt[0]} ({B.interpretasi_silhouette(tanpa[kt[0]]['silhouette']).lower()}), "
    f"DBI: {kt[1]}, CHI: {kt[2]}.")

# karakteristik klaster pada k optimal tanpa outlier (Silhouette)
k = kt[0]
h = hasil_tanpa[k]
skor, _, label = B.fcm.beri_label(h["V"])
anggota = B.np.bincount(h["U"].argmax(axis=1), minlength=k)
lab = h["U"].argmax(axis=1)
rows2 = []
for i, idx in enumerate(B.urutan_recency(h["V"])):
    g = sisa[lab == idx]
    rows2.append([f"V{i + 1}", B.desimal(h["V"][idx, 0]), B.desimal(h["V"][idx, 1]), B.desimal(h["V"][idx, 2]),
                  str(int(anggota[idx])), B.bulat(g["R"].median()), B.desimal(g["F"].median(), 1),
                  B.desimal(g["M"].median() / 1e6, 2), B.desimal(skor[idx]), "Loyalitas " + label[int(idx)]])
isi += [B.Spacer(1, 14),
        B.Paragraph(f"Informasi tambahan: karakteristik klaster tanpa outlier pada k = {k}", B.SUBJUDUL),
        B.tabel(["Klaster", "Pusat R", "Pusat F", "Pusat M", "Anggota", "Median R (hari)", "Median F",
                 "Median M (juta Rp)", "Skor", "Label"], rows2,
                [1.4, 1.5, 1.5, 1.5, 1.5, 1.7, 1.4, 1.9, 1.4, 2.6], ukuran=8.5)]
isi += B.catatan("Pusat klaster dalam skala ternormalisasi data tanpa outlier; V1, V2, ... diurutkan dari pusat "
                 "Recency terkecil. Skor dan label dihitung dengan rumus 2.22 dan aturan pelabelan yang sama.")
B.simpan_pdf(SINI / "Tabel 4.16.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
