import numpy as np

from analytics.models import (
    AssociationRule, Cluster, CrmScenario, Recommendation, RfmValue,
)
from .fpgrowth import keanggotaan_tegas


def rupiah(x):
    return "Rp" + f"{round(x):,}".replace(",", ".")


def angka(x, desimal=1):
    return f"{x:.{desimal}f}".replace(".", ",")

def persen(x):
    """0,0287 -> '2,87%"""
    teks = f"{x * 100:.2f}".rstrip("0").rstrip(".")
    return teks.replace(".", ",")

def daftar_item(teks):
    """'A, B, C' -> 'A, B, dan C' ; 'A, B' -> 'A dan B'."""
    item = teks.split(", ")
    if len(item) <= 2:
        return " dan ".join(item)
    return ", ".join(item[:-1]) + ", dan " + item[-1]

def aturan_lift_tertinggi(cluster):
    return (AssociationRule.objects.filter(cluster=cluster)
            .order_by("-lift_ratio", "-support", "-confidence").first())

def bukti_aturan(cluster, maks=3):
    """Aturan dengan lift tertinggi, satu per kombinasi produk (A->B dan B->A dianggap sama)."""
    terpilih, terlihat = [], set()
    for r in AssociationRule.objects.filter(cluster=cluster).order_by("-lift_ratio", "-support"):
        kombinasi = frozenset(r.antecedent.split(", ") + r.consequent.split(", "))
        if kombinasi in terlihat:
            continue
        terlihat.add(kombinasi)
        terpilih.append(r)
        if len(terpilih) == maks:
            break
    return terpilih


def susun_rekomendasi():
    tegas = keanggotaan_tegas()
    rfm = {r.customer_id: r for r in RfmValue.objects.all()}
    hasil = []
    Recommendation.objects.all().delete()

    for cl in Cluster.objects.order_by("cluster_number"):
        anggota = [rfm[p] for p, k in tegas.items() if k == cl.cluster_id]
        n = len(anggota)
        rata = lambda attr: float(np.mean([getattr(a, attr) for a in anggota]))
        label = cl.loyalty_label.replace("Loyalitas ", "", 1)   

        # 1. karakteristik pelanggan
        characteristics = (
            f"Klaster {cl.cluster_number} beranggotakan {n} pelanggan dengan label loyalitas {label}. "
            f"Secara rata-rata, pelanggan pada segmen ini melakukan transaksi terakhir {round(rata('recency'))} hari "
            f"yang lalu, dengan frekuensi pembelian sebanyak {angka(rata('frequency'))} kali selama periode analisis "
            f"dan total nilai pembelian sekitar {rupiah(rata('monetary'))}."
        )

        # 2. strategi CRM
        skenario = CrmScenario.objects.get(loyalty_label=cl.loyalty_label)
        strategy = skenario.description

        # 3. alasan + bukti pola pembelian dengan lift tertinggi
        aturan = bukti_aturan(cl)
        alasan = (
            f"Rekomendasi strategi ini didasarkan pada skor loyalitas komposit klaster sebesar "
            f"{angka(cl.loyalty_score, 2)} (dari skala 0 hingga 1) yang menempatkan segmen ini pada label {label} "
            f"berdasarkan hasil pemeringkatan terhadap {cl.total_clusters} klaster yang terbentuk."
        )
        r = aturan_lift_tertinggi(cl)
        if r:
            alasan += (
                f" Selain itu, pola pembelian pada segmen ini menunjukkan bahwa pelanggan yang membeli "
                f"{daftar_item(r.antecedent)} memiliki kecenderungan juga membeli {daftar_item(r.consequent)}, "
                f"dengan nilai support sebesar {persen(r.support)}% dan nilai confidence sebesar {persen(r.confidence)}%. "
                f"Nilai lift ratio sebesar {angka(r.lift_ratio, 2)} "
            )
            if r.lift_ratio > 1:
                alasan += ("(lebih besar dari 1) menunjukkan hubungan tersebut bersifat positif dan dapat dijadikan "
                           "dasar strategi cross-selling atau bundling.")
            else:
                alasan += "(tidak lebih besar dari 1) menunjukkan hubungan tersebut belum bersifat positif."
        else:
            alasan += (" Belum ada aturan asosiasi yang tersimpan untuk segmen ini pada parameter analisis terakhir, "
                       "sehingga rekomendasi disusun berdasarkan skor loyalitas klaster.")

        Recommendation.objects.create(
            cluster=cl, scenario=skenario, characteristics_text=characteristics,
            strategy_text=strategy, reason_text=alasan)
        hasil.append((cl, characteristics, strategy, alasan))
    return hasil