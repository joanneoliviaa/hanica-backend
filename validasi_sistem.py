"""
Validasi hasil perhitungan sistem dengan cara independen.
Jalankan dari folder Aplikasi:   python validasi_sistem.py
Syarat: segmentasi sudah dijalankan di aplikasi. Skrip ini TIDAK mengubah database.
Hasil dicetak ke layar dan disimpan ke validasi_hasil.md
"""
import itertools
import os
import sys
from collections import defaultdict
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import numpy as np
import skfuzzy as fuzz
from sklearn.metrics import silhouette_score

from analytics.models import Cluster, ClusterMembership, RfmValue
from analytics.services import fcm, fpgrowth
from catalog.models import TransactionDetail

baris_laporan = []
gagal = []


def cetak(teks=""):
    print(teks)
    baris_laporan.append(teks)


def periksa(nama, lolos, detail=""):
    cetak(f"  [{'LOLOS' if lolos else 'GAGAL'}] {nama}  {detail}")
    if not lolos:
        gagal.append(nama)


if not Cluster.objects.exists() or not RfmValue.objects.exists():
    sys.exit("Segmentasi belum dijalankan. Jalankan dulu dari aplikasi.")

# ---------------------------------------------------------------- 1. RFM
cetak("## 1. RFM dan normalisasi Min-Max (hitung ulang dengan perulangan biasa, tanpa pandas)")
rows = list(TransactionDetail.objects.values_list(
    "transaction_id", "transaction__transaction_date", "transaction__customer_id", "subtotal"))
terakhir = max(r[1] for r in rows)
acuan = terakhir + timedelta(days=1)
faktur = defaultdict(lambda: defaultdict(float))     # pelanggan -> faktur -> nilai
tgl_terakhir = {}
for trx, tgl, pel, sub in rows:
    faktur[pel][trx] += float(sub)
    if pel not in tgl_terakhir or tgl > tgl_terakhir[pel]:
        tgl_terakhir[pel] = tgl
mentah = {p: ((acuan - tgl_terakhir[p]).days, len(faktur[p]), sum(faktur[p].values())) for p in faktur}


def minmax(nilai):
    lo, hi = min(nilai.values()), max(nilai.values())
    return {k: (v - lo) / (hi - lo) if hi > lo else 0.0 for k, v in nilai.items()}


rn = minmax({p: v[0] for p, v in mentah.items()})
fn = minmax({p: v[1] for p, v in mentah.items()})
mn = minmax({p: v[2] for p, v in mentah.items()})
tersimpan = {r.customer_id: r for r in RfmValue.objects.all()}
cetak(f"  Tanggal acuan: {acuan}; jumlah pelanggan: sistem {len(tersimpan)}, hitung ulang {len(mentah)}")
periksa("Jumlah pelanggan sama", len(tersimpan) == len(mentah))
sel = {"R": 0, "F": 0, "M": 0.0, "Rn": 0.0, "Fn": 0.0, "Mn": 0.0}
for p, (r, f, m) in mentah.items():
    t = tersimpan[p]
    sel["R"] += int(t.recency != r)
    sel["F"] += int(t.frequency != f)
    sel["M"] = max(sel["M"], abs(t.monetary - m))
    sel["Rn"] = max(sel["Rn"], abs(t.recency_norm - rn[p]))
    sel["Fn"] = max(sel["Fn"], abs(t.frequency_norm - fn[p]))
    sel["Mn"] = max(sel["Mn"], abs(t.monetary_norm - mn[p]))
periksa("Recency identik untuk semua pelanggan", sel["R"] == 0, f"(beda: {sel['R']} pelanggan)")
periksa("Frequency identik untuk semua pelanggan", sel["F"] == 0, f"(beda: {sel['F']} pelanggan)")
periksa("Monetary identik", sel["M"] < 0.01, f"(selisih maks Rp{sel['M']:.4f})")
periksa("R, F, M ternormalisasi identik", max(sel["Rn"], sel["Fn"], sel["Mn"]) < 1e-9,
        f"(selisih maks {max(sel['Rn'], sel['Fn'], sel['Mn']):.2e})")
salah_status = sum(
    1 for p, t in tersimpan.items()
    if t.activity_status != ("Aktif" if mentah[p][0] <= 30 else "Kurang Aktif" if mentah[p][0] <= 180 else "Tidak Aktif"))
periksa("Status keaktifan (<=30 / <=180 / >180 hari) sesuai", salah_status == 0, f"(salah: {salah_status})")

