from django.urls import path

from . import views

urlpatterns = [
    path("upload", views.upload_data),
    path("uploads", views.riwayat_upload),
    path("transactions", views.daftar_transaksi),
]