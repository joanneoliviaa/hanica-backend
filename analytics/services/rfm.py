from datetime import timedelta

import pandas as pd
from django.db import transaction as db_transaction

from analytics.models import RfmValue
from catalog.models import Customer, TransactionDetail


def status_aktivitas(recency):
    if recency <= 30:
        return "Aktif"
    if recency <= 180:
        return "Kurang Aktif"
    return "Tidak Aktif"


def minmax(seri):
    selisih = seri.max() - seri.min()
    if selisih == 0:
        return seri * 0
    return (seri - seri.min()) / selisih


def hitung_rfm(tanggal_mulai=None, tanggal_akhir=None):
    """Hitung RFM semua pelanggan pada rentang tanggal tertentu (default: seluruh data)."""
    qs = TransactionDetail.objects.select_related("transaction")
    if tanggal_mulai:
        qs = qs.filter(transaction__transaction_date__gte=tanggal_mulai)
    if tanggal_akhir:
        qs = qs.filter(transaction__transaction_date__lte=tanggal_akhir)
    df = pd.DataFrame(list(qs.values(
        "transaction_id", "transaction__transaction_date", "transaction__customer_id",
        "product_id", "subtotal",
    )))
    if df.empty:
        raise ValueError("Tidak ada transaksi pada periode ini.")
    df.columns = ["trx", "tanggal", "pelanggan", "produk", "subtotal"]
    df["tanggal"] = pd.to_datetime(df["tanggal"])

    # tanggal acuan = sehari setelah transaksi terakhir pada periode
    acuan = df["tanggal"].max() + timedelta(days=1)

    per_trx = df.groupby(["pelanggan", "trx"]).agg(
        tanggal=("tanggal", "first"), nilai=("subtotal", "sum")).reset_index()
    g = per_trx.groupby("pelanggan")
    hasil = pd.DataFrame({
        "recency": (acuan - g["tanggal"].max()).dt.days,
        "frequency": g["trx"].nunique(),
        "monetary": g["nilai"].sum(),
        "first_purchase_date": g["tanggal"].min(),
        "last_purchase_date": g["tanggal"].max(),
    })
    hasil["tenure_days"] = (hasil["last_purchase_date"] - hasil["first_purchase_date"]).dt.days
    hasil["avg_invoice_value"] = hasil["monetary"] / hasil["frequency"]
    hasil["product_variety"] = df.groupby("pelanggan")["produk"].nunique()
    # produk favorit = produk yang muncul di faktur paling banyak
    favorit = (df.drop_duplicates(["pelanggan", "trx", "produk"])
               .groupby(["pelanggan", "produk"]).size().reset_index(name="n")
               .sort_values(["pelanggan", "n", "produk"], ascending=[True, False, True])
               .drop_duplicates("pelanggan").set_index("pelanggan")["produk"])
    hasil["favorite_product"] = favorit

    # normalisasi Min-Max
    hasil["recency_norm"] = minmax(hasil["recency"])
    hasil["frequency_norm"] = minmax(hasil["frequency"])
    hasil["monetary_norm"] = minmax(hasil["monetary"])
    hasil["composite_score"] = (
        (1 - hasil["recency_norm"]) + hasil["frequency_norm"] + hasil["monetary_norm"]
    ) / 3
    hasil["activity_status"] = hasil["recency"].map(status_aktivitas)
    return hasil, acuan


def simpan_rfm(hasil):
    with db_transaction.atomic():
        RfmValue.objects.all().delete()
        pelanggan = Customer.objects.in_bulk(list(hasil.index))
        RfmValue.objects.bulk_create([
            RfmValue(
                customer=pelanggan[kode],
                recency=int(r.recency), frequency=int(r.frequency), monetary=float(r.monetary),
                recency_norm=float(r.recency_norm), frequency_norm=float(r.frequency_norm),
                monetary_norm=float(r.monetary_norm), composite_score=float(r.composite_score),
                activity_status=r.activity_status,
                first_purchase_date=r.first_purchase_date.date(),
                last_purchase_date=r.last_purchase_date.date(),
                tenure_days=int(r.tenure_days), avg_invoice_value=float(r.avg_invoice_value),
                product_variety=int(r.product_variety), favorite_product=r.favorite_product,
            )
            for kode, r in hasil.iterrows()
        ])