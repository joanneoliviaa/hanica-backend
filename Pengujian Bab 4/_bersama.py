"""
Modul bersama untuk semua script di folder "Pengujian Bab 4".
Tidak perlu dijalankan langsung. Isinya:
  - menyambungkan script ke aplikasi Django (database yang sama dengan aplikasi),
  - format angka gaya Indonesia,
  - pembuat PDF tabel,
  - FCM dengan riwayat fungsi objektif (identik dengan analytics/services/fcm.py).
"""
import os
import sys
from pathlib import Path

FOLDER_PENGUJIAN = Path(__file__).resolve().parent
FOLDER_APLIKASI = FOLDER_PENGUJIAN.parent
sys.path.insert(0, str(FOLDER_APLIKASI))
os.chdir(FOLDER_APLIKASI)  # supaya pengaturan Django membaca .env/db yang sama dengan aplikasi

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

import numpy as np  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4, landscape  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from analytics.services import fcm  # noqa: E402

# ============================================================================ format angka
def desimal(x, n=4):
    """1234.5678 -> '1.234,5678'"""
    return f"{x:,.{n}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def bulat(x):
    return f"{x:,.0f}".replace(",", ".")


def persen(x, n=2):
    """0.0310 -> '3,10%'"""
    return desimal(x * 100, n) + "%"


def rupiah(x, n=2):
    return desimal(x, n) if n else bulat(x)


# ============================================================================ gaya PDF
_ss = getSampleStyleSheet()
JUDUL = ParagraphStyle("judul", parent=_ss["Normal"], fontName="Times-Bold", fontSize=12,
                       alignment=TA_CENTER, spaceAfter=8, leading=15)
SUBJUDUL = ParagraphStyle("subjudul", parent=_ss["Normal"], fontName="Times-Bold", fontSize=11,
                          spaceBefore=6, spaceAfter=6, leading=14)
BIASA = ParagraphStyle("biasa", parent=_ss["Normal"], fontName="Times-Roman", fontSize=10, leading=13)
KECIL = ParagraphStyle("kecil", parent=BIASA, fontSize=9, leading=11.5)
SEL = ParagraphStyle("sel", parent=BIASA, alignment=TA_CENTER)
SEL_KIRI = ParagraphStyle("selkiri", parent=BIASA)
SEL_KEPALA = ParagraphStyle("selkepala", parent=BIASA, fontName="Times-Bold", alignment=TA_CENTER)


def p(teks, gaya=SEL):
    return Paragraph(str(teks), gaya)


def tabel(header, baris, lebar, rata_kiri=(), span=(), ukuran=10):
    """header: list teks; baris: list of list (teks atau Paragraph); lebar: list cm."""
    gaya_sel = ParagraphStyle("s", parent=SEL, fontSize=ukuran, leading=ukuran * 1.3)
    gaya_kiri = ParagraphStyle("sk", parent=SEL_KIRI, fontSize=ukuran, leading=ukuran * 1.3)
    gaya_kepala = ParagraphStyle("sh", parent=SEL_KEPALA, fontSize=ukuran, leading=ukuran * 1.3)
    data = [[Paragraph(h, gaya_kepala) for h in header]]
    for b in baris:
        data.append([
            v if not isinstance(v, str) else Paragraph(v, gaya_kiri if j in rata_kiri else gaya_sel)
            for j, v in enumerate(b)
        ])
    t = Table(data, colWidths=[w * cm for w in lebar], repeatRows=1)
    gaya = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    gaya += [("SPAN", a, b) for a, b in span]
    t.setStyle(TableStyle(gaya))
    return t


def simpan_pdf(path, isi, mendatar=False):
    ukuran = landscape(A4) if mendatar else A4
    SimpleDocTemplate(str(path), pagesize=ukuran, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm,
                      title=Path(path).stem).build(isi)
    print(f"PDF tersimpan: {path}")


def judul(teks):
    return Paragraph(teks, JUDUL)


def catatan(teks, gaya=KECIL):
    return [Spacer(1, 4), Paragraph(teks, gaya)]


