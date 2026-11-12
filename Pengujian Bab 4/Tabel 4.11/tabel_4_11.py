"""
Tabel 4.11 Hasil Pelabelan Klaster Berdasarkan Skor Loyalitas
Membaca klaster yang tersimpan di aplikasi, lalu mencocokkan skornya dengan perhitungan ulang (rumus 2.22).
Jalankan:  python "Pengujian Bab 4/Tabel 4.11/tabel_4_11.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import pandas as pd  # noqa: E402

from analytics.models import Cluster  # noqa: E402
from analytics.services.fpgrowth import keanggotaan_tegas  # noqa: E402
from catalog.models import Transaction  # noqa: E402

klaster = list(Cluster.objects.order_by("-loyalty_score"))  # skor tertinggi di atas
if not klaster:
    raise SystemExit("Belum ada klaster. Jalankan segmentasi di aplikasi dulu.")

rfm, _ = B.ambil_rfm()
info = pd.DataFrame({"pelanggan": [r.customer_id for r in rfm], "R": [r.recency for r in rfm],
                     "F": [r.frequency for r in rfm], "M": [r.monetary for r in rfm],
                     "status": [r.activity_status for r in rfm]})
info["klaster"] = info["pelanggan"].map(keanggotaan_tegas())
faktur = pd.Series(dict(pd.DataFrame(list(Transaction.objects.values_list("customer_id", "transaction_id")),
                                     columns=["c", "t"]).groupby("c")["t"].nunique()))
info["faktur"] = info["pelanggan"].map(faktur).fillna(0)

rows, rows_hitung, rows_karakter = [], [], []
for cl in klaster:
    vr, vf, vm = cl.centroid
    skor_ulang = ((1 - vr) + vf + vm) / 3
    rows.append([str(cl.cluster_number), B.desimal(cl.loyalty_score), cl.loyalty_label])
    rows_hitung.append([str(cl.cluster_number), B.desimal(vr), B.desimal(vf), B.desimal(vm),
                        f"((1 − {B.desimal(vr)}) + {B.desimal(vf)} + {B.desimal(vm)}) / 3 = {B.desimal(skor_ulang)}",
                        "Sesuai" if abs(skor_ulang - cl.loyalty_score) < 1e-9 else "BEDA"])
    g = info[info["klaster"] == cl.cluster_id]
    rows_karakter.append([cl.loyalty_label, str(len(g)), B.bulat(g["faktur"].sum()),
                          B.bulat(g["R"].median()), B.desimal(g["F"].median(), 1),
                          B.desimal(g["M"].median() / 1e6, 2),
                          str(int((g["status"] == "Aktif").sum())), str(int((g["status"] == "Kurang Aktif").sum())),
                          str(int((g["status"] == "Tidak Aktif").sum()))])

urut_skor = [cl.loyalty_score for cl in sorted(klaster, key=lambda c: -c.loyalty_score)]
urutan_benar = all(a >= b for a, b in zip(urut_skor, urut_skor[1:]))

isi = [B.judul("Tabel 4.11 Hasil Pelabelan Klaster Berdasarkan Skor Loyalitas"),
       B.tabel(["Klaster", "Skor", "Label Loyalitas"], rows, [4, 4, 6])]
isi += B.catatan(f"k optimal = {klaster[0].total_clusters}. Label diberikan berdasarkan urutan skor "
                 f"(skor lebih tinggi = loyalitas lebih tinggi): {'sesuai' if urutan_benar else 'TIDAK sesuai'}.")
isi += [B.Spacer(1, 14), B.Paragraph("Rincian perhitungan skor loyalitas (rumus 2.22)", B.SUBJUDUL),
        B.tabel(["Klaster", "Pusat R", "Pusat F", "Pusat M", "Perhitungan", "Cek"], rows_hitung,
                [1.6, 1.8, 1.8, 1.8, 7.0, 1.4], ukuran=9),
        B.Spacer(1, 14), B.Paragraph("Informasi tambahan: karakteristik anggota setiap klaster", B.SUBJUDUL),
        B.tabel(["Label", "Pelanggan", "Faktur", "Median R (hari)", "Median F", "Median M (juta Rp)",
                 "Aktif", "Kurang Aktif", "Tidak Aktif"], rows_karakter,
                [2.8, 1.8, 1.6, 1.8, 1.5, 2.0, 1.3, 1.6, 1.6], ukuran=8.5)]
isi += B.catatan("Pelanggan dimasukkan ke klaster dengan derajat keanggotaan tertinggi. Status keaktifan: "
                 "Aktif ≤ 30 hari, Kurang Aktif 31–180 hari, Tidak Aktif &gt; 180 hari.")
B.simpan_pdf(SINI / "Tabel 4.11.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
