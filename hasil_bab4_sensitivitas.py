"""
Angka dan gambar untuk Bab IV 4.2.1 f (Pengujian sensitivitas parameter FP-Growth).
Jalankan dari folder Aplikasi (venv aktif), SETELAH segmentasi dijalankan di aplikasi:
    python hasil_bab4_sensitivitas.py
Skrip ini hanya MEMBACA database dan memanggil fungsi FP-Growth sistem (fpgrowth.tambang_aturan)
untuk setiap kombinasi minimum support x minimum confidence pada setiap klaster (seluruh periode).
Hasil:
  - hasil_bab4_sensitivitas.xlsx  (jumlah aturan, rata-rata confidence, rata-rata lift per kombinasi)
  - heatmap_sensitivitas.png      (gambar heatmap jumlah aturan, siap dipakai sebagai Gambar 4.x)
Butuh matplotlib:  pip install matplotlib
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import numpy as np
import pandas as pd

from analytics.models import Cluster
from analytics.services import fpgrowth

SUPPORT = fpgrowth.GRID_SUPPORT          # 1% .. 40%
CONFIDENCE = fpgrowth.GRID_CONFIDENCE    # 30% .. 80%
DEF_S, DEF_C = fpgrowth.DEFAULT_MIN_SUPPORT, fpgrowth.DEFAULT_MIN_CONFIDENCE

keranjang = fpgrowth.ambil_keranjang(*fpgrowth._rentang_data())
keranjang["klaster"] = keranjang["pelanggan"].map(fpgrowth.keanggotaan_tegas())

# ---------------------------------------------------------------- hitung grid
grid = {}   # label -> dict of DataFrames
for cl in Cluster.objects.order_by("-loyalty_score"):
    d = keranjang[keranjang["klaster"] == cl.cluster_id]
    n_faktur = d["trx"].nunique()
    jumlah = pd.DataFrame(0, index=SUPPORT, columns=CONFIDENCE)
    rata_conf = pd.DataFrame(np.nan, index=SUPPORT, columns=CONFIDENCE)
    rata_lift = pd.DataFrame(np.nan, index=SUPPORT, columns=CONFIDENCE)
    for s in SUPPORT:
        for c in CONFIDENCE:
            aturan = fpgrowth.tambang_aturan(d, s, c)
            jumlah.loc[s, c] = len(aturan)
            if len(aturan):
                rata_conf.loc[s, c] = aturan["confidence"].mean()
                rata_lift.loc[s, c] = aturan["lift"].mean()
    grid[cl.loyalty_label] = {"faktur": n_faktur, "jumlah": jumlah, "conf": rata_conf, "lift": rata_lift}


def pct(v):
    return f"{v * 100:g}%"


pd.set_option("display.width", 200)
for label, g in grid.items():
    print(f"\n=== {label} ({g['faktur']} faktur) - jumlah aturan ===")
    t = g["jumlah"].copy()
    t.index = [pct(s) for s in t.index]
    t.columns = [pct(c) for c in t.columns]
    t.index.name = "support \\ confidence"
    print(t.to_string())
    print(f"Pada nilai bawaan ({pct(DEF_S)} / {pct(DEF_C)}): {g['jumlah'].loc[DEF_S, DEF_C]} aturan, "
          f"rata-rata confidence {g['conf'].loc[DEF_S, DEF_C]:.4f}, rata-rata lift {g['lift'].loc[DEF_S, DEF_C]:.4f}")

# ringkasan baris minimum confidence bawaan (untuk Tabel 4.10)
ringkas = []
for s in SUPPORT:
    baris = {"Minimum support": pct(s)}
    for label, g in grid.items():
        baris[f"Jumlah aturan {label}"] = int(g["jumlah"].loc[s, DEF_C])
        baris[f"Rata-rata confidence {label}"] = g["conf"].loc[s, DEF_C]
        baris[f"Rata-rata lift {label}"] = g["lift"].loc[s, DEF_C]
    ringkas.append(baris)
tabel_ringkas = pd.DataFrame(ringkas)
print(f"\n=== Ringkasan pada minimum confidence {pct(DEF_C)} (untuk Tabel 4.10) ===")
print(tabel_ringkas.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

with pd.ExcelWriter("hasil_bab4_sensitivitas.xlsx") as w:
    tabel_ringkas.to_excel(w, sheet_name="Ringkasan conf bawaan", index=False)
    for label, g in grid.items():
        nama = label.replace("Loyalitas ", "")[:12]
        for kunci, judul in [("jumlah", "aturan"), ("conf", "conf"), ("lift", "lift")]:
            t = g[kunci].copy()
            t.index = [pct(s) for s in t.index]
            t.columns = [pct(c) for c in t.columns]
            t.to_excel(w, sheet_name=f"{nama} {judul}")
print("\nTabel disimpan ke hasil_bab4_sensitivitas.xlsx")

# ---------------------------------------------------------------- heatmap
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, PowerNorm
    from matplotlib.patches import Rectangle
except ImportError:
    raise SystemExit("matplotlib belum terpasang. Jalankan: pip install matplotlib, lalu ulangi skrip ini.")

# satu hue (biru), terang -> gelap: makin gelap = makin banyak aturan
BIRU = ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("biru", BIRU)
TINTA, TINTA_2, GRID = "#1f1f1e", "#5f5e5a", "#ffffff"

vmax = max(int(g["jumlah"].values.max()) for g in grid.values())
norm = PowerNorm(gamma=0.5, vmin=0, vmax=max(vmax, 1))   # akar: beda kecil di nilai rendah tetap terlihat

plt.rcParams.update({"font.size": 10, "font.family": "sans-serif"})
fig, axes = plt.subplots(1, len(grid), figsize=(5.2 * len(grid), 5.9), constrained_layout=True)
axes = np.atleast_1d(axes)
for ax, (label, g) in zip(axes, grid.items()):
    data = g["jumlah"].values.astype(float)
    ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = int(data[i, j])
            warna = "#ffffff" if norm(v) > 0.55 else TINTA
            ax.text(j, i, str(v), ha="center", va="center", fontsize=9, color=warna)
    # garis putih tipis antarsel
    ax.set_xticks(np.arange(-0.5, data.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, data.shape[0]), minor=True)
    ax.grid(which="minor", color=GRID, linewidth=2)
    ax.tick_params(which="minor", length=0)
    # tandai nilai bawaan
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
fig.savefig("heatmap_sensitivitas.png", dpi=220, facecolor="white")
print("Gambar disimpan ke heatmap_sensitivitas.png")
