from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalog.services.importer import proses_upload


class Command(BaseCommand):
    help = "Impor file Excel penjualan (Accurate) ke database"

    def add_arguments(self, parser):
        parser.add_argument("path", help="Lokasi file .xlsx")

    def handle(self, *args, **opts):
        user = get_user_model().objects.filter(is_superuser=True).first()
        laporan = proses_upload(opts["path"], user)
        for k, v in laporan.items():
            self.stdout.write(f"{k}: {v}")