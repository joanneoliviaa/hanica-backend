"""
Gambar 4.1 Grafik Fungsi Objektif Fuzzy C-Means per Iterasi (k = 2 sampai k = 5)
FCM dijalankan ulang di memori dengan fungsi, parameter, dan seed yang sama dengan aplikasi.
Hasil: Gambar 4.1.pdf (gambar + tabel nilai per iterasi) dan Gambar 4.1.png (siap ditempel ke Word).
Jalankan:  python "Pengujian Bab 4/Gambar 4.1/gambar_4_1.py"
"""
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

rfm, X = B.ambil_rfm()
hasil = B.hitung_fcm_semua(X)

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
for k, h in hasil.items():
    r = h["riwayat"]
    ax.plot(range(1, len(r) + 1), r, marker={2: "o", 3: "s", 4: "^", 5: "D"}.get(k, "o"), markersize=4,
            linewidth=1.4, label=f"k = {k} ({len(r)} iterasi)")
maks = max(len(h["riwayat"]) for h in hasil.values())
ax.set_xticks(range(1, maks + 1, 1 if maks <= 20 else 2))
ax.set_xlabel("Iterasi ke-t")
ax.set_ylabel("Fungsi objektif (Pt)")
ax.grid(True, alpha=0.3)
ax.legend()
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: B.desimal(v, 1)))
fig.tight_layout()
path_png = SINI / "Gambar 4.1.png"
fig.savefig(path_png)
plt.close(fig)

rows = [[str(t + 1)] + [B.desimal(h["riwayat"][t]) if t < len(h["riwayat"]) else "-" for h in hasil.values()]
        for t in range(maks)]
isi = [B.Image(str(path_png), width=16 * B.cm, height=9.2 * B.cm),
       B.judul("Gambar 4.1 Grafik Fungsi Objektif Fuzzy C-Means per Iterasi")]
isi += B.catatan(f"{len(rfm)} pelanggan; m = {B.desimal(B.fcm.M, 0)}; batas maksimum iterasi = {B.fcm.MAX_ITER}; "
                 f"ξ = {B.desimal(B.fcm.EPSILON, 3)}; seed = {B.fcm.SEED}.")
isi += [B.PageBreak(), B.Paragraph("Nilai fungsi objektif setiap iterasi (data Gambar 4.1)", B.SUBJUDUL),
        B.tabel(["Iterasi"] + [f"k = {k}" for k in hasil], rows, [2.6, 3.3, 3.3, 3.3, 3.3], ukuran=9)]
turun = []
for k, h in hasil.items():
    r = h["riwayat"]
    total = r[0] - r[-1]
    turun.append([f"k = {k}", B.desimal(r[0]), B.desimal(r[min(5, len(r) - 1)]), B.desimal(r[-1]),
                  B.desimal((r[0] - r[min(5, len(r) - 1)]) / total * 100, 1) + "%" if total else "-"])
isi += [B.Spacer(1, 12), B.Paragraph("Informasi tambahan: besar penurunan fungsi objektif", B.SUBJUDUL),
        B.tabel(["k", "Iterasi ke-1", "Iterasi ke-6", "Iterasi terakhir", "Penurunan s.d. iterasi ke-6"], turun,
                [2.2, 3.2, 3.2, 3.4, 4.4])]
B.simpan_pdf(SINI / "Gambar 4.1.pdf", isi)
