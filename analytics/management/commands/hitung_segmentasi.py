from django.core.management.base import BaseCommand

from analytics.models import Cluster, ClusterMembership
from analytics.services.fcm import jalankan_segmentasi


class Command(BaseCommand):
    help = "Jalankan Fuzzy C-Means k=2..5, pilih k terbaik (Silhouette), beri label loyalitas"

    def handle(self, *args, **opts):
        h = jalankan_segmentasi()
        for c in h["silhouette"]:
            self.stdout.write(f"k={c}: silhouette={h['silhouette'][c]:.4f} (iterasi {h['iterasi'][c]})")
        self.stdout.write(f"k optimal = {h['k_optimal']}")
        for cl in Cluster.objects.order_by("cluster_number"):
            anggota = ClusterMembership.objects.filter(cluster=cl).select_related("customer")
            tegas = sum(
                1 for m in anggota
                if m.membership_degree == max(
                    x.membership_degree for x in ClusterMembership.objects.filter(customer=m.customer))
            )
            self.stdout.write(
                f"Klaster {cl.cluster_number} | {cl.loyalty_label} | skor={cl.loyalty_score:.4f} | "
                f"anggota (keanggotaan tertinggi)={tegas} | pusat(R,F,M)="
                + ", ".join(f"{v:.4f}" for v in cl.centroid))