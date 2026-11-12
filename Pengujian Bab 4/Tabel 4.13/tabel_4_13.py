"""
Tabel 4.13 Lima Aturan Asosiasi dengan Lift Tertinggi pada Setiap Klaster
FP-Growth dijalankan dengan fungsi aplikasi (simpan=False), parameter default, periode seluruh data.
Jalankan:  python "Pengujian Bab 4/Tabel 4.13/tabel_4_13.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

from analytics.services import fpgrowth  # noqa: E402

N_TERATAS = 5
MS, MC = fpgrowth.DEFAULT_MIN_SUPPORT, fpgrowth.DEFAULT_MIN_CONFIDENCE
hasil = fpgrowth.jalankan_fpgrowth(MS, MC, "seluruh", simpan=False)
klaster = sorted(hasil["hasil"].items(), key=lambda x: -x[0].loyalty_score)


def gabung(itemset):
    return ", ".join(sorted(B.rapikan_produk(i) for i in itemset))


rows, span = [], []
for cl, h in klaster:
    a = h["aturan"]
    if not len(a):
        rows.append([cl.loyalty_label, "Tidak ada aturan", "-", "-", "-", "-"])
        continue
    top = a.sort_values(["lift", "confidence"], ascending=False).head(N_TERATAS)
    awal = len(rows) + 1
    for i, r in enumerate(top.itertuples()):
        rows.append([cl.loyalty_label if i == 0 else "", gabung(r.antecedents), gabung(r.consequents),
                     B.persen(r.support), B.persen(r.confidence), B.desimal(r.lift)])
    span.append(((0, awal), (0, len(rows))))

isi = [B.judul("Tabel 4.13 Lima Aturan Asosiasi dengan Lift Tertinggi pada Setiap Klaster"),
       B.tabel(["Klaster", "Antecedent", "Consequent", "Support", "Confidence", "Lift"], rows,
               [3.2, 7.6, 6.4, 2.2, 2.4, 2.0], rata_kiri=(1, 2), span=span, ukuran=9)]
isi += B.catatan(f"Parameter: minimum support {B.persen(MS, 0)}, minimum confidence {B.persen(MC, 0)}, seluruh "
                 "periode. Diurutkan dari lift tertinggi (jika sama, confidence tertinggi). Nama produk ditampilkan "
                 "tanpa keterangan isi kemasan.")
B.simpan_pdf(SINI / "Tabel 4.13.pdf", isi, mendatar=True)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
