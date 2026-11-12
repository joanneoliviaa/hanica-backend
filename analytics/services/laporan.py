from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from analytics.models import ClusterMembership, Recommendation, RfmValue
from .rekomendasi import angka, bukti_aturan

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def _produk(teks, sel):
    """Satu produk per baris dengan penanda bullet, supaya kombinasi >2 produk mudah dibaca."""
    gaya = ParagraphStyle("produk", parent=sel, leftIndent=8, bulletIndent=0, spaceAfter=2)
    return [Paragraph(escape(p), gaya, bulletText="\u2022") for p in teks.split(", ")]


def rupiah(x):
    return "Rp " + f"{x:,.0f}".replace(",", ".")


def _pelanggan_per_klaster():
    """Anggota tiap klaster berdasarkan derajat keanggotaan tertinggi (sama dengan halaman Segmentasi)."""
    tertinggi = {}
    for m in ClusterMembership.objects.all():
        lama = tertinggi.get(m.customer_id)
        if lama is None or m.membership_degree > lama[1]:
            tertinggi[m.customer_id] = (m.cluster_id, m.membership_degree)
    rfm_nilai = {r.customer_id: r for r in RfmValue.objects.select_related("customer")}
    hasil = {}
    for pelanggan, (klaster, derajat) in tertinggi.items():
        r = rfm_nilai.get(pelanggan)
        if r is not None:
            hasil.setdefault(klaster, []).append((r, derajat))
    for daftar in hasil.values():
        daftar.sort(key=lambda x: (-x[1], x[0].customer.customer_name))
    return hasil


def _tabel_pelanggan(daftar, sel):
    baris = [["No", "ID", "Nama Pelanggan", "Status", "R (hari)", "F", "M", "Derajat"]]
    for i, (r, derajat) in enumerate(daftar, 1):
        baris.append([str(i), r.customer_id, Paragraph(escape(r.customer.customer_name), sel),
                      Paragraph(escape(r.activity_status), sel), str(r.recency), str(r.frequency),
                      rupiah(r.monetary), angka(derajat * 100) + "%"])
    t = Table(baris, colWidths=[0.8 * cm, 2.4 * cm, 4.7 * cm, 2.0 * cm, 1.4 * cm, 0.9 * cm, 3.0 * cm, 1.6 * cm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "RIGHT")]))
    return t


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

    anggota = _pelanggan_per_klaster()
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
                baris.append([_produk(a.antecedent, sel), _produk(a.consequent, sel),
                              angka(a.support * 100) + "%", angka(a.confidence * 100) + "%", angka(a.lift_ratio, 2)])
            t = Table(baris, colWidths=[5.6 * cm, 5.6 * cm, 1.8 * cm, 2.1 * cm, 1.4 * cm], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 1), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, -1), 4)]))
            isi_dok.append(Spacer(1, 4))
            isi_dok.append(t)
        daftar = anggota.get(r.cluster_id, [])
        isi_dok.append(Paragraph(f"Daftar Pelanggan dalam Segmen ({len(daftar)} pelanggan)", h3))
        if daftar:
            isi_dok.append(Paragraph(
                "Pelanggan dimasukkan ke segmen dengan derajat keanggotaan tertingginya; "
                "diurutkan dari derajat keanggotaan terbesar. R = recency, F = frequency, M = monetary.", sel))
            isi_dok.append(Spacer(1, 4))
            isi_dok.append(_tabel_pelanggan(daftar, sel))
        else:
            isi_dok.append(Paragraph("Tidak ada pelanggan pada segmen ini.", isi))
        isi_dok.append(Spacer(1, 10))
    dok.build(isi_dok)
    return buf.getvalue()