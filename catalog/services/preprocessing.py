import re

import pandas as pd

# Kolom yang wajib ada di Sheet1 uploaded file 
KOLOM_WAJIB = [
    "No Faktur", "Tanggal Faktur", "No Pelanggan", "Nama Pelanggan",
    "Nama Barang", "Qty", "Satuan", "Harga", "Dpp",
]

BULAN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "agu": 8, "sep": 9, "okt": 10, "nop": 11, "des": 12,
}

# Penggabungan nama barang manual (kalau ada varian yang tidak tertangkap aturan otomatis).
# Isi: {"NAMA VARIAN": "NAMA BAKU"}
ALIAS_BARANG = {}

# Penggabungan nama pelanggan manual (varian ejaan yang tidak tertangkap aturan otomatis).
# Isi: {"NAMA VARIAN (huruf besar)": "NAMA BAKU (huruf besar)"}
ALIAS_PELANGGAN = {}


class PreprocessingError(Exception):
    pass


# ---------- tanggal ----------
def parse_tanggal(nilai):
    if isinstance(nilai, str):
        bagian = nilai.strip().split()
        try:
            return pd.Timestamp(int(bagian[2]), BULAN[bagian[1][:3].lower()], int(bagian[0]))
        except (IndexError, KeyError, ValueError):
            return pd.NaT
    return pd.to_datetime(nilai, errors="coerce")


# ---------- nama barang ----------
def rapikan_nama_barang(teks):
    s = str(teks).strip().upper()
    s = re.sub(r"^PENJ\s+", "", s) #buang awalan PENJ
    s = re.sub(r"\s+[\d.,]+\*[\d.,]+.*$", "", s) #buang bagian belakang "120*247747,75 NAMA PELANGGAN"
    s = s.replace('"', " ").replace(":", " ").replace("'", " ") #mengganti tanda kutip dan titik dua dengan spasi
    s = re.sub(r"\bFXLEXIBLE\b|\bFLEKSIBLE\b", "FLEXIBLE", s) #typo
    s = re.sub(r"\s*/\s*", " / ", s) #menyeragamkan spasi di sekitar /
    s = re.sub( #"@2000 PCS" / "@ 2.000 PCS" -> "@2.000 PCS"
        r"@\s*([\d.]+)\s*PCS",
        lambda m: "@" + f"{int(m.group(1).replace('.', '')):,}".replace(",", ".") + " PCS",
        s,
    )
    s = re.sub(r"\b(\d+)\s*ML\b", r"\1 ML", s) #220ML -> 220 ML
    s = re.sub(r"\bS-MART\b", "SMART", s)
    s = re.sub(r"\b([WSTB])\s*\.\s*", r"\1 ", s) #"W.250" -> "W 250"
    s = re.sub(r"\bTM\s*([WSTB])\b", r"TM \1", s) #"TMW" -> "TM W"
    s = re.sub(r"\bSTRAW FLEXIBLE TM\b", "FLEXIBLE TM", s)
    s = re.sub(r"\bSAKA FLEXIBLE BUNGKUS KERTAS\b", "SAKA BUNGKUS KERTAS", s)

    # ukuran "A X B": angka terkecil dulu supaya "250 X 40" = "40 X 250"
    def urut_ukuran(m):
        a, b = int(m.group(1)), int(m.group(2))
        return f"{min(a, b)} X {max(a, b)}"
    s = re.sub(r"\b(\d+)\s*[Xx]\s*(\d+)\b", urut_ukuran, s)
    s = re.sub(r"\s+", " ", s).strip(" /-")
    return ALIAS_BARANG.get(s, s)


# ---------- pelanggan ----------
def kunci_nama(nama):
    # huruf besar, buang semua selain huruf/angka: "TOKO SAMA - SAMA" = "TOKO SAMA-SAMA"
    nama = str(nama).upper().strip()
    nama = ALIAS_PELANGGAN.get(nama, nama)
    return re.sub(r"[^A-Z0-9]", "", nama)


def kode_lama(kode):
    # format manual sebelum Accurate: "01.6400.XXX"
    return bool(re.fullmatch(r"\d\d\.\d{4}\.\d{3}", str(kode)))