# ============================================================================ data RFM & FCM
def ambil_rfm():
    """RfmValue diurutkan sama seperti aplikasi (customer_id), plus matriks X ternormalisasi."""
    from analytics.models import RfmValue

    rfm = list(RfmValue.objects.select_related("customer").order_by("customer_id"))
    if not rfm:
        raise SystemExit("Tabel RFM kosong. Jalankan perhitungan RFM di aplikasi dulu.")
    X = np.array([[r.recency_norm, r.frequency_norm, r.monetary_norm] for r in rfm])
    return rfm, X


def fcm_dengan_riwayat(X, c, m=fcm.M, eps=fcm.EPSILON, max_iter=fcm.MAX_ITER, seed=fcm.SEED):
    """Langkahnya sama persis dengan fcm.fcm(), ditambah pencatatan fungsi objektif tiap iterasi."""
    n = len(X)
    rng = np.random.default_rng(seed)
    U = rng.dirichlet(np.ones(c), size=n)
    P_lama = 0.0
    riwayat = []
    for t in range(1, max_iter + 1):
        Um = U ** m
        V = (Um.T @ X) / Um.sum(axis=0)[:, None]
        D = np.fmax(fcm.jarak(X, V), 1e-12)
        P = float((Um * D ** 2).sum())
        riwayat.append(P)
        U = 1.0 / ((D[:, :, None] / D[:, None, :]) ** (2 / (m - 1))).sum(axis=2)
        if t > 1 and abs(P - P_lama) < eps:
            break
        P_lama = P
    Um = U ** m
    V = (Um.T @ X) / Um.sum(axis=0)[:, None]
    return U, V, t, riwayat


def hitung_fcm_semua(X, daftar_k=(2, 3, 4, 5)):
    hasil = {}
    for k in daftar_k:
        U, V, iterasi, riwayat = fcm_dengan_riwayat(X, k)
        U_app, V_app, it_app = fcm.fcm(X, k)
        assert it_app == iterasi and np.allclose(U, U_app) and np.allclose(V, V_app), \
            f"Hasil FCM k={k} berbeda dengan fcm.py, cek ulang!"
        P_akhir = float(((U ** fcm.M) * fcm.jarak(X, V) ** 2).sum())
        hasil[k] = {"U": U, "V": V, "iterasi": iterasi, "riwayat": riwayat, "P_akhir": P_akhir}
    return hasil


def urutan_recency(V):
    """Indeks klaster diurutkan dari pusat Recency terkecil (V1, V2, ...)."""
    return list(np.argsort(V[:, 0]))


def interpretasi_silhouette(s):
    """Tabel 4.3"""
    if s > 0.70:
        return "Struktur kuat"
    if s > 0.50:
        return "Struktur baik"
    if s > 0.25:
        return "Struktur lemah"
    return "Struktur buruk"


def indeks_validitas(X, label):
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score

    return {"silhouette": fcm.silhouette(X, label),
            "dbi": davies_bouldin_score(X, label),
            "chi": calinski_harabasz_score(X, label)}


def rapikan_produk(nama):
    """'CUP 10 OZ TINGGI / HANICA / @2.000 PCS' -> 'Cup 10 Oz Tinggi / Hanica'"""
    bagian = [b.strip() for b in str(nama).split("/") if not b.strip().startswith("@")]
    teks = " / ".join(bagian)
    return teks.title() if teks.isupper() else teks


__all__ = [
    "FOLDER_PENGUJIAN", "FOLDER_APLIKASI", "np", "cm", "Image", "KeepTogether", "PageBreak",
    "Paragraph", "Spacer", "desimal", "bulat", "persen", "rupiah", "p", "tabel", "simpan_pdf", "judul",
    "catatan", "SUBJUDUL", "BIASA", "KECIL", "SEL_KIRI", "ambil_rfm", "fcm_dengan_riwayat",
    "hitung_fcm_semua", "urutan_recency", "interpretasi_silhouette", "indeks_validitas",
    "rapikan_produk", "fcm",
]