# ---------------------------------------------------------------- 2. FCM + Silhouette
cetak("\n## 2. Fuzzy C-Means dan Silhouette (dibandingkan dengan scikit-fuzzy dan scikit-learn)")
kode = sorted(tersimpan)
X = np.array([[tersimpan[p].recency_norm, tersimpan[p].frequency_norm, tersimpan[p].monetary_norm] for p in kode])
hasil_app = fcm.evaluasi_k(X)
cetak("  | k | Silhouette sistem | Silhouette sklearn (label sistem) | Silhouette sklearn (FCM skfuzzy) | selisih pusat klaster maks |")
cetak("  |---|---|---|---|---|")
for k in (2, 3, 4, 5):
    U_app, V_app = hasil_app[k]["U"], hasil_app[k]["V"]
    lab_app = U_app.argmax(axis=1)
    s_app = hasil_app[k]["silhouette"]
    s_sk = silhouette_score(X, lab_app) if len(set(lab_app)) > 1 else float("nan")
    cntr, u, *_ = fuzz.cmeans(X.T, k, 2.0, error=1e-8, maxiter=2000, seed=42)
    lab_fz = u.argmax(axis=0)
    s_fz = silhouette_score(X, lab_fz)
    # cocokkan pusat klaster: urutkan menurut skor loyalitas ((1-R)+F+M)/3
    urut = lambda V: V[np.argsort(((1 - V[:, 0]) + V[:, 1] + V[:, 2]) / 3)]
    selisih = np.abs(urut(V_app) - urut(cntr)).max()
    cetak(f"  | {k} | {s_app:.4f} | {s_sk:.4f} | {s_fz:.4f} | {selisih:.4f} |")
    periksa(f"k={k}: fungsi silhouette sistem = sklearn pada label yang sama", abs(s_app - s_sk) < 1e-9)
    periksa(f"k={k}: pusat klaster sistem ~ scikit-fuzzy (toleransi 0,02)", selisih < 0.02)
k_sistem = Cluster.objects.first().total_clusters
k_fz = max((2, 3, 4, 5), key=lambda k: silhouette_score(X, fuzz.cmeans(X.T, k, 2.0, error=1e-8, maxiter=2000, seed=42)[1].argmax(axis=0)))
periksa("k optimal sama dengan hasil scikit-fuzzy + sklearn", k_sistem == k_fz, f"(sistem k={k_sistem}, pembanding k={k_fz})")
U_db = defaultdict(dict)
for m in ClusterMembership.objects.all():
    U_db[m.customer_id][m.cluster_id] = m.membership_degree
jumlah_salah = sum(1 for p in kode if abs(sum(U_db[p].values()) - 1) > 1e-6)
periksa("Derajat keanggotaan tiap pelanggan berjumlah 1", jumlah_salah == 0, f"(menyimpang: {jumlah_salah})")

# ---------------------------------------------------------------- 3. FP-Growth
cetak("\n## 3. FP-Growth (dibandingkan dengan Apriori buatan sendiri + hitung manual support/confidence/lift)")
klaster_pel = {p: max(d, key=d.get) for p, d in U_db.items()}
baskets = defaultdict(lambda: defaultdict(set))       # klaster -> faktur -> produk
for trx, pel, prod in TransactionDetail.objects.values_list("transaction_id", "transaction__customer_id", "product_id"):
    baskets[klaster_pel[pel]][trx].add(prod)


def apriori_manual(bks, min_sup):
    n = len(bks)
    batas = min_sup * n - 1e-12
    cnt = defaultdict(int)
    for b in bks:
        for i in b:
            cnt[frozenset([i])] += 1
    level = {s: c for s, c in cnt.items() if c >= batas}
    semua = dict(level)
    k = 2
    while level:
        kandidat = set()
        keys = list(level)
        for a, b in itertools.combinations(keys, 2):
            u = a | b
            if len(u) == k and all(frozenset(s) in level for s in itertools.combinations(u, k - 1)):
                kandidat.add(u)
        cnt = defaultdict(int)
        for b in bks:
            for c in kandidat:
                if c <= b:
                    cnt[c] += 1
        level = {s: c for s, c in cnt.items() if c >= batas}
        semua.update(level)
        k += 1
    return semua, n


def aturan_manual(bks, min_sup, min_conf):
    semua, n = apriori_manual(bks, min_sup)
    hasil = {}
    for s, c in semua.items():
        if len(s) < 2:
            continue
        for r in range(1, len(s)):
            for a in map(frozenset, itertools.combinations(s, r)):
                b = s - a
                conf = c / semua[a]
                if conf >= min_conf - 1e-12:
                    hasil[(a, b)] = (c / n, conf, conf / (semua[b] / n))
    return hasil


for ms, mc in [(0.02, 0.60), (0.02, 0.40)]:
    cetak(f"\n  Parameter: min support {ms:.0%}, min confidence {mc:.0%}")
    h_sistem = fpgrowth.jalankan_fpgrowth(ms, mc, "seluruh", simpan=False)["hasil"]
    for cl, h in h_sistem.items():
        bks = list(baskets[cl.cluster_id].values())
        man = aturan_manual(bks, ms, mc)
        sis = {}
        for r in h["aturan"].itertuples():
            sis[(frozenset(r.antecedents), frozenset(r.consequents))] = (r.support, r.confidence, r.lift)
        sama_kunci = set(man) == set(sis)
        selisih = max((max(abs(a - b) for a, b in zip(man[k], sis[k])) for k in set(man) & set(sis)), default=0)
        periksa(f"{cl.loyalty_label}: {len(bks)} transaksi, aturan sistem {len(sis)} vs manual {len(man)}",
                sama_kunci and selisih < 1e-9, f"(selisih maks support/confidence/lift {selisih:.2e})")
        if not sama_kunci:
            cetak(f"      hanya di sistem: {len(set(sis) - set(man))}, hanya di manual: {len(set(man) - set(sis))}")

cetak("\n## Ringkasan")
if gagal:
    cetak(f"  {len(gagal)} pemeriksaan GAGAL:")
    for g in gagal:
        cetak(f"   - {g}")
else:
    cetak("  Semua pemeriksaan LOLOS.")
with open("validasi_hasil.md", "w", encoding="utf-8") as f:
    f.write("# Hasil validasi sistem\n\n" + "\n".join(baris_laporan) + "\n")
print("\nLaporan disimpan di validasi_hasil.md")