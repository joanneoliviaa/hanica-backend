import os
from datetime import date
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import numpy as np
import pandas as pd

from analytics.services import fcm, fpgrowth, rfm

TOLERANSI = 0.0001
hasil = []


def bandingkan(tahap, nama, manual, sistem):
    sistem = float(sistem)
    selisih = abs(round(sistem, 4) - manual)
    hasil.append({
        "Tahap": tahap, "Nilai yang Diuji": nama, "Hasil Manual": manual,
        "Hasil Sistem": round(sistem, 4), "Selisih": round(selisih, 4),
        "Keterangan": "Sesuai" if selisih <= TOLERANSI + 1e-12 else "TIDAK SESUAI",
    })


def bandingkan_teks(tahap, nama, manual, sistem):
    hasil.append({
        "Tahap": tahap, "Nilai yang Diuji": nama, "Hasil Manual": manual,
        "Hasil Sistem": sistem, "Selisih": "-",
        "Keterangan": "Sesuai" if manual == sistem else "TIDAK SESUAI",
    })


# ======================================================================
# Data Lampiran 9 (Tabel L9.1): faktur, tanggal, pelanggan, barang, subtotal
# Subtotal faktur ditulis pada baris terakhir faktur, baris lain 0
# ======================================================================
L91 = [
    ("2026/HSM/V/019", date(2026, 5, 20), "ENG-005", "Cup 22 Oz Oval / Jamboe", 7581195.02),
    ("2026/HSM/V/020", date(2026, 5, 21), "NUH-001", "Cup 10 Oz Tinggi / Hanica", 0),
    ("2026/HSM/V/020", date(2026, 5, 21), "NUH-001", "Cup 12 Oz / Hanica", 0),
    ("2026/HSM/V/020", date(2026, 5, 21), "NUH-001", "Cup 14 Oz / Hanica", 0),
    ("2026/HSM/V/020", date(2026, 5, 21), "NUH-001", "Cup 18 Oz Oval / Hanica", 0),
    ("2026/HSM/V/020", date(2026, 5, 21), "NUH-001", "Cup 22 Oz Oval / Hanica", 45276394.95),
    ("2026/HSM/V/021", date(2026, 5, 29), "DAUD-002", "Cup 12 Oz / Hanica", 0),
    ("2026/HSM/V/021", date(2026, 5, 29), "DAUD-002", "Cup 16 Oz / Hanica", 0),
    ("2026/HSM/V/021", date(2026, 5, 29), "DAUD-002", "Cup 22 Oz Oval / Hanica", 19638120.00),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 16 Oz Oval / Jamboe", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 22 Oz Oval / Hanica", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 22 Oz Oval / Jamboe", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 22 Oz Oval / Jamboe", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 22 Oz Oval / Jamboe", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 22 Oz Oval / Jamboe", 0),
    ("2026/HSM/V/022", date(2026, 5, 30), "DAU-001", "Cup 220 Ml / Cania", 16138530.86),
    ("2026/HSM/V/023", date(2026, 5, 30), "ENG-005", "Cup 22 Oz Oval / Hanica", 2940000.39),
]
NAMA = {"ENG-005": "Engelina", "NUH-001": "PT. Nuhun Bravo Agung",
        "DAUD-002": "Daud Samuel", "DAU-001": "Daud Amos"}
URUT = ["ENG-005", "NUH-001", "DAUD-002", "DAU-001"]   

# ======================================================================
# 1. RFM dan normalisasi -> rfm.hitung_rfm() asli, sumber data diganti Lampiran 9
# ======================================================================
baris_qs = [{"transaction_id": f, "transaction__transaction_date": t, "transaction__customer_id": p,
             "product_id": b, "subtotal": s} for f, t, p, b, s in L91]
qs_palsu = mock.MagicMock()
qs_palsu.select_related.return_value = qs_palsu
qs_palsu.filter.return_value = qs_palsu
qs_palsu.values.return_value = baris_qs
with mock.patch.object(rfm, "TransactionDetail", mock.MagicMock(objects=qs_palsu)):
    tabel_rfm, acuan = rfm.hitung_rfm()
tabel_rfm = tabel_rfm.loc[URUT]

