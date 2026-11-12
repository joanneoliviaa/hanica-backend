"""
Tabel 4.5 Perbandingan Hasil Perhitungan Manual dan Sistem
Menjalankan verifikasi_lampiran9.py (fungsi RFM, FCM, Silhouette, label loyalitas, dan FP-Growth
milik aplikasi, dengan data contoh Lampiran 9), lalu menyusun tabelnya ke PDF.
Jalankan:  python "Pengujian Bab 4/Tabel 4.5/tabel_4_5.py"
"""
import contextlib
import io
import os
import runpy
import re
import sys
import tempfile
from pathlib import Path

SINI = Path(__file__).resolve().parent
sys.path.insert(0, str(SINI.parent))
import _bersama as B  # noqa: E402

TOLERANSI = 0.0001

# ------------------------------------------------------------------ jalankan verifikasi asli
# dijalankan di folder sementara supaya file csv/xlsx bawaannya tidak berserakan
asal = os.getcwd()
with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
    os.chdir(tmp)
    try:
        g = runpy.run_path(str(B.FOLDER_APLIKASI / "verifikasi_lampiran9.py"))
    finally:
        os.chdir(asal)

fcm = g["fcm"]
t_eng = g["tabel_rfm"].loc["ENG-005"]
X, U_iter, V_iter, U_k3 = g["X"], g["U_iter"], g["V_iter"], g["U_k3"]
skor, label = g["skor"], g["label"]
aturan = g["aturan"]
G, Bk = g["G"], g["B"]


def rapat(nilai, n=4):
    return "; ".join(B.desimal(v, n) for v in nilai)


def baris(nama, manual, sistem, n=4, teks_manual=None, teks_sistem=None):
    manual, sistem = list(manual), [float(s) for s in sistem]
    selisih = [abs(round(s, n) - m) for m, s in zip(manual, sistem)]
    ok = all(s <= TOLERANSI + 1e-12 for s in selisih)
    return [nama, teks_manual or rapat(manual, n), teks_sistem or rapat([round(s, n) for s in sistem], n),
            "; ".join(B.desimal(s, 4) for s in selisih), "Sesuai" if ok else "TIDAK SESUAI"], ok


aturan_GB = aturan[(aturan["antecedents"] == frozenset([G])) & (aturan["consequents"] == frozenset([Bk]))]
s_gb, c_gb, l_gb = (float(aturan_GB[k].iloc[0]) for k in ("support", "confidence", "lift"))

rows, status = [], []
for r in [
    baris("RFM Engelina (R; F; M)", (1, 2, 10521195.41), (t_eng.recency, t_eng.frequency, t_eng.monetary), n=2,
          teks_manual="1; 2; 10.521.195,41",
          teks_sistem=f"{int(t_eng.recency)}; {int(t_eng.frequency)}; {B.desimal(t_eng.monetary, 2)}"),
    baris("RFM ternormalisasi Engelina (R; F; M)", (0, 1, 0),
          (t_eng.recency_norm, t_eng.frequency_norm, t_eng.monetary_norm)),
    baris("Pusat klaster V1 iterasi ke-1, k = 2 (R; F; M)", (0.0333, 0.4267, 0.1224), V_iter[1][0]),
    baris("Fungsi objektif iterasi ke-1 (k = 2)", (0.7732,), (g["fungsi_objektif"](U_iter[0], V_iter[1]),)),
    baris("Fungsi objektif iterasi ke-4 (k = 2)", (0.6236,), (g["fungsi_objektif"](U_iter[3], V_iter[4]),)),
    baris("μ Engelina terhadap klaster 1 (U<super>4</super>, k = 2)", (0.8461,), (U_iter[4][0, 0],)),
    baris("Silhouette Coefficient k = 2", (0.3617,), (fcm.silhouette(X, U_iter[4].argmax(axis=1)),)),
    baris("Silhouette Coefficient k = 3", (0.4270,), (fcm.silhouette(X, U_k3.argmax(axis=1)),)),
    baris("Skor loyalitas klaster 1, k = 3", (0.6666,), (skor[0],)),
]:
    rows.append(r[0]); status.append(r[1])

lab_sistem = "; ".join(label[k] for k in range(3))
ok = lab_sistem == "Tinggi; Rendah; Sedang"
rows.append(["Label loyalitas klaster 1, 2, 3 (k = 3)", "Tinggi; Rendah; Sedang", lab_sistem, "-",
             "Sesuai" if ok else "TIDAK SESUAI"]); status.append(ok)
sel = [abs(round(s_gb, 4) - 0.40), abs(round(c_gb, 4) - 0.50), abs(round(l_gb, 4) - 1.25)]
ok = all(s <= TOLERANSI + 1e-12 for s in sel)
rows.append(["Support, confidence, dan lift aturan G → B", "40%; 50%; 1,25",
             f"{B.desimal(s_gb * 100, 0)}%; {B.desimal(c_gb * 100, 0)}%; {B.desimal(l_gb, 2)}",
             "; ".join(B.desimal(s, 4) for s in sel), "Sesuai" if ok else "TIDAK SESUAI"]); status.append(ok)

# ------------------------------------------------------------------ PDF
df = g["df"]  # rincian lengkap dari verifikasi_lampiran9.py
selisih_maks = float(B.np.nanmax(B.np.array(
    [float(v) for v in df["Selisih"] if v != "-"] or [0.0])))
isi = [B.judul("Tabel 4.5 Perbandingan Hasil Perhitungan Manual dan Sistem"),
       B.tabel(["Nilai yang Diuji", "Hasil Manual", "Hasil Sistem", "Selisih", "Keterangan"], rows,
               [5.2, 3.3, 3.3, 2.4, 2.2], rata_kiri=(0,), ukuran=9.5)]
isi += B.catatan(
    f"Data: contoh Lampiran 9 (4 pelanggan, 5 faktur); U0 disamakan dengan Tabel L9.6 (k = 2) dan L9.22 (k = 3); "
    f"m = 2; batas maksimum iterasi 4; minimum support 40%; toleransi selisih {B.desimal(TOLERANSI, 4)}. "
    f"Hasil: {sum(status)} dari {len(status)} baris Sesuai.")

isi += [B.PageBreak(), B.Paragraph("Rincian seluruh nilai yang diverifikasi (keluaran verifikasi_lampiran9.py)",
                                  B.SUBJUDUL)]
rinci = []
for _, r in df.iterrows():
    fmt = lambda v: B.desimal(v, 4) if isinstance(v, (int, float)) else str(v)
    rinci.append([str(r["Tahap"]), str(r["Nilai yang Diuji"]), fmt(r["Hasil Manual"]), fmt(r["Hasil Sistem"]),
                  fmt(r["Selisih"]), str(r["Keterangan"])])
isi.append(B.tabel(["Tahap", "Nilai yang Diuji", "Manual", "Sistem", "Selisih", "Keterangan"], rinci,
                   [3.0, 5.4, 2.4, 2.4, 1.6, 2.0], rata_kiri=(0, 1), ukuran=8))
n_ok = int((df["Keterangan"] == "Sesuai").sum())
isi += B.catatan(f"Total nilai diuji: {len(df)}; Sesuai: {n_ok}; Tidak sesuai: {len(df) - n_ok}; "
                 f"selisih maksimum: {B.desimal(selisih_maks, 4)}.")

B.simpan_pdf(SINI / "Tabel 4.5.pdf", isi)
for r in rows:
    print(" | ".join(re.sub(r"<[^>]+>", "", str(v)) for v in r))
