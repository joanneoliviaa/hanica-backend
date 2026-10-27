import pandas as pd
from django.db import transaction as db_transaction

from analytics.models import Cluster
from catalog.models import Customer, Product, Transaction, TransactionDetail, UploadHistory
from .preprocessing import praproses, PreprocessingError


def simpan_ke_database(hasil):
    """Hapus data transaksi lama, lalu isi ulang dari hasil praproses."""
    with db_transaction.atomic():
        Cluster.objects.all().delete()  
        TransactionDetail.objects.all().delete()
        Transaction.objects.all().delete()
        Customer.objects.all().delete()
        Product.objects.all().delete()

        pelanggan = hasil.drop_duplicates("kode_pelanggan")[["kode_pelanggan", "nama_pelanggan"]]
        Customer.objects.bulk_create(
            [Customer(customer_id=r.kode_pelanggan, customer_name=r.nama_pelanggan)
             for r in pelanggan.itertuples()]
        )
        Product.objects.bulk_create(
            [Product(product_name=n) for n in hasil["produk"].unique()]
        )
        trx = hasil.drop_duplicates("id_transaksi")[["id_transaksi", "tanggal", "kode_pelanggan"]]
        Transaction.objects.bulk_create(
            [Transaction(transaction_id=r.id_transaksi, transaction_date=r.tanggal.date(),
                         customer_id=r.kode_pelanggan)
             for r in trx.itertuples()]
        )
        TransactionDetail.objects.bulk_create(
            [TransactionDetail(
                transaction_id=r.id_transaksi, product_id=r.produk,
                quantity=float(r.qty), unit=r.satuan if isinstance(r.satuan, str) else None,
                price=float(r.harga), subtotal=float(r.subtotal))
             for r in hasil.itertuples()],
            batch_size=1000,
        )


def proses_upload(file, user):
    nama_file = getattr(file, "name", "upload.xlsx")
    try:
        df = pd.read_excel(file, sheet_name=0)
        hasil, laporan = praproses(df)
        simpan_ke_database(hasil)
    except Exception as e:
        UploadHistory.objects.create(user=user, file_name=nama_file, status="gagal")
        if isinstance(e, PreprocessingError):
            raise
        raise PreprocessingError(
            "Berkas tidak dapat dibaca atau formatnya tidak sesuai. "
            "Pastikan berkas adalah ekspor Excel (.xlsx) dari Accurate."
        )
    UploadHistory.objects.create(user=user, file_name=nama_file, status="berhasil")
    return laporan