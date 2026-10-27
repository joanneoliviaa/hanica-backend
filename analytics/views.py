from datetime import date, timedelta

import numpy as np
from django.db.models import Count, Max, Min, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from analytics.models import AssociationRule, Cluster, ClusterMembership, Recommendation, RfmValue
from analytics.services import fcm, fpgrowth, laporan, rekomendasi, rfm
from catalog.models import Customer, Transaction, TransactionDetail

_cache_sensitivitas = {}

def _silhouette_optimal(k):
    """Nilai Silhouette untuk k terbaik"""
    if "silhouette" not in _cache_sensitivitas:
        rfm_nilai = sorted(RfmValue.objects.all(), key=lambda r: r.customer_id)
        X = np.array([[r.recency_norm, r.frequency_norm, r.monetary_norm] for r in rfm_nilai])
        _cache_sensitivitas["silhouette"] = fcm.evaluasi_k(X)[k]["silhouette"] if len (X) else None
    return _cache_sensitivitas["silhouette"]

def _status_per_klaster():
    tegas = fpgrowth.keanggotaan_tegas()
    rfm_nilai = {r.customer_id: r for r in RfmValue.objects.all()}
    hasil = {}
    for pelanggan, klaster in tegas.items():
        s = hasil.setdefault(klaster, {"Aktif": 0, "Kurang Aktif": 0, "Tidak Aktif": 0, "jumlah": 0})
        s[rfm_nilai[pelanggan].activity_status] += 1
        s["jumlah"] += 1
    return hasil


