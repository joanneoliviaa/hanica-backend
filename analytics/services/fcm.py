import numpy as np
from django.db import transaction as db_transaction

from analytics.models import Cluster, ClusterMembership, RfmValue

M = 2.0 #eksponen pembobot
EPSILON = 0.001 #ambang konvergensi fungsi objektif
MAX_ITER = 100
SEED = 42

LABEL_PER_K = {
    2: ["Rendah", "Tinggi"],
    3: ["Rendah", "Sedang", "Tinggi"],
    4: ["Sangat Rendah", "Rendah", "Tinggi", "Sangat Tinggi"],
    5: ["Sangat Rendah", "Rendah", "Sedang", "Tinggi", "Sangat Tinggi"],
}


def jarak(X, V):
    # matriks jarak Euclidean (n x c)
    return np.sqrt(((X[:, None, :] - V[None, :, :]) ** 2).sum(axis=2))


def fcm(X, c, m=M, eps=EPSILON, max_iter=MAX_ITER, seed=SEED):
    n = len(X)
    rng = np.random.default_rng(seed)
    U = rng.dirichlet(np.ones(c), size=n) #U0 acak, tiap baris berjumlah 1
    P_lama = 0.0
    for t in range(1, max_iter + 1):
        Um = U ** m
        V = (Um.T @ X) / Um.sum(axis=0)[:, None] #rumus 2.9
        D = np.fmax(jarak(X, V), 1e-12)
        P = float((Um * D ** 2).sum()) #fungsi objektif
        U = 1.0 / ((D[:, :, None] / D[:, None, :]) ** (2 / (m - 1))).sum(axis=2) #rumus 2.12
        if t > 1 and abs(P - P_lama) < eps:
            break
        P_lama = P
    Um = U ** m
    V = (Um.T @ X) / Um.sum(axis=0)[:, None]
    return U, V, t


def silhouette(X, label):
    n = len(X)
    D = jarak(X, X)
    s = np.zeros(n)
    for i in range(n):
        sama = (label == label[i])
        if sama.sum() <= 1:
            continue      
        a = D[i, sama].sum() / (sama.sum() - 1)
        b = min(D[i, label == k].mean() for k in set(label) if k != label[i])
        s[i] = (b - a) / max(a, b)
    return float(s.mean())


def evaluasi_k(X, daftar_k=(2, 3, 4, 5)):
    hasil = {}
    for c in daftar_k:
        U, V, iterasi = fcm(X, c)
        hasil[c] = {"U": U, "V": V, "iterasi": iterasi,
                    "silhouette": silhouette(X, U.argmax(axis=1))}
    return hasil


def beri_label(V):
    skor = ((1 - V[:, 0]) + V[:, 1] + V[:, 2]) / 3
    urutan = np.argsort(skor) #dari terendah ke tertinggi
    label = {int(k): LABEL_PER_K[len(V)][r] for r, k in enumerate(urutan)}
    return skor, urutan, label


def jalankan_segmentasi(k_dipilih=None):
    rfm = list(RfmValue.objects.select_related("customer").order_by("customer_id"))
    X = np.array([[r.recency_norm, r.frequency_norm, r.monetary_norm] for r in rfm])
    hasil = evaluasi_k(X)
    k_opt = k_dipilih or max(hasil, key=lambda c: hasil[c]["silhouette"])
    U, V = hasil[k_opt]["U"], hasil[k_opt]["V"]
    skor, urutan, label = beri_label(V)

    with db_transaction.atomic():
        Cluster.objects.all().delete()
        klaster = {}
        for nomor, k in enumerate(urutan, start=1): 
            klaster[int(k)] = Cluster.objects.create(
                cluster_number=nomor, total_clusters=k_opt,
                centroid=[float(v) for v in V[k]],
                loyalty_score=float(skor[k]), loyalty_label="Loyalitas " + label[int(k)],
            )
        ClusterMembership.objects.bulk_create([
            ClusterMembership(customer=r.customer, cluster=klaster[k], membership_degree=float(U[i, k]))
            for i, r in enumerate(rfm) for k in range(k_opt)
        ])
    return {"silhouette": {c: h["silhouette"] for c, h in hasil.items()},
            "iterasi": {c: h["iterasi"] for c, h in hasil.items()},
            "k_optimal": k_opt}