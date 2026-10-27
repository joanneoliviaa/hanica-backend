from django.core.management.base import BaseCommand

from analytics.services.rfm import hitung_rfm, simpan_rfm


class Command(BaseCommand):
    help = "Hitung nilai RFM semua pelanggan dan simpan ke database"

    def handle(self, *args, **opts):
        hasil, acuan = hitung_rfm()
        simpan_rfm(hasil)
        self.stdout.write(f"Tanggal acuan: {acuan.date()}")
        self.stdout.write(f"Jumlah pelanggan: {len(hasil)}")
        self.stdout.write(hasil["activity_status"].value_counts().to_string())
        self.stdout.write(hasil[["recency", "frequency", "monetary"]].describe().round(2).to_string())