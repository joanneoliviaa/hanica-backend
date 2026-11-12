"""
Gambar 4.2 Heatmap Uji Sensitivitas Parameter FP-Growth
FP-Growth (fungsi aplikasi: fpgrowth.tambang_aturan) dijalankan pada setiap klaster untuk setiap kombinasi
minimum support x minimum confidence, seluruh periode data. Database tidak diubah.
Tampilan heatmap sama dengan hasil_bab4_sensitivitas.py.
Hasil: Gambar 4.2.pdf dan Gambar 4.2.png (siap ditempel ke Word).
Jalankan:  python "Pengujian Bab 4/Gambar 4.2/gambar_4_2.py"
"""
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, PowerNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from analytics.models import Cluster  # noqa: E402
from analytics.services import fpgrowth  # noqa: E402

np = B.np
SUPPORT = fpgrowth.GRID_SUPPORT
CONFIDENCE = fpgrowth.GRID_CONFIDENCE
DEF_S, DEF_C = fpgrowth.DEFAULT_MIN_SUPPORT, fpgrowth.DEFAULT_MIN_CONFIDENCE

keranjang = fpgrowth.ambil_keranjang(*fpgrowth._rentang_data())
keranjang["klaster"] = keranjang["pelanggan"].map(fpgrowth.keanggotaan_tegas())

grid = {}
for cl in Cluster.objects.order_by("-loyalty_score"):
    d = keranjang[keranjang["klaster"] == cl.cluster_id]
    jumlah = pd.DataFrame(0, index=SUPPORT, columns=CONFIDENCE)
    conf = pd.DataFrame(np.nan, index=SUPPORT, columns=CONFIDENCE)
    lift = pd.DataFrame(np.nan, index=SUPPORT, columns=CONFIDENCE)
    for s in SUPPORT:
        for c in CONFIDENCE:
            a = fpgrowth.tambang_aturan(d, s, c)
            jumlah.loc[s, c] = len(a)
            if len(a):
                conf.loc[s, c] = a["confidence"].mean()
                lift.loc[s, c] = a["lift"].mean()
    grid[cl.loyalty_label] = {"faktur": d["trx"].nunique(), "jumlah": jumlah, "conf": conf, "lift": lift}
if not grid:
    raise SystemExit("Belum ada klaster. Jalankan segmentasi di aplikasi dulu.")


def pct(v):
    return f"{v * 100:g}%"


# ------------------------------------------------------------------ heatmap
BIRU = ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("biru", BIRU)
TINTA, TINTA_2 = "#1f1f1e", "#5f5e5a"
vmax = max(int(g["jumlah"].values.max()) for g in grid.values())
norm = PowerNorm(gamma=0.5, vmin=0, vmax=max(vmax, 1))

plt.rcParams.update({"font.size": 10, "font.family": "sans-serif"})
fig, axes = plt.subplots(1, len(grid), figsize=(5.2 * len(grid), 5.9), constrained_layout=True)
axes = np.atleast_1d(axes)
for ax, (label, g) in zip(axes, grid.items()):
    data = g["jumlah"].values.astype(float)
    ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = int(data[i, j])
            ax.text(j, i, str(v), ha="center", va="center", fontsize=9,
                    color="#ffffff" if norm(v) > 0.55 else TINTA)
    ax.set_xticks(np.arange(-0.5, data.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, data.shape[0]), minor=True)
    ax.grid(which="minor", color="#ffffff", linewidth=2)
    ax.tick_params(which="minor", length=0)
    i0, j0 = SUPPORT.index(DEF_S), CONFIDENCE.index(DEF_C)
    ax.add_patch(Rectangle((j0 - 0.45, i0 - 0.45), 0.9, 0.9, fill=False, edgecolor="#d1452f", linewidth=2.5, zorder=5))
    ax.set_xticks(range(len(CONFIDENCE)), [pct(c) for c in CONFIDENCE], color=TINTA_2)
    ax.set_yticks(range(len(SUPPORT)), [pct(s) for s in SUPPORT], color=TINTA_2)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Minimum confidence", color=TINTA_2)
    ax.set_ylabel("Minimum support", color=TINTA_2)
    ax.set_title(f"{label} ({g['faktur']:,} faktur)".replace(",", "."), color=TINTA, fontsize=11, loc="left")
path_png = SINI / "Gambar 4.2.png"
fig.savefig(path_png, dpi=220, facecolor="white")
plt.close(fig)

# ------------------------------------------------------------------ PDF
lebar = 16 if len(grid) <= 2 else 24
isi = [B.Image(str(path_png), width=lebar * B.cm, height=lebar * 5.9 / (5.2 * len(grid)) * B.cm),
       B.judul("Gambar 4.2 Heatmap Uji Sensitivitas Parameter FP-Growth")]
isi += B.catatan(f"Angka pada sel = jumlah aturan asosiasi. Kotak merah = nilai default sistem (minimum support "
                 f"{pct(DEF_S)}, minimum confidence {pct(DEF_C)}). Seluruh periode data.")

# informasi tambahan: rata-rata confidence & lift pada minimum confidence default
rows, header = [], ["Minimum support"]
for label in grid:
    header += [f"Aturan<br/>{label}", f"Rata-rata conf.<br/>{label}", f"Rata-rata lift<br/>{label}"]
for s in SUPPORT:
    b = [pct(s)]
    for g in grid.values():
        n = int(g["jumlah"].loc[s, DEF_C])
        b += [str(n), B.persen(g["conf"].loc[s, DEF_C]) if n else "-", B.desimal(g["lift"].loc[s, DEF_C]) if n else "-"]
    rows.append(b)
isi += [B.PageBreak(),
        B.Paragraph(f"Informasi tambahan: jumlah aturan, rata-rata confidence, dan rata-rata lift pada minimum "
                    f"confidence {pct(DEF_C)}", B.SUBJUDUL),
        B.tabel(header, rows, [2.4] + [2.3] * (3 * len(grid)), ukuran=8.5)]
B.simpan_pdf(SINI / "Gambar 4.2.pdf", isi)
for label, g in grid.items():
    print(f"{label}: {g['jumlah'].loc[DEF_S, DEF_C]} aturan pada default; maksimum {int(g['jumlah'].values.max())}")
