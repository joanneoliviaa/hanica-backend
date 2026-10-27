import pandas as pd
from django.db import transaction

from catalog.models import Customer, Product, Invoice, InvoiceDetail

REQUIRED_COLUMNS = [
    "No Faktur", "Tanggal Faktur", "No Pelanggan", "Nama Pelanggan",
    "Nama Barang", "Qty", "Satuan", "Harga", "Dpp",
]


class ExcelImportError(Exception):
    pass


def import_sales_excel(file_obj):
    """Baca sheet 'Sheet1' dari file Excel penjualan dan simpan ke database.
    """
    try:
        df = pd.read_excel(file_obj, sheet_name="Sheet1")
    except ValueError as exc:
        raise ExcelImportError(f"Sheet 'Sheet1' tidak ditemukan: {exc}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ExcelImportError(f"Kolom wajib tidak ditemukan: {missing}")

    # Perbaikan kualitas data #1: Dpp kosong -> isi dengan Qty x Harga
    df["Dpp"] = df["Dpp"].fillna(df["Qty"] * df["Harga"])

    # Buang baris yang benar-benar kosong di kolom kunci
    df = df.dropna(subset=["No Faktur", "No Pelanggan", "Nama Barang"])

    stats = {
        "rows_processed": 0,
        "customers_created": 0,
        "invoices_created": 0,
        "products_created": 0,
        "details_created": 0,
        "skipped_rows": 0,
    }

    with transaction.atomic():
        for _, row in df.iterrows():
            try:
                customer_id = str(row["No Pelanggan"]).strip()
                customer, created = Customer.objects.get_or_create(
                    customer_id=customer_id,
                    defaults={"customer_name": str(row["Nama Pelanggan"]).strip()},
                )
                stats["customers_created"] += int(created)

                product_name = str(row["Nama Barang"]).strip()
                product, created = Product.objects.get_or_create(
                    product_name=product_name
                )
                stats["products_created"] += int(created)

                invoice_id = str(row["No Faktur"]).strip()
                invoice_date = pd.to_datetime(row["Tanggal Faktur"]).date()
                invoice, created = Invoice.objects.get_or_create(
                    invoice_id=invoice_id,
                    defaults={"invoice_date": invoice_date, "customer": customer},
                )
                stats["invoices_created"] += int(created)

                InvoiceDetail.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=int(row["Qty"]),
                    unit=str(row["Satuan"]) if pd.notna(row["Satuan"]) else None,
                    price=float(row["Harga"]),
                    subtotal=float(row["Dpp"]),
                )
                stats["details_created"] += 1
                stats["rows_processed"] += 1
            except Exception:
                stats["skipped_rows"] += 1
                continue

    return stats