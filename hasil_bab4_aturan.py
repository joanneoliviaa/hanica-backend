"""
Angka untuk Bab IV 4.2.1 g (Aturan asosiasi yang terbentuk).
Jalankan dari folder Aplikasi (venv aktif), SETELAH segmentasi dijalankan di aplikasi:
    python hasil_bab4_aturan.py
Skrip ini hanya MEMBACA database dan memanggil fpgrowth.jalankan_fpgrowth(..., simpan=False),
yaitu fungsi yang sama dengan halaman Analisis Pola Pembelian, dengan parameter default
dan periode seluruh data. Hasil dicetak dan disimpan ke hasil_bab4_aturan.xlsx
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import pandas as pd

from analytics.services import fpgrowth
from catalog.models import TransactionDetail

MS, MC = fpgrowth.DEFAULT_MIN_SUPPORT, fpgrowth.DEFAULT_MIN_CONFIDENCE
hasil = fpgrowth.jalankan_fpgrowth(MS, MC, "seluruh", simpan=False)
awal, akhir = hasil["periode"]

# tanggal terakhir setiap produk terjual -> untuk menandai produk yang sudah tidak dijual
jual = pd.DataFrame(list(TransactionDetail.objects.values_list("product_id", "transaction__transaction_date")),
                    columns=["produk", "tanggal"])
terakhir_jual = jual.groupby("produk")["tanggal"].max()
batas_usang = pd.Timestamp(akhir) - pd.DateOffset(months=12)
usang = {p for p, t in terakhir_jual.items() if pd.Timestamp(t) < batas_usang}


def merek(produk):
    return produk.split("/")[-1].strip().title() if "/" in produk else "(tanpa merek)"


def gabung(itemset):
    return ", ".join(sorted(itemset))


pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 60)
print(f"Parameter: min support {MS:.0%}, min confidence {MC:.0%}, periode {awal} s.d. {akhir}")
print(f"Produk dianggap 'sudah tidak dijual' bila terakhir terjual sebelum {batas_usang:%d-%m-%Y}: {len(usang)} produk")

semua = []
ringkas = []
for cl, h in hasil["hasil"].items():
    a = h["aturan"]
    label = cl.loyalty_label
    print(f"\n==================== {label} ({h['transaksi']} faktur) ====================")
    if a is None or len(a) == 0:
        print("  Tidak ada aturan.", h.get("keterangan") or "")
        ringkas.append({"Klaster": label, "Faktur": h["transaksi"], "Jumlah aturan": 0})
        continue
    a = a.copy()
    a["Antecedent"] = a["antecedents"].map(gabung)
    a["Consequent"] = a["consequents"].map(gabung)
    a["Jumlah item"] = a["antecedents"].map(len) + a["consequents"].map(len)
    item = a.apply(lambda r: set(r["antecedents"]) | set(r["consequents"]), axis=1)
    a["Merek"] = item.map(lambda s: ", ".join(sorted({merek(p) for p in s})))
    a["Memuat produk tidak dijual lagi"] = item.map(lambda s: ", ".join(sorted(s & usang)))
    a = a.sort_values(["lift", "confidence"], ascending=False)

    print(f"Jumlah aturan        : {len(a)}")
    print(f"Lift > 1 semua       : {(a['lift'] > 1).all()}  (min {a['lift'].min():.4f}, maks {a['lift'].max():.4f})")
    print(f"Rata-rata support    : {a['support'].mean():.4f}")
    print(f"Rata-rata confidence : {a['confidence'].mean():.4f}")
    print(f"Rata-rata lift       : {a['lift'].mean():.4f}")
    print(f"Aturan 2 item / 3 item atau lebih: {(a['Jumlah item'] == 2).sum()} / {(a['Jumlah item'] >= 3).sum()}")
    print("Komposisi merek dalam aturan (jumlah aturan yang memuat merek tsb):")
    hitung = {}
    for s in item:
        for m in {merek(p) for p in s}:
            hitung[m] = hitung.get(m, 0) + 1
    for m, n in sorted(hitung.items(), key=lambda x: -x[1]):
        print(f"   {m:<20} {n}")
    n_usang = (a["Memuat produk tidak dijual lagi"] != "").sum()
    print(f"Aturan yang memuat produk yang sudah tidak dijual: {n_usang}")
    if n_usang:
        print("   produk:", "; ".join(sorted(set(", ".join(a.loc[a['Memuat produk tidak dijual lagi'] != '',
                                                              'Memuat produk tidak dijual lagi']).split(", ")))))
    print("\n5 aturan dengan lift tertinggi:")
    top = a.head(5)[["Antecedent", "Consequent", "support", "confidence", "lift"]]
    print(top.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    ringkas.append({"Klaster": label, "Faktur": h["transaksi"], "Jumlah aturan": len(a),
                    "Lift min": a["lift"].min(), "Lift maks": a["lift"].max(),
                    "Rata-rata support": a["support"].mean(), "Rata-rata confidence": a["confidence"].mean(),
                    "Rata-rata lift": a["lift"].mean(), "Aturan 2 item": int((a["Jumlah item"] == 2).sum()),
                    "Aturan >=3 item": int((a["Jumlah item"] >= 3).sum()),
                    "Aturan dgn produk tidak dijual lagi": int(n_usang),
                    **{f"Aturan memuat {m}": n for m, n in hitung.items()}})
    a.insert(0, "Klaster", label)
    semua.append(a[["Klaster", "Antecedent", "Consequent", "support", "confidence", "lift",
                    "Jumlah item", "Merek", "Memuat produk tidak dijual lagi"]])

with pd.ExcelWriter("hasil_bab4_aturan.xlsx") as w:
    pd.DataFrame(ringkas).to_excel(w, sheet_name="Ringkasan", index=False)
    if semua:
        pd.concat(semua).to_excel(w, sheet_name="Semua aturan", index=False)
print("\nHasil disimpan ke hasil_bab4_aturan.xlsx")