bandingkan_teks("RFM", "Tanggal acuan", "2026-05-31", str(acuan.date()))
manual_rfm = {  # Tabel L9.4 dan L9.5
    "ENG-005": (1, 2, 10521195.41, 0.0000, 1.0000, 0.0000),
    "NUH-001": (10, 1, 45276394.95, 1.0000, 0.0000, 1.0000),
    "DAUD-002": (2, 1, 19638120.00, 0.1111, 0.0000, 0.2623),
    "DAU-001": (1, 1, 16138530.86, 0.0000, 0.0000, 0.1616),
}
for p, (r, f, m, rn, fn, mn) in manual_rfm.items():
    t = tabel_rfm.loc[p]
    bandingkan("RFM", f"Recency {NAMA[p]}", r, t.recency)
    bandingkan("RFM", f"Frequency {NAMA[p]}", f, t.frequency)
    bandingkan("RFM", f"Monetary {NAMA[p]} (Rp)", m, t.monetary)
    bandingkan("Normalisasi", f"R norm {NAMA[p]}", rn, t.recency_norm)
    bandingkan("Normalisasi", f"F norm {NAMA[p]}", fn, t.frequency_norm)
    bandingkan("Normalisasi", f"M norm {NAMA[p]}", mn, t.monetary_norm)

# Masukan FCM = hasil normalisasi sistem
X = tabel_rfm[["recency_norm", "frequency_norm", "monetary_norm"]].to_numpy(dtype=float)


# ======================================================================
# 2. FCM -> fcm.fcm() asli, U0 disamakan dengan Lampiran 9, MaxIter = 4
# ======================================================================
class RngTetap:
    """Pengganti generator acak: mengembalikan U0 Lampiran 9 alih-alih U0 acak."""
    def __init__(self, U0):
        self.U0 = np.array(U0, dtype=float)

    def dirichlet(self, alpha, size):
        return self.U0.copy()


def jalankan_fcm(U0, c, max_iter):
    """Panggil fcm.fcm() asli; catat pusat klaster V tiap iterasi dari dalam fungsi."""
    riwayat_V = []
    jarak_asli = fcm.jarak

    def jarak_dicatat(A, B):
        if A is X and B is not X and len(B) == c:
            riwayat_V.append(B.copy())
        return jarak_asli(A, B)

    with mock.patch("numpy.random.default_rng", lambda seed=None: RngTetap(U0)), \
         mock.patch.object(fcm, "jarak", jarak_dicatat):
        U, V, iterasi = fcm.fcm(X, c, max_iter=max_iter)
    return U, V, iterasi, riwayat_V


def fungsi_objektif(U_sebelum, V, m=fcm.M):
    """Rumus 2.11 memakai U iterasi sebelumnya dan pusat klaster V dari sistem."""
    return float(((U_sebelum ** m) * fcm.jarak(X, V) ** 2).sum())


U0_k2 = [[0.8, 0.2], [0.1, 0.9], [0.6, 0.4], [0.7, 0.3]]            # Tabel L9.6
U_iter = {0: np.array(U0_k2)}
V_iter = {}
for t in range(1, 5):
    U_t, _, _, riwayat = jalankan_fcm(U0_k2, 2, max_iter=t)
    U_iter[t] = U_t
    V_iter[t] = riwayat[t - 1]

manual_V_k2 = {  # Tabel L9.8, L9.13, L9.17
    1: [(0.0333, 0.4267, 0.1224), (0.7525, 0.0364, 0.7877)],
    2: [(0.0336, 0.3632, 0.1333), (0.9061, 0.0198, 0.9185)],
    3: [(0.0363, 0.3172, 0.1432), (0.9597, 0.0189, 0.9633)],
    4: [(0.0378, 0.2982, 0.1476), (0.9681, 0.0212, 0.9698)],
}
fitur = ["R", "F", "M"]
for t, pusat in manual_V_k2.items():
    for k, vk in enumerate(pusat):
        for j, nilai in enumerate(vk):
            bandingkan(f"FCM k=2 iterasi {t}", f"Pusat klaster V{k + 1} ({fitur[j]})", nilai, V_iter[t][k, j])

manual_P_k2 = {1: 0.7732, 2: 0.6636, 3: 0.6279, 4: 0.6236}         # Tabel L9.21
for t, nilai in manual_P_k2.items():
    bandingkan(f"FCM k=2 iterasi {t}", f"Fungsi objektif P{t}", nilai, fungsi_objektif(U_iter[t - 1], V_iter[t]))

manual_U_k2 = {  # Tabel L9.12, L9.16, L9.20 (mu klaster 1; mu klaster 2 = 1 - mu klaster 1)
    1: [0.8598, 0.0540, 0.7684, 0.8386],
    2: [0.8608, 0.0087, 0.8731, 0.9124],
    3: [0.8521, 0.0019, 0.9096, 0.9386],
    4: [0.8461, 0.0014, 0.9200, 0.9461],
}
for t, mu in manual_U_k2.items():
    for i, nilai in enumerate(mu):
        bandingkan(f"FCM k=2 iterasi {t}", f"Keanggotaan {NAMA[URUT[i]]} klaster 1", nilai, U_iter[t][i, 0])