def _bentuk_klaster():
    per = _status_per_klaster()
    return [
        {"cluster_id": c.cluster_id, "nomor": c.cluster_number, "label": c.loyalty_label,
         "skor_loyalitas": c.loyalty_score, "pusat": c.centroid,
         "jumlah_pelanggan": per.get(c.cluster_id, {}).get("jumlah", 0),
         "status_keaktifan": {k: per.get(c.cluster_id, {}).get(k, 0) for k in ("Aktif", "Kurang Aktif", "Tidak Aktif")}}
        for c in Cluster.objects.order_by("cluster_number")
    ]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    if not Customer.objects.exists():
        return Response({"siap": False, "detail": "Belum ada data transaksi. Unggah data terlebih dahulu."})
    status_rfm = {s["activity_status"]: s["n"] for s in RfmValue.objects.values("activity_status").annotate(n=Count("pk"))}
    omzet = (TransactionDetail.objects.annotate(bulan=TruncMonth("transaction__transaction_date"))
             .values("bulan").annotate(total=Sum("subtotal")).order_by("bulan"))
    aturan_teratas = AssociationRule.objects.select_related("cluster").order_by("-lift_ratio")[:5]
    klaster = _bentuk_klaster()
    rentang = Transaction.objects.aggregate(a=Min("transaction_date"), b=Max("transaction_date"))
    return Response({
        "siap": True,
        "periode_data": {"mulai": rentang["a"], "selesai": rentang["b"],
                         "acuan": rentang["b"] + timedelta(days=1) if rentang["b"] else None}, 
        "silhouette_optimal": _silhouette_optimal(Cluster.objects.first().total_clusters) if klaster else None,
        "total_pelanggan": Customer.objects.count(),
        "status_keaktifan": {k: status_rfm.get(k, 0) for k in ("Aktif", "Kurang Aktif", "Tidak Aktif")},
        "total_transaksi": Transaction.objects.count(),
        "total_nilai_transaksi": TransactionDetail.objects.aggregate(t=Sum("subtotal"))["t"],
        "k_optimal": Cluster.objects.first().total_clusters if klaster else None,
        "pelanggan_per_segmen": [{"label": k["label"], "nomor": k["nomor"],
                                  "jumlah": k["jumlah_pelanggan"], "status_keaktifan": k["status_keaktifan"]} for k in klaster],
        "omzet_bulanan": [{"bulan": o["bulan"].strftime("%Y-%m"), "total": o["total"]} for o in omzet],
        "aturan_lift_tertinggi": [
            {"segmen": a.cluster.loyalty_label, "antecedent": a.antecedent, "consequent": a.consequent,
             "support": a.support, "confidence": a.confidence, "lift": a.lift_ratio} for a in aturan_teratas],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def jalankan_segmentasi(request):
    if not Customer.objects.exists():
        return Response({"detail": "Belum ada data transaksi."}, status=status.HTTP_400_BAD_REQUEST)
    hasil_rfm, acuan = rfm.hitung_rfm()
    rfm.simpan_rfm(hasil_rfm)
    hasil = fcm.jalankan_segmentasi()
    _cache_sensitivitas.clear()
    return Response({"detail": "Segmentasi selesai.", "tanggal_acuan": acuan.date(),
                     "k_optimal": hasil["k_optimal"], "silhouette": hasil["silhouette"]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hasil_segmentasi(request):
    if not Cluster.objects.exists() or not RfmValue.objects.exists():
        return Response({"siap": False, "detail": "Segmentasi belum dijalankan."})
    rfm_nilai = list(RfmValue.objects.select_related("customer").order_by("customer__customer_name"))
    X = [[r.recency_norm, r.frequency_norm, r.monetary_norm] for r in sorted(rfm_nilai, key=lambda r: r.customer_id)]
    evaluasi = fcm.evaluasi_k(np.array(X))
    klaster = Cluster.objects.order_by("cluster_number")
    anggota_klaster = {}
    for m in ClusterMembership.objects.all():
        anggota_klaster.setdefault(m.customer_id, {})[m.cluster_id] = m.membership_degree
    label_klaster = {c.cluster_id: c.loyalty_label for c in klaster}
    # daftar produk per pelanggan (seluruh data, sama dengan dasar product_variety)
    daftar_produk = {}
    for d in (TransactionDetail.objects
              .values("transaction__customer_id", "product_id")
              .annotate(faktur=Count("transaction_id", distinct=True))
              .order_by("transaction__customer_id", "-faktur", "product_id")):
        daftar_produk.setdefault(d["transaction__customer_id"], []).append(
            {"nama": d["product_id"], "jumlah_faktur": d["faktur"]})
    anggota = []
    for r in rfm_nilai:
        derajat = anggota_klaster.get(r.customer_id, {})
        tertinggi = max(derajat, key=derajat.get)
        anggota.append({
            "customer_id": r.customer_id, "nama": r.customer.customer_name,
            "recency": r.recency, "frequency": r.frequency, "monetary": r.monetary,
            "recency_norm": r.recency_norm, "frequency_norm": r.frequency_norm, "monetary_norm": r.monetary_norm,
            "status_keaktifan": r.activity_status, "segmen": label_klaster[tertinggi],
            "keanggotaan": {label_klaster[k]: round(v * 100, 1) for k, v in derajat.items()},
            "profil": {
                "transaksi_pertama": r.first_purchase_date, "transaksi_terakhir": r.last_purchase_date,
                "lama_berlangganan_hari": r.tenure_days, "rata_rata_nilai_faktur": r.avg_invoice_value,
                "jumlah_jenis_produk": r.product_variety, "produk_favorit": r.favorite_product,
                "daftar_produk": daftar_produk.get(r.customer_id, [])},
        })
    return Response({
        "siap": True, "k_optimal": klaster[0].total_clusters,
        "silhouette_per_k": {k: round(h["silhouette"], 4) for k, h in evaluasi.items()},
        "klaster": _bentuk_klaster(), "anggota": anggota,
    })

DEFAULT_MIN_SUPPORT = fpgrowth.DEFAULT_MIN_SUPPORT
DEFAULT_MIN_CONFIDENCE = fpgrowth.DEFAULT_MIN_CONFIDENCE

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sensitivitas(request):
    """Nilai default min support/confidence"""
    if not Cluster.objects.exists():
        return Response({"detail": "Segmentasi belum dijalankan."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({
        "min_support_default": DEFAULT_MIN_SUPPORT,
        "min_confidence_default": DEFAULT_MIN_CONFIDENCE,
        "tabel": [],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analisis_pola(request):
    d = request.data
    if not Cluster.objects.exists():
        return Response({"detail": "Segmentasi belum dijalankan."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        min_support = float(d.get("min_support", DEFAULT_MIN_SUPPORT))
        min_confidence = float(d.get("min_confidence", DEFAULT_MIN_CONFIDENCE))
        if not (0 < min_support <= 1 and 0 < min_confidence <= 1):
            raise ValueError("Minimum support dan confidence harus di antara 0 dan 1.")
        mulai = date.fromisoformat(d["start"]) if d.get("start") else None
        selesai = date.fromisoformat(d["end"]) if d.get("end") else None
        h = fpgrowth.jalankan_fpgrowth(min_support, min_confidence, d.get("period_type", "seluruh"), mulai, selesai)
    except (ValueError, TypeError) as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    segmen = d.get("segment")  # label klaster atau kosong = semua
    hasil = []
    for cl, x in h["hasil"].items():
        if segmen and segmen != cl.loyalty_label:
            continue
        aturan = x["aturan"].sort_values("lift", ascending=False) if len(x["aturan"]) else x["aturan"]
        hasil.append({
            "segmen": cl.loyalty_label, "jumlah_transaksi": x["transaksi"], "keterangan": x["keterangan"],
            "aturan": [{"antecedent": ", ".join(sorted(r.antecedents)), "consequent": ", ".join(sorted(r.consequents)),
                        "support": r.support, "confidence": r.confidence, "lift": r.lift}
                       for r in aturan.itertuples()]})
    return Response({"periode": {"mulai": h["periode"][0], "selesai": h["periode"][1]},
                     "min_support": min_support, "min_confidence": min_confidence, "hasil": hasil})


def _data_rekomendasi():
    data = []
    for r in Recommendation.objects.select_related("cluster", "scenario").order_by("cluster__cluster_number"):
        data.append({
            "segmen": r.cluster.loyalty_label, "skor_loyalitas": r.cluster.loyalty_score,
            "karakteristik": r.characteristics_text, "strategi": r.strategy_text, "alasan": r.reason_text,
            "bukti": [{"antecedent": a.antecedent, "consequent": a.consequent, "support": a.support,
                       "confidence": a.confidence, "lift": a.lift_ratio}
                      for a in rekomendasi.bukti_aturan(r.cluster, maks=10)],
        })
    return data


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buat_rekomendasi(request):
    if not Cluster.objects.exists():
        return Response({"detail": "Segmentasi belum dijalankan."}, status=status.HTTP_400_BAD_REQUEST)
    rekomendasi.susun_rekomendasi()
    return Response(_data_rekomendasi())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daftar_rekomendasi(request):
    return Response(_data_rekomendasi())

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unduh_laporan(request):
    pdf = laporan.buat_pdf(request.query_params.get("segment"))
    if pdf is None:
        return Response({"detail": "Rekomendasi belum dibuat untuk segmen ini."}, status=status.HTTP_404_NOT_FOUND)
    respons = HttpResponse(pdf, content_type="application/pdf")
    respons["Content-Disposition"] = 'attachment; filename="laporan-rekomendasi-crm.pdf"'
    return respons