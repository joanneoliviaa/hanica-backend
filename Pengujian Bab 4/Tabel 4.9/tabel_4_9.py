"""
Tabel 4.9 Contoh Hasil Derajat Keanggotaan Akhir Pelanggan (k = 2)
Memilih pelanggan paling tegas di setiap klaster dan pelanggan paling di perbatasan.
Jalankan:  python "Pengujian Bab 4/Tabel 4.9/tabel_4_9.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

import pandas as pd  # noqa: E402

K = 2              # k optimal
N_TEGAS = 2        # contoh pelanggan paling tegas per klaster
N_PERBATASAN = 2   # contoh pelanggan paling di perbatasan

rfm, X = B.ambil_rfm()
h = B.hitung_fcm_semua(X, daftar_k=(K,))[K]
urut = B.urutan_recency(h["V"])          # Klaster 1 = V1 (pusat Recency terkecil), dst.
U = h["U"][:, urut]

df = pd.DataFrame({"nama": [r.customer.customer_name for r in rfm], "R": [r.recency for r in rfm],
                   "F": [r.frequency for r in rfm], "M": [r.monetary for r in rfm]})
for j in range(K):
    df[f"mu{j + 1}"] = U[:, j]
df["klaster"] = U.argmax(axis=1) + 1
df["mu_maks"] = U.max(axis=1)

contoh = [df[df["klaster"] == j + 1].nlargest(N_TEGAS, "mu_maks") for j in range(K)]
contoh.append(df.nsmallest(N_PERBATASAN, "mu_maks"))
contoh = pd.concat(contoh).drop_duplicates("nama")

rows = [[r["nama"], B.bulat(r["R"]), B.bulat(r["F"]), B.bulat(r["M"])] + [B.desimal(r[f"mu{j + 1}"]) for j in range(K)]
        for _, r in contoh.iterrows()]
mu = df["mu_maks"]
isi = [B.judul(f"Tabel 4.9 Contoh Hasil Derajat Keanggotaan Akhir Pelanggan (k = {K})"),
       B.tabel(["Nama Pelanggan", "R", "F", "M"] + [f"μ Klaster {j + 1}" for j in range(K)], rows,
               [5.0, 1.5, 1.4, 3.2, 2.5, 2.5], rata_kiri=(0,))]
isi += B.catatan(
    "R = Recency (hari), F = Frequency (faktur), M = Monetary (Rp). Klaster 1 dan Klaster 2 sesuai dengan V1 dan V2 "
    f"pada Tabel 4.8. Baris 1–{N_TEGAS * K}: pelanggan dengan μ maksimum tertinggi pada setiap klaster; "
    f"{N_PERBATASAN} baris terakhir: pelanggan dengan μ maksimum terendah (paling di perbatasan).")
ring = [[f"{K}", B.desimal(mu.mean()), B.desimal(mu.min()), str(int((mu >= 0.8).sum())),
         str(int(((mu >= 0.6) & (mu < 0.8)).sum())), str(int((mu < 0.6).sum()))]]
isi += [B.Spacer(1, 14), B.Paragraph("Informasi tambahan: ringkasan derajat keanggotaan maksimum seluruh pelanggan",
                                     B.SUBJUDUL),
        B.tabel(["k", "Rata-rata μ maks", "μ maks terendah", "μ maks ≥ 0,8", "0,6 ≤ μ maks &lt; 0,8", "μ maks &lt; 0,6"],
                ring, [1.5, 3, 3, 2.8, 3.2, 2.6])]
isi += B.catatan(f"Tiga kolom terakhir adalah jumlah pelanggan (total {len(df)} pelanggan).")
B.simpan_pdf(SINI / "Tabel 4.9.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
