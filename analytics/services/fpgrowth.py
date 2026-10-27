from datetime import timedelta

import pandas as pd
from django.db import transaction as db_transaction
from mlxtend.frequent_patterns import association_rules, fpgrowth

from analytics.models import AssociationRule, Cluster, ClusterMembership
from catalog.models import TransactionDetail

MIN_TRANSAKSI = 10   
GRID_SUPPORT = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.40]
GRID_CONFIDENCE = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
DEFAULT_MIN_SUPPORT = 0.02
DEFAULT_MIN_CONFIDENCE = 0.6


def tentukan_periode(tipe, tanggal_akhir_data, mulai=None, selesai=None, tanggal_awal_data=None):
    """tipe: 'seluruh' | '12_bulan' | '6_bulan' | 'custom'"""
    if tipe == "seluruh":
        return tanggal_awal_data, tanggal_akhir_data
    if tipe in ("12_bulan", "6_bulan"):
        bulan = 12 if tipe == "12_bulan" else 6
        awal = (pd.Timestamp(tanggal_akhir_data) - pd.DateOffset(months=bulan) + timedelta(days=1)).date()
        return awal, tanggal_akhir_data
    if tipe == "custom":
        if not mulai or not selesai or mulai > selesai:
            raise ValueError("Periode custom: tanggal mulai dan selesai harus diisi dan mulai <= selesai.")
        return mulai, selesai
    raise ValueError("Tipe periode tidak dikenal.")


def ambil_keranjang(awal, akhir):
    """Satu baris = satu produk dalam satu faktur, pada periode terpilih."""
    qs = TransactionDetail.objects.filter(
        transaction__transaction_date__gte=awal, transaction__transaction_date__lte=akhir
    ).values_list("transaction_id", "transaction__customer_id", "product_id")
    return pd.DataFrame(list(qs), columns=["trx", "pelanggan", "produk"])


def keanggotaan_tegas():
    """Klaster tiap pelanggan = klaster dengan derajat keanggotaan tertinggi."""
    m = pd.DataFrame(
        list(ClusterMembership.objects.values_list("customer_id", "cluster_id", "membership_degree")),
        columns=["pelanggan", "klaster", "derajat"])
    return m.sort_values("derajat", ascending=False).drop_duplicates("pelanggan").set_index("pelanggan")["klaster"]


def tambang_aturan(df_klaster, min_support, min_confidence):
    """df_klaster: kolom trx, produk (satu klaster). Return DataFrame aturan (bisa kosong)."""
    keranjang = pd.crosstab(df_klaster["trx"], df_klaster["produk"]).astype(bool)
    itemset = fpgrowth(keranjang, min_support=min_support, use_colnames=True)
    if itemset.empty or (itemset["itemsets"].map(len) >= 2).sum() == 0:
        return pd.DataFrame()
    aturan = association_rules(itemset, metric="confidence", min_threshold=min_confidence)
    return aturan[["antecedents", "consequents", "support", "confidence", "lift"]]


def _rentang_data():
    t = pd.DataFrame(
        list(TransactionDetail.objects.values_list("transaction__transaction_date", flat=True)),
        columns=["t"])["t"]
    return t.min(), t.max()


def jalankan_fpgrowth(min_support=DEFAULT_MIN_SUPPORT, min_confidence=DEFAULT_MIN_CONFIDENCE, tipe_periode="seluruh",
                      mulai=None, selesai=None, simpan=True):
    awal_data, akhir_data = _rentang_data()
    awal, akhir = tentukan_periode(tipe_periode, akhir_data, mulai, selesai, awal_data)

    df = ambil_keranjang(awal, akhir)
    df["klaster"] = df["pelanggan"].map(keanggotaan_tegas())

    hasil = {}
    for cl in Cluster.objects.order_by("cluster_number"):
        d = df[df["klaster"] == cl.cluster_id]
        n_trx = d["trx"].nunique()
        if n_trx < MIN_TRANSAKSI:
            hasil[cl] = {"transaksi": n_trx, "aturan": pd.DataFrame(),
                         "keterangan": "Transaksi pada periode ini tidak cukup untuk membentuk aturan asosiasi."}
            continue
        aturan = tambang_aturan(d, min_support, min_confidence)
        hasil[cl] = {"transaksi": n_trx, "aturan": aturan,
                     "keterangan": None if len(aturan) else
                     "Tidak ada aturan yang memenuhi nilai minimum support dan minimum confidence."}

    if simpan:
        with db_transaction.atomic():
            AssociationRule.objects.all().delete()
            baris = []
            for cl, h in hasil.items():
                for r in h["aturan"].itertuples():
                    baris.append(AssociationRule(
                        cluster=cl, antecedent=", ".join(sorted(r.antecedents)),
                        consequent=", ".join(sorted(r.consequents)),
                        support=float(r.support), confidence=float(r.confidence), lift_ratio=float(r.lift),
                        min_support=min_support, min_confidence=min_confidence,
                        period_type=tipe_periode, period_start=awal, period_end=akhir))
            AssociationRule.objects.bulk_create(baris)
    return {"periode": (awal, akhir), "hasil": hasil}


def uji_sensitivitas():
    """Jumlah aturan tiap kombinasi support x confidence pada setiap klaster (seluruh periode).
    Nilai bawaan = nilai terbesar yang masih menyisakan >= 25% aturan dari kombinasi paling longgar
    (1% / 30%), dan syarat itu harus terpenuhi di SEMUA klaster."""
    df = ambil_keranjang(*_rentang_data())
    df["klaster"] = df["pelanggan"].map(keanggotaan_tegas())
    tabel = {}
    for cl in Cluster.objects.order_by("cluster_number"):
        d = df[df["klaster"] == cl.cluster_id]
        for s in GRID_SUPPORT:
            for c in GRID_CONFIDENCE:
                tabel[(cl.cluster_number, s, c)] = len(tambang_aturan(d, s, c))
    klaster = sorted({k[0] for k in tabel})
    longgar = {k: tabel[(k, GRID_SUPPORT[0], GRID_CONFIDENCE[0])] for k in klaster}

    def lolos(s, c):
        return all(longgar[k] > 0 and tabel[(k, s, c)] >= 0.25 * longgar[k] for k in klaster)

    s_pilih = max([s for s in GRID_SUPPORT if lolos(s, GRID_CONFIDENCE[0])], default=GRID_SUPPORT[0])
    c_pilih = max([c for c in GRID_CONFIDENCE if lolos(s_pilih, c)], default=GRID_CONFIDENCE[0])
    return tabel, s_pilih, c_pilih