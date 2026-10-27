"""Bandingkan jumlah baris tiap tabel antara db.sqlite3 (lama) dan PostgreSQL (baru).
Jalankan dari folder Aplikasi:  python cek_migrasi_postgresql.py
"""
import os
import sqlite3

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.apps import apps
from django.db import connection

lama = sqlite3.connect("file:db.sqlite3?mode=ro", uri=True)
print(f"Database baru: {connection.vendor} / {connection.settings_dict['NAME']}\n")
print(f"{'Tabel':40} {'SQLite':>8} {'PostgreSQL':>11}")
semua_cocok = True
for label in ("accounts", "catalog", "analytics"):
    for model in apps.get_app_config(label).get_models():
        tabel = model._meta.db_table
        n_lama = lama.execute(f'SELECT COUNT(*) FROM "{tabel}"').fetchone()[0]
        n_baru = model.objects.count()
        tanda = "" if n_lama == n_baru else "  <-- BEDA"
        semua_cocok &= n_lama == n_baru
        print(f"{tabel:40} {n_lama:>8} {n_baru:>11}{tanda}")
print("\nSEMUA COCOK ✔" if semua_cocok else "\nADA YANG BEDA ✘ — kirim hasil ini ke Claude")
