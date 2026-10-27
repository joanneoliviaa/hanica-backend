import uuid

from django.conf import settings
from django.db import models


class Customer(models.Model):
    """Tabel 3.9 — data master pelanggan."""

    customer_id = models.CharField(max_length=20, primary_key=True)
    customer_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.customer_id} - {self.customer_name}"


class Product(models.Model):
    """Tabel 3.11 — nama produk hasil standarisasi."""

    product_name = models.CharField(max_length=255, primary_key=True)

    def __str__(self):
        return self.product_name


class Transaction(models.Model):
    """Tabel 3.10 — data faktur (satu faktur = satu transaksi)."""

    transaction_id = models.CharField(max_length=30, primary_key=True)
    transaction_date = models.DateField()
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="transactions"
    )

    def __str__(self):
        return self.transaction_id


class TransactionDetail(models.Model):
    """Tabel 3.12 — rincian produk per faktur (perantara Transaction <-> Product)."""

    detail_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="details"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="transaction_details"
    )
    # FloatField (bukan Integer): 15 baris data asli punya Qty pecahan, mis. 116,5 / 446,01 KG
    quantity = models.FloatField()
    unit = models.CharField(max_length=10, null=True, blank=True)
    price = models.FloatField()
    subtotal = models.FloatField()

    def __str__(self):
        return f"{self.transaction_id} - {self.product_id}"


class UploadHistory(models.Model):
    """Tabel 3.8 — riwayat unggahan data transaksi."""

    STATUS_CHOICES = [("berhasil", "Berhasil"), ("gagal", "Gagal")]

    upload_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploads"
    )
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.file_name} ({self.status})"