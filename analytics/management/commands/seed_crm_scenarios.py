from django.core.management.base import BaseCommand

from analytics.models import CrmScenario

SCENARIOS = [
    {
        "loyalty_label": "Loyalitas Sangat Tinggi",
        "strategy_name": "Relasi Personal & Loyalitas Eksklusif",
        "description": (
            "Bangun program relasi personal dan loyalitas eksklusif seperti penawaran "
            "bundling produk. Prioritaskan kapasitas produksi dan jadwal pengiriman, "
            "berikan diskon volume terstruktur sesuai kebijakan ongkir."
        ),
    },
    {
        "loyalty_label": "Loyalitas Tinggi",
        "strategy_name": "Cross-Selling & Bundling Produk Komplementer",
        "description": (
            "Jalankan cross-selling/bundling produk komplementer untuk menaikkan "
            "rata-rata nilai pemesanan. Jaga komunikasi rutin dan catat preferensi "
            "produk tiap pelanggan."
        ),
    },
    {
        "loyalty_label": "Loyalitas Sedang",
        "strategy_name": "Reaktivasi Tertarget & Pemantauan Pelanggan Baru",
        "description": (
            "Prioritaskan reaktivasi tertarget dengan insentif khusus untuk pelanggan "
            "bernilai historis tinggi. Untuk pelanggan baru, investasi pemasaran minimum "
            "sambil dipantau pertumbuhannya."
        ),
    },
    {
        "loyalty_label": "Loyalitas Rendah",
        "strategy_name": "Komunikasi Minimal & Reaktivasi Terbatas",
        "description": (
            "Batasi biaya reaktivasi aktif, cukup komunikasi ringan/otomatis tanpa "
            "promosi khusus. Untuk pelanggan berisiko finansial, hentikan upaya "
            "reaktivasi."
        ),
    },
    {
        "loyalty_label": "Loyalitas Sangat Rendah",
        "strategy_name": "Deprioritasi & Alihkan ke Akuisisi Baru",
        "description": (
            "Deprioritaskan dari aktivitas pemasaran aktif. Alihkan sumber daya "
            "sepenuhnya untuk akuisisi pelanggan baru yang lebih potensial."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed 5 baris statis tabel Crm_Scenarios (Tabel 2.9 / 3.17 proposal)."

    def handle(self, *args, **options):
        created = updated = 0
        for row in SCENARIOS:
            _, was_created = CrmScenario.objects.update_or_create(
                loyalty_label=row["loyalty_label"],
                defaults={
                    "strategy_name": row["strategy_name"],
                    "description": row["description"],
                },
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(f"Selesai. {created} skenario dibuat, {updated} diperbarui.")
        )