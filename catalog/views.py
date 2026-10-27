from datetime import date
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import Transaction, TransactionDetail, UploadHistory
from catalog.services.importer import proses_upload
from catalog.services.preprocessing import PreprocessingError


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_data(request):
    berkas = request.FILES.get("file")
    if berkas is None:
        return Response({"detail": "Berkas belum dipilih."}, status=status.HTTP_400_BAD_REQUEST)
    if not berkas.name.lower().endswith((".xlsx", ".xls")):
        return Response({"detail": "Format berkas harus .xlsx."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        laporan = proses_upload(berkas, request.user)
    except PreprocessingError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": "Data berhasil diunggah dan dibersihkan.", "ringkasan": laporan})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riwayat_upload(request):
    data = [
        {"nama_berkas": u.file_name, "tanggal": u.upload_date, "pengunggah": u.user.username, "status": u.status}
        for u in UploadHistory.objects.select_related("user").order_by("-upload_date")
    ]
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daftar_transaksi(request):
    """Data transaksi bersih yang tersimpan di sistem (per baris produk), dengan pencarian dan halaman."""
    p = request.query_params
    try:
        halaman = max(int(p.get("page", 1)), 1)
        per_halaman = min(max(int(p.get("per_page", 25)), 1), 100)
        dari = date.fromisoformat(p["dari"]) if p.get("dari") else None
        sampai = date.fromisoformat(p["sampai"]) if p.get("sampai") else None
    except ValueError:
        return Response({"detail": "Parameter tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

    qs = TransactionDetail.objects.select_related("transaction__customer", "product")
    q = p.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(transaction__transaction_id__icontains=q)
            | Q(transaction__customer__customer_name__icontains=q)
            | Q(transaction__customer__customer_id__icontains=q)
            | Q(product__product_name__icontains=q)
        )
    if dari:
        qs = qs.filter(transaction__transaction_date__gte=dari)
    if sampai:
        qs = qs.filter(transaction__transaction_date__lte=sampai)
    qs = qs.order_by("-transaction__transaction_date", "transaction__transaction_id", "product__product_name", "detail_id")

    jumlah = qs.count()
    awal = (halaman - 1) * per_halaman
    baris = [
        {
            "tanggal": d.transaction.transaction_date,
            "no_faktur": d.transaction.transaction_id,
            "kode_pelanggan": d.transaction.customer_id,
            "pelanggan": d.transaction.customer.customer_name,
            "produk": d.product_id,
            "qty": d.quantity,
            "satuan": d.unit,
            "harga": d.price,
            "subtotal": d.subtotal,
        }
        for d in qs[awal:awal + per_halaman]
    ]
    return Response({
        "jumlah_baris": jumlah,
        "jumlah_baris_total": TransactionDetail.objects.count(),
        "jumlah_transaksi_total": Transaction.objects.count(),
        "halaman": halaman,
        "per_halaman": per_halaman,
        "jumlah_halaman": max((jumlah + per_halaman - 1) // per_halaman, 1),
        "data": baris,
    })