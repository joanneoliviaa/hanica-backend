import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import pandas as pd

from analytics.models import RfmValue
from catalog.models import Transaction

rfm = pd.DataFrame(list(RfmValue.objects.values(
    "customer_id", "customer__customer_name", "recency", "frequency", "monetary",
    "recency_norm", "frequency_norm", "monetary_norm", "activity_status")))
if rfm.empty:
    raise SystemExit("Tabel RFM masih kosong. Unggah data dan jalankan perhitungan dulu.")
rfm = rfm.rename(columns={"customer__customer_name": "nama"})

trx = pd.DataFrame(list(Transaction.objects.values("transaction_id", "transaction_date")))
awal, akhir = trx["transaction_date"].min(), trx["transaction_date"].max()
acuan = akhir + pd.Timedelta(days=1)

print("=== Ringkasan data ===")
print(f"Jumlah faktur (transaksi)   : {len(trx):,}".replace(",", "."))
print(f"Jumlah pelanggan unik       : {len(rfm)}")
print(f"Periode data                : {awal:%d-%m-%Y} s.d. {akhir:%d-%m-%Y}")
print(f"Tanggal acuan Recency       : {acuan:%d-%m-%Y}")

# ---- Tabel 4.6: statistik deskriptif
stat = pd.DataFrame({
    "Recency (hari)": rfm["recency"],
    "Frequency (faktur)": rfm["frequency"],
    "Monetary (Rp)": rfm["monetary"],
}).agg(["min", "max", "mean", "median", "std"]).rename(
    index={"min": "Minimum", "max": "Maksimum", "mean": "Rata-rata", "median": "Median", "std": "Simpangan baku"})
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
print("\n=== Tabel 4.6 Statistik deskriptif RFM ===")
print(stat.to_string())

# ---- Pelanggan dengan nilai ekstrem (untuk contoh di paragraf)
print("\n=== 5 pelanggan dengan Monetary terbesar ===")
print(rfm.nlargest(5, "monetary")[["nama", "recency", "frequency", "monetary"]].to_string(index=False))
print("\n=== 5 pelanggan dengan Frequency terbesar ===")
print(rfm.nlargest(5, "frequency")[["nama", "recency", "frequency", "monetary"]].to_string(index=False))
print(f"\nPelanggan yang hanya 1 kali bertransaksi (F = 1): {(rfm['frequency'] == 1).sum()}")
print(f"Pelanggan dengan Monetary di atas rata-rata     : {(rfm['monetary'] > rfm['monetary'].mean()).sum()}")

# ---- Kriteria 4.1.5
print("\n=== Pemeriksaan kriteria evaluasi (4.1.5) ===")
cek = {
    "Recency > 0 untuk semua pelanggan": (rfm["recency"] > 0).all(),
    "Frequency >= 1 untuk semua pelanggan": (rfm["frequency"] >= 1).all(),
    "Monetary > 0 untuk semua pelanggan": (rfm["monetary"] > 0).all(),
    "Semua nilai normalisasi di rentang 0-1": rfm[["recency_norm", "frequency_norm", "monetary_norm"]]
        .apply(lambda s: s.between(0, 1).all()).all(),
}
for nama, lolos in cek.items():
    print(f"  [{'LOLOS' if lolos else 'GAGAL'}] {nama}")
for kolom in ["recency", "frequency", "monetary"]:
    gagal = rfm[(rfm[kolom] <= 0) if kolom != "frequency" else (rfm[kolom] < 1)]
    if len(gagal):
        print(f"  Pelanggan bermasalah pada {kolom}:", ", ".join(gagal["nama"].head(10)))

print("\n=== Status keaktifan ===")
print(rfm["activity_status"].value_counts().reindex(["Aktif", "Kurang Aktif", "Tidak Aktif"]).to_string())

with pd.ExcelWriter("hasil_bab4_rfm.xlsx") as w:
    stat.to_excel(w, sheet_name="Statistik RFM")
    rfm.sort_values("monetary", ascending=False).to_excel(w, sheet_name="RFM per pelanggan", index=False)
print("\nHasil disimpan ke hasil_bab4_rfm.xlsx")
