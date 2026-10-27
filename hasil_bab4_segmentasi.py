"""
Angka untuk Bab IV 4.2.1 c (Segmentasi FCM), d (Jumlah klaster optimal), dan e (Pelabelan loyalitas).
Jalankan dari folder Aplikasi (venv aktif), SETELAH RFM dan segmentasi dijalankan di aplikasi:
    python hasil_bab4_segmentasi.py
Skrip ini hanya MEMBACA database dan menjalankan ulang fungsi fcm.py yang sama (seed sama) di memori.
Hasil dicetak dan disimpan ke hasil_bab4_segmentasi.xlsx
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import numpy as np
import pandas as pd

from analytics.models import Cluster, ClusterMembership, RfmValue
from analytics.services import fcm
from catalog.models import Transaction

pd.set_option("display.width", 220)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

rfm = list(RfmValue.objects.select_related("customer").order_by("customer_id"))  # urutan sama dgn jalankan_segmentasi
if not rfm:
    raise SystemExit("Tabel RFM kosong. Jalankan perhitungan RFM dulu di aplikasi.")
X = np.array([[r.recency_norm, r.frequency_norm, r.monetary_norm] for r in rfm])
df = pd.DataFrame({
    "customer_id": [r.customer_id for r in rfm],
    "nama": [r.customer.customer_name for r in rfm],
    "recency": [r.recency for r in rfm],
    "frequency": [r.frequency for r in rfm],
    "monetary": [r.monetary for r in rfm],
    "status": [r.activity_status for r in rfm],
})
print(f"Jumlah pelanggan: {len(rfm)} | m = {fcm.M}, epsilon = {fcm.EPSILON}, MaxIter = {fcm.MAX_ITER}, seed = {fcm.SEED}")

# ------------------------------------------------------------- c & d: FCM untuk k = 2..5
hasil = fcm.evaluasi_k(X)
baris = []
for k, h in hasil.items():
    U, V = h["U"], h["V"]
    P = float(((U ** fcm.M) * fcm.jarak(X, V) ** 2).sum())
    anggota = np.bincount(U.argmax(axis=1), minlength=k)
    baris.append({"k": k, "Iterasi hingga konvergen": h["iterasi"],
                  "Konvergen sebelum MaxIter": h["iterasi"] < fcm.MAX_ITER,
                  "Fungsi objektif akhir": P,
                  "Anggota per klaster (urut kecil-besar)": " / ".join(map(str, sorted(anggota))),
                  "Klaster kosong": int((anggota == 0).sum()),
                  "Silhouette": h["silhouette"]})
tabel_k = pd.DataFrame(baris)
print("\n=== Tabel 4.7 dan 4.8: hasil FCM dan Silhouette per k ===")
print(tabel_k.to_string(index=False))
print("\nSilhouette per k:")
for _, r in tabel_k.iterrows():
    print(f"  k = {int(r['k'])}: {r['Silhouette']:.4f}")
k_opt = int(tabel_k.loc[tabel_k["Silhouette"].idxmax(), "k"])
print(f"k optimal (Silhouette tertinggi): {k_opt}")

k_db = Cluster.objects.first().total_clusters if Cluster.objects.exists() else None
print(f"k optimal tersimpan di aplikasi : {k_db}  -> {'SAMA' if k_db == k_opt else 'BERBEDA, cek ulang!'}")

# Jumlah keanggotaan tiap pelanggan = 1 (rumus 2.7)
U_opt = hasil[k_opt]["U"]
print(f"Jumlah derajat keanggotaan tiap pelanggan = 1: {np.allclose(U_opt.sum(axis=1), 1)}")

# ------------------------------------------------------------- c: derajat keanggotaan pada k optimal
V_opt = hasil[k_opt]["V"]
skor, urutan, label = fcm.beri_label(V_opt)
nama_label = {k: "Loyalitas " + label[k] for k in range(k_opt)}
for k in range(k_opt):
    df[f"mu {nama_label[k]}"] = U_opt[:, k]
df["klaster"] = [nama_label[k] for k in U_opt.argmax(axis=1)]
df["mu tertinggi"] = U_opt.max(axis=1)
transisi = df[df["mu tertinggi"] <= 0.60]
print(f"\n=== Derajat keanggotaan (k={k_opt}) ===")
print(f"Pelanggan dengan keanggotaan tertinggi <= 60% (berada di antara klaster): {len(transisi)}")
print(f"Rata-rata derajat keanggotaan tertinggi: {df['mu tertinggi'].mean():.4f}")
kol_mu = [c for c in df.columns if c.startswith("mu Loyalitas")]
print("Contoh pelanggan transisi (keanggotaan paling seimbang):")
print(df.nsmallest(5, "mu tertinggi")[["nama", "recency", "frequency", "monetary"] + kol_mu].to_string(index=False))

# ------------------------------------------------------------- e: pelabelan loyalitas
faktur = dict(pd.DataFrame(list(Transaction.objects.values_list("customer_id", "transaction_id")),
                           columns=["c", "t"]).groupby("c")["t"].nunique())
df["faktur"] = df["customer_id"].map(faktur).fillna(0).astype(int)
ringkas = []
for k in urutan[::-1]:  # dari skor tertinggi
    g = df[df["klaster"] == nama_label[k]]
    ringkas.append({
        "Label": nama_label[k], "Skor loyalitas": skor[k],
        "Pusat R norm": V_opt[k, 0], "Pusat F norm": V_opt[k, 1], "Pusat M norm": V_opt[k, 2],
        "Jumlah pelanggan": len(g), "Jumlah faktur": int(g["faktur"].sum()),
        "Rata-rata Recency (hari)": g["recency"].mean(), "Median Recency": g["recency"].median(),
        "Rata-rata Frequency": g["frequency"].mean(), "Median Frequency": g["frequency"].median(),
        "Rata-rata Monetary (Rp)": g["monetary"].mean(), "Median Monetary (Rp)": g["monetary"].median(),
        "Total Monetary (Rp)": g["monetary"].sum(),
        "Aktif": int((g["status"] == "Aktif").sum()),
        "Kurang Aktif": int((g["status"] == "Kurang Aktif").sum()),
        "Tidak Aktif": int((g["status"] == "Tidak Aktif").sum()),
    })
tabel_label = pd.DataFrame(ringkas)
print("\n=== Tabel 4.9: karakteristik klaster ===")
print(tabel_label.T.to_string(header=False))

# Bandingkan dengan yang tersimpan di aplikasi
print("\n=== Klaster tersimpan di aplikasi ===")
for cl in Cluster.objects.order_by("cluster_number"):
    n = sum(1 for p, d in pd.DataFrame(list(ClusterMembership.objects.values_list(
        "customer_id", "cluster_id", "membership_degree")), columns=["p", "c", "d"])
        .sort_values("d", ascending=False).drop_duplicates("p")[["p", "c"]].values if d == cl.cluster_id)
    print(f"  {cl.loyalty_label}: skor {cl.loyalty_score:.4f}, anggota {n}, pusat "
          + ", ".join(f"{v:.4f}" for v in cl.centroid))

with pd.ExcelWriter("hasil_bab4_segmentasi.xlsx") as w:
    tabel_k.to_excel(w, sheet_name="FCM per k", index=False)
    tabel_label.to_excel(w, sheet_name="Karakteristik klaster", index=False)
    df.sort_values(["klaster", "mu tertinggi"], ascending=[True, False]).to_excel(
        w, sheet_name="Keanggotaan pelanggan", index=False)
print("\nHasil disimpan ke hasil_bab4_segmentasi.xlsx")
