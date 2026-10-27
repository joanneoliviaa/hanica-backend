from django.core.management.base import BaseCommand

from analytics.services.rekomendasi import susun_rekomendasi


class Command(BaseCommand):
    help = "Susun rekomendasi strategi CRM (3 narasi self-explainable) untuk tiap klaster"

    def handle(self, *args, **opts):
        for cl, k, s, a in susun_rekomendasi():
            self.stdout.write(f"\n=== {cl.loyalty_label} ===")
            self.stdout.write(f"[Karakteristik] {k}")
            self.stdout.write(f"[Strategi] {s}")
            self.stdout.write(f"[Alasan] {a}")