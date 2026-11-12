"""
Tabel 4.12 Ringkasan Aturan Asosiasi pada Setiap Klaster
FP-Growth dijalankan dengan fungsi aplikasi (fpgrowth.jalankan_fpgrowth, simpan=False), parameter default,
dan periode seluruh data. Database tidak diubah.
Jalankan:  python "Pengujian Bab 4/Tabel 4.12/tabel_4_12.py"
"""
import math
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

from analytics.services import fpgrowth  # noqa: E402

MS, MC = fpgrowth.DEFAULT_MIN_SUPPORT, fpgrowth.DEFAULT_MIN_CONFIDENCE
hasil = fpgrowth.jalankan_fpgrowth(MS, MC, "seluruh", simpan=False)
klaster = sorted(hasil["hasil"].items(), key=lambda x: -x[0].loyalty_score)  # loyalitas tertinggi di kiri

kolom, info = [], []
for cl, h in klaster:
    a = h["aturan"]
    n_item = (a["antecedents"].map(len) + a["consequents"].map(len)) if len(a) else []
    kolom.append({
        "Jumlah aturan asosiasi": str(len(a)),
        "Aturan dengan 2 item": str(int((n_item == 2).sum())) if len(a) else "0",
        "Aturan dengan 3 item atau lebih": str(int((n_item >= 3).sum())) if len(a) else "0",
        "Rata-rata support": B.persen(a["support"].mean()) if len(a) else "-",
        "Rata-rata confidence": B.persen(a["confidence"].mean()) if len(a) else "-",
        "Rata-rata lift": B.desimal(a["lift"].mean()) if len(a) else "-",
    })
    info.append(f"{cl.loyalty_label}: {B.bulat(h['transaksi'])} faktur, minimum support {B.persen(MS, 0)} ≈ "
                f"{math.ceil(MS * h['transaksi'])} faktur; lift minimum {B.desimal(a['lift'].min()) if len(a) else '-'}; "
                f"seluruh aturan lift &gt; 1: {'Ya' if len(a) and (a['lift'] > 1).all() else 'Tidak'}")

rows = [[baris] + [k[baris] for k in kolom] for baris in kolom[0]]
isi = [B.judul("Tabel 4.12 Ringkasan Aturan Asosiasi pada Setiap Klaster"),
       B.tabel(["Karakteristik"] + [cl.loyalty_label for cl, _ in klaster], rows, [6] + [4.5] * len(klaster),
               rata_kiri=(0,))]
awal, akhir = hasil["periode"]
isi += B.catatan(f"Parameter: minimum support {B.persen(MS, 0)}, minimum confidence {B.persen(MC, 0)}, periode "
                 f"{awal:%d-%m-%Y} s.d. {akhir:%d-%m-%Y}.<br/>" + "<br/>".join(info))
B.simpan_pdf(SINI / "Tabel 4.12.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
