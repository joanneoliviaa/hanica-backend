from django.urls import path

from . import views

urlpatterns = [
    path("dashboard", views.dashboard),
    path("segmentation/run", views.jalankan_segmentasi),
    path("segmentation", views.hasil_segmentasi),
    path("patterns/sensitivity", views.sensitivitas),
    path("patterns", views.analisis_pola),
    path("recommendations/generate", views.buat_rekomendasi),
    path("recommendations", views.daftar_rekomendasi),
    path("report/pdf", views.unduh_laporan),
]