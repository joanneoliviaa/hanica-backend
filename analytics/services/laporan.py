from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from analytics.models import Recommendation
from .rekomendasi import angka, bukti_aturan

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def buat_pdf(segmen=None):
    qs = Recommendation.objects.select_related("cluster").order_by("cluster__cluster_number")
    if segmen:
        qs = qs.filter(cluster__loyalty_label=segmen)
    rekomendasi = list(qs)
    if not rekomendasi:
        return None

    gaya = getSampleStyleSheet()
    judul = ParagraphStyle("judul", parent=gaya["Title"], fontSize=17, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=gaya["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=14)
    h2 = ParagraphStyle("h2", parent=gaya["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=4, keepWithNext=1)
    h3 = ParagraphStyle("h3", parent=gaya["Heading3"], fontSize=10.5, spaceBefore=8, spaceAfter=2, keepWithNext=1)
    isi = ParagraphStyle("isi", parent=gaya["Normal"], fontSize=9.5, leading=13.5)
    sel = ParagraphStyle("sel", parent=gaya["Normal"], fontSize=8, leading=10)

    hari_ini = date.today()
    buf = BytesIO()
    dok = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title="Laporan Rekomendasi Strategi CRM")
    isi_dok = [
        Paragraph("Laporan Rekomendasi Strategi CRM", judul),
        Paragraph(f"PT Hanica Sukses Makmur · Dibuat {hari_ini.day} {BULAN[hari_ini.month - 1]} {hari_ini.year}", sub),
    ]
    for r in rekomendasi:
        isi_dok.append(Paragraph(f"{escape(r.cluster.loyalty_label)}", h2))
        isi_dok.append(Paragraph("Karakteristik Pelanggan", h3))
        isi_dok.append(Paragraph(escape(r.characteristics_text), isi))
        isi_dok.append(Paragraph("Strategi yang Direkomendasikan", h3))
        isi_dok.append(Paragraph(escape(r.strategy_text), isi))
        isi_dok.append(Paragraph("Alasan Rekomendasi", h3))
        isi_dok.append(Paragraph(escape(r.reason_text), isi))
        aturan = bukti_aturan(r.cluster, maks=5)
        if aturan:
            isi_dok.append(Paragraph("Bukti Pendukung Pola Pembelian", h3))
            baris = [["Jika membeli", "Maka juga membeli", "Support", "Confidence", "Lift"]]
            for a in aturan:
                baris.append([Paragraph(escape(a.antecedent), sel), Paragraph(escape(a.consequent), sel),
                              angka(a.support * 100) + "%", angka(a.confidence * 100) + "%", angka(a.lift_ratio, 2)])
            t = Table(baris, colWidths=[5.6 * cm, 5.6 * cm, 1.8 * cm, 2.1 * cm, 1.4 * cm], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
            isi_dok.append(Spacer(1, 4))
            isi_dok.append(t)
        isi_dok.append(Spacer(1, 10))
    dok.build(isi_dok)
    return buf.getvalue()