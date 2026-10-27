from django.core.management.base import BaseCommand

from analytics.services.fpgrowth import jalankan_fpgrowth, uji_sensitivitas, GRID_SUPPORT, GRID_CONFIDENCE


class Command(BaseCommand):
    help = "Uji sensitivitas lalu jalankan FP-Growth per klaster"

    def add_arguments(self, parser):
        parser.add_argument("--support", type=float)
        parser.add_argument("--confidence", type=float)
        parser.add_argument("--periode", default="seluruh", choices=["seluruh", "12_bulan", "6_bulan"])

    def handle(self, *args, **o):
        tabel, s_pilih, c_pilih = uji_sensitivitas()
        klaster = sorted({k[0] for k in tabel})
        for k in klaster:
            self.stdout.write(f"\nJumlah aturan, klaster {k} (baris = min support, kolom = min confidence)")
            self.stdout.write("      " + "".join(f"{int(c*100):>6}%" for c in GRID_CONFIDENCE))
            for s in GRID_SUPPORT:
                self.stdout.write(f"{int(s*100):>4}% " + "".join(f"{tabel[(k, s, c)]:>7}" for c in GRID_CONFIDENCE))
        self.stdout.write(f"\nNilai bawaan hasil uji sensitivitas: support={s_pilih}, confidence={c_pilih}")

        s = o["support"] or s_pilih
        c = o["confidence"] or c_pilih
        h = jalankan_fpgrowth(s, c, o["periode"])
        self.stdout.write(f"\nFP-Growth: support={s}, confidence={c}, periode={h['periode'][0]} s/d {h['periode'][1]}")
        for cl, x in h["hasil"].items():
            self.stdout.write(f"{cl.loyalty_label}: {x['transaksi']} transaksi, {len(x['aturan'])} aturan"
                              + (f" - {x['keterangan']}" if x["keterangan"] else ""))
            for r in x["aturan"].sort_values("lift", ascending=False).head(3).itertuples():
                self.stdout.write(f"   {', '.join(sorted(r.antecedents))} -> {', '.join(sorted(r.consequents))} "
                                  f"(sup {r.support:.3f}, conf {r.confidence:.2f}, lift {r.lift:.2f})")