U0_k3 = [[0.5, 0.3, 0.2], [0.3, 0.5, 0.2], [0.2, 0.3, 0.5], [0.3, 0.2, 0.5]]   # Tabel L9.22
U_k3, V_k3_akhir, _, riwayat_k3 = jalankan_fcm(U0_k3, 3, max_iter=4)
manual_V_k3_iter1 = [(0.2009, 0.5319, 0.2448), (0.5532, 0.1915, 0.5959), (0.1169, 0.0690, 0.2517)]  # Tabel L9.24
for k, vk in enumerate(manual_V_k3_iter1):
    for j, nilai in enumerate(vk):
        bandingkan("FCM k=3 iterasi 1", f"Pusat klaster V{k + 1} ({fitur[j]})", nilai, riwayat_k3[0][k, j])

# ======================================================================
# 3. Silhouette -> fcm.silhouette() asli, label = keanggotaan tertinggi U4
# ======================================================================
bandingkan("Silhouette", "Silhouette Coefficient k=2", 0.3617, fcm.silhouette(X, U_iter[4].argmax(axis=1)))
bandingkan("Silhouette", "Silhouette Coefficient k=3", 0.4270, fcm.silhouette(X, U_k3.argmax(axis=1)))
bandingkan_teks("Silhouette", "k optimal (Silhouette tertinggi)", "3",
                "3" if fcm.silhouette(X, U_k3.argmax(axis=1)) > fcm.silhouette(X, U_iter[4].argmax(axis=1)) else "2")

# ======================================================================
# 4. Label loyalitas -> fcm.beri_label() asli pada k=3
#    Manual memakai pusat klaster iterasi ke-4 (V4).
# ======================================================================
V4_k3 = riwayat_k3[3]
skor, _, label = fcm.beri_label(V4_k3)
manual_label = {0: (0.6666, "Tinggi"), 1: (0.3333, "Rendah"), 2: (0.3855, "Sedang")}
for k, (nilai, lab) in manual_label.items():
    bandingkan("Label loyalitas", f"Skor loyalitas klaster {k + 1} (V4)", nilai, skor[k])
    bandingkan_teks("Label loyalitas", f"Label klaster {k + 1}", lab, label[k])

# Catatan: fcm.fcm() mengembalikan V yang dihitung ulang dari U akhir (setara V5),
# dan jalankan_segmentasi() memakai V itu untuk label. Dicatat sebagai informasi.
skor_v5, _, label_v5 = fcm.beri_label(V_k3_akhir)

# ======================================================================
# 5. FP-Growth -> fpgrowth.tambang_aturan() asli, Tabel L9.39, min support 40%
# ======================================================================
keranjang = pd.DataFrame([(f, b) for f, _, _, b, _ in L91], columns=["trx", "produk"])
aturan = fpgrowth.tambang_aturan(keranjang, 0.40, 0.50)
G, B = "Cup 22 Oz Oval / Hanica", "Cup 12 Oz / Hanica"
manual_aturan = {  # Tabel L9.43
    "G -> B": (frozenset([G]), frozenset([B]), 0.40, 0.50, 1.25),
    "B -> G": (frozenset([B]), frozenset([G]), 0.40, 1.00, 1.25),
}
bandingkan("FP-Growth", "Jumlah aturan asosiasi", 2, len(aturan))
for nama, (a, b, s, c, l) in manual_aturan.items():
    r = aturan[(aturan["antecedents"] == a) & (aturan["consequents"] == b)]
    if r.empty:
        bandingkan_teks("FP-Growth", f"Aturan {nama} terbentuk", "Ya", "Tidak")
        continue
    bandingkan("FP-Growth", f"Support {nama}", s, r["support"].iloc[0])
    bandingkan("FP-Growth", f"Confidence {nama}", c, r["confidence"].iloc[0])
    bandingkan("FP-Growth", f"Lift {nama}", l, r["lift"].iloc[0])

# ======================================================================
# Ringkasan
# ======================================================================
df = pd.DataFrame(hasil)
pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 500)
print(df.to_string(index=False))
gagal = df[df["Keterangan"] != "Sesuai"]
angka = pd.to_numeric(df["Selisih"], errors="coerce")
print(f"\nTotal nilai diuji: {len(df)} | Sesuai: {len(df) - len(gagal)} | Tidak sesuai: {len(gagal)}")
print(f"Selisih maksimum: {angka.max():.4f}")
print("\nInformasi: skor loyalitas k=3 bila memakai pusat klaster yang dikembalikan fcm() (dihitung dari U4):")
for k in range(3):
    print(f"  klaster {k + 1}: skor {skor_v5[k]:.4f}, label {label_v5[k]}")

df.to_csv("hasil_verifikasi_lampiran9.csv", index=False)
try:
    df.to_excel("hasil_verifikasi_lampiran9.xlsx", index=False)
    print("\nHasil disimpan ke hasil_verifikasi_lampiran9.xlsx dan .csv")
except Exception:
    print("\nHasil disimpan ke hasil_verifikasi_lampiran9.csv")