def gabungkan_pelanggan(df):
    # Dua kode pelanggan digabung kalau namanya (setelah dirapikan) sama
    induk = {k: k for k in df["No Pelanggan"].unique()}

    def cari(x):
        while induk[x] != x:
            induk[x] = induk[induk[x]]
            x = induk[x]
        return x

    pemilik_nama = {}
    for kode, nama in zip(df["No Pelanggan"], df["Nama Pelanggan"]):
        kunci = kunci_nama(nama)
        if kunci in pemilik_nama:
            induk[cari(kode)] = cari(pemilik_nama[kunci])
        else:
            pemilik_nama[kunci] = kode

    kelompok = {}
    for kode in induk:
        kelompok.setdefault(cari(kode), []).append(kode)

    jumlah_baris = df["No Pelanggan"].value_counts()
    peta = {}
    for anggota in kelompok.values():
        # prioritas kode Accurate; kalau ada beberapa, yang barisnya paling banyak
        kandidat = [k for k in anggota if not kode_lama(k)] or anggota
        utama = max(kandidat, key=lambda k: jumlah_baris[k])
        for k in anggota:
            peta[k] = utama
    return peta

def praproses(df_mentah):
    laporan = {"baris_mentah": len(df_mentah)}

    kurang = [k for k in KOLOM_WAJIB if k not in df_mentah.columns]
    if kurang:
        raise PreprocessingError(f"Kolom wajib tidak ditemukan: {kurang}")

    # 1. seleksi atribut
    df = df_mentah[KOLOM_WAJIB].copy()
    for kolom in ["No Faktur", "No Pelanggan", "Nama Pelanggan", "Nama Barang"]:
        df[kolom] = df[kolom].astype(str).str.strip()
    df["Satuan"] = df["Satuan"].astype(str).str.strip().str.upper().replace({"NAN": None, "": None})

    # 2. data kosong pada atribut kunci
    kunci = ["No Faktur", "Tanggal Faktur", "No Pelanggan", "Nama Barang", "Dpp"]
    sebelum = len(df)
    df = df.dropna(subset=kunci)
    laporan["baris_kosong_dibuang"] = sebelum - len(df)

    # 3. duplikat persis
    sebelum = len(df)
    df = df.drop_duplicates()
    laporan["duplikat_persis_dibuang"] = sebelum - len(df)

    # 4. tanggal
    df["tanggal"] = df["Tanggal Faktur"].map(parse_tanggal)
    if df["tanggal"].isna().any():
        raise PreprocessingError("Ada tanggal faktur yang tidak bisa dibaca.")

    # 5. nama barang
    df["produk"] = df["Nama Barang"].map(rapikan_nama_barang)

    # 6. pelanggan ganda
    peta = gabungkan_pelanggan(df)
    laporan["pelanggan_sebelum_gabung"] = df["No Pelanggan"].nunique()
    df["kode_pelanggan"] = df["No Pelanggan"].map(peta)
    nama_utama = (
        df.groupby("kode_pelanggan")["Nama Pelanggan"]
        .agg(lambda s: s.value_counts().index[0])
    )
    df["nama_pelanggan"] = df["kode_pelanggan"].map(nama_utama)

    # 7. angka
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce")
    df["Dpp"] = pd.to_numeric(df["Dpp"], errors="coerce")
    df = df.dropna(subset=["Qty", "Harga", "Dpp"])

    hasil = df.rename(columns={
        "No Faktur": "no_faktur", "Qty": "qty", "Satuan": "satuan",
        "Harga": "harga", "Dpp": "subtotal",
    })[["no_faktur", "tanggal", "kode_pelanggan", "nama_pelanggan",
        "produk", "qty", "satuan", "harga", "subtotal"]].reset_index(drop=True)

    # 8. duplikat setelah nama barang dirapikan
    sebelum = len(hasil)
    hasil = hasil.drop_duplicates().reset_index(drop=True)
    laporan["duplikat_setelah_standarisasi"] = sebelum - len(hasil)

    hasil["id_transaksi"] = hasil["no_faktur"]

    laporan.update({
        "transaksi": hasil["id_transaksi"].nunique(),
        "baris": len(hasil),
        "faktur": hasil["no_faktur"].nunique(),
        "pelanggan": hasil["kode_pelanggan"].nunique(),
        "produk": hasil["produk"].nunique(),
    })
    return hasil, laporan