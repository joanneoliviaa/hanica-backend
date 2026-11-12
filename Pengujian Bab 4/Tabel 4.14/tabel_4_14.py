"""
Tabel 4.14 Rekomendasi Strategi CRM untuk Setiap Klaster
Membaca rekomendasi yang tersimpan di aplikasi (halaman Rekomendasi Strategi CRM) dan memeriksa
kesesuaiannya dengan tabel skenario CRM.
Jalankan:  python "Pengujian Bab 4/Tabel 4.14/tabel_4_14.py"
"""
import re
import sys
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

from analytics.models import CrmScenario, Recommendation  # noqa: E402

rek = list(Recommendation.objects.select_related("cluster", "scenario").order_by("-cluster__loyalty_score"))
if not rek:
    raise SystemExit("Belum ada rekomendasi. Buka halaman Rekomendasi Strategi CRM di aplikasi dulu.")

rows, cek = [], []
for r in rek:
    rows.append([r.cluster.loyalty_label, r.strategy_text])
    skenario_seharusnya = CrmScenario.objects.get(loyalty_label=r.cluster.loyalty_label)
    lengkap = all(t.strip() for t in (r.characteristics_text, r.strategy_text, r.reason_text))
    ada_bukti = "lift" in r.reason_text.lower()
    cek.append([r.cluster.loyalty_label,
                "Sesuai" if r.scenario_id == skenario_seharusnya.scenario_id
                and r.strategy_text == skenario_seharusnya.description else "TIDAK sesuai",
                "Lengkap" if lengkap else "Tidak lengkap",
                "Ada" if ada_bukti else "Tidak ada"])

isi = [B.judul("Tabel 4.14 Rekomendasi Strategi CRM untuk Setiap Klaster"),
       B.tabel(["Klaster", "Strategi yang Direkomendasikan"], rows, [3.5, 13], rata_kiri=(1,))]
isi += B.catatan("Teks strategi diambil langsung dari rekomendasi yang tersimpan di aplikasi.")
isi += [B.Spacer(1, 14), B.Paragraph("Pemeriksaan kesesuaian rekomendasi", B.SUBJUDUL),
        B.tabel(["Klaster", "Strategi = skenario CRM label tsb.", "Narasi (karakteristik, strategi, alasan)",
                 "Aturan asosiasi sebagai bukti"], cek, [3.5, 4.3, 4.6, 4.1])]
isi += [B.PageBreak(), B.Paragraph("Narasi rekomendasi lengkap yang ditampilkan sistem", B.SUBJUDUL)]
for r in rek:
    isi += [B.Paragraph(f"<b>{r.cluster.loyalty_label}</b>", B.BIASA), B.Spacer(1, 3),
            B.tabel(["Bagian", "Isi"], [["Karakteristik", r.characteristics_text], ["Strategi", r.strategy_text],
                                         ["Alasan", r.reason_text]], [3, 13.5], rata_kiri=(0, 1), ukuran=9),
            B.Spacer(1, 10)]
B.simpan_pdf(SINI / "Tabel 4.14.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
