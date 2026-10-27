# Hasil validasi sistem

## 1. RFM dan normalisasi Min-Max (hitung ulang dengan perulangan biasa, tanpa pandas)
  Tanggal acuan: 2026-07-01; jumlah pelanggan: sistem 133, hitung ulang 133
  [LOLOS] Jumlah pelanggan sama  
  [LOLOS] Recency identik untuk semua pelanggan  (beda: 0 pelanggan)
  [LOLOS] Frequency identik untuk semua pelanggan  (beda: 0 pelanggan)
  [LOLOS] Monetary identik  (selisih maks Rp0.0000)
  [LOLOS] R, F, M ternormalisasi identik  (selisih maks 5.55e-17)
  [LOLOS] Status keaktifan (<=30 / <=180 / >180 hari) sesuai  (salah: 0)

## 2. Fuzzy C-Means dan Silhouette (dibandingkan dengan scikit-fuzzy dan scikit-learn)
  | k | Silhouette sistem | Silhouette sklearn (label sistem) | Silhouette sklearn (FCM skfuzzy) | selisih pusat klaster maks |
  |---|---|---|---|---|
  | 2 | 0.5580 | 0.5580 | 0.5580 | 0.0003 |
  [LOLOS] k=2: fungsi silhouette sistem = sklearn pada label yang sama  
  [LOLOS] k=2: pusat klaster sistem ~ scikit-fuzzy (toleransi 0,02)  
  | 3 | 0.4772 | 0.4772 | 0.4812 | 0.0066 |
  [LOLOS] k=3: fungsi silhouette sistem = sklearn pada label yang sama  
  [LOLOS] k=3: pusat klaster sistem ~ scikit-fuzzy (toleransi 0,02)  
  | 4 | 0.4060 | 0.4060 | 0.4031 | 0.0089 |
  [LOLOS] k=4: fungsi silhouette sistem = sklearn pada label yang sama  
  [LOLOS] k=4: pusat klaster sistem ~ scikit-fuzzy (toleransi 0,02)  
  | 5 | 0.3378 | 0.3378 | 0.3406 | 0.0042 |
  [LOLOS] k=5: fungsi silhouette sistem = sklearn pada label yang sama  
  [LOLOS] k=5: pusat klaster sistem ~ scikit-fuzzy (toleransi 0,02)  
  [LOLOS] k optimal sama dengan hasil scikit-fuzzy + sklearn  (sistem k=2, pembanding k=2)
  [LOLOS] Derajat keanggotaan tiap pelanggan berjumlah 1  (menyimpang: 0)

## 3. FP-Growth (dibandingkan dengan Apriori buatan sendiri + hitung manual support/confidence/lift)

  Parameter: min support 2%, min confidence 60%
  [LOLOS] Loyalitas Rendah: 555 transaksi, aturan sistem 69 vs manual 69  (selisih maks support/confidence/lift 3.55e-15)
  [LOLOS] Loyalitas Tinggi: 1700 transaksi, aturan sistem 27 vs manual 27  (selisih maks support/confidence/lift 1.78e-15)

  Parameter: min support 2%, min confidence 40%
  [LOLOS] Loyalitas Rendah: 555 transaksi, aturan sistem 107 vs manual 107  (selisih maks support/confidence/lift 3.55e-15)
  [LOLOS] Loyalitas Tinggi: 1700 transaksi, aturan sistem 50 vs manual 50  (selisih maks support/confidence/lift 3.55e-15)

## Ringkasan
  Semua pemeriksaan LOLOS.
