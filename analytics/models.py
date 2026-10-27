import uuid

from django.db import models

from catalog.models import Customer


class RfmValue(models.Model):
    """Tabel 3.13 — nilai RFM, status keaktifan, dan profil pelanggan."""

    ACTIVITY_CHOICES = [
        ("Aktif", "Aktif"),
        ("Kurang Aktif", "Kurang Aktif"),
        ("Tidak Aktif", "Tidak Aktif"),
    ]

    rfm_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="rfm_value"
    )
    recency = models.IntegerField()
    frequency = models.IntegerField()
    monetary = models.FloatField()
    recency_norm = models.FloatField()
    frequency_norm = models.FloatField()
    monetary_norm = models.FloatField()
    composite_score = models.FloatField()
    activity_status = models.CharField(max_length=15, choices=ACTIVITY_CHOICES)
    first_purchase_date = models.DateField()
    last_purchase_date = models.DateField()
    tenure_days = models.IntegerField()
    avg_invoice_value = models.FloatField()
    product_variety = models.IntegerField()
    favorite_product = models.CharField(max_length=255, null=True, blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RFM {self.customer_id}"


class Cluster(models.Model):
    """Tabel 3.14 — hasil klasterisasi Fuzzy C-Means + label loyalitas."""

    cluster_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster_number = models.IntegerField()
    total_clusters = models.IntegerField()
    centroid = models.JSONField()
    loyalty_score = models.FloatField()
    loyalty_label = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Klaster {self.cluster_number} ({self.loyalty_label})"


class ClusterMembership(models.Model):
    """Tabel 3.15 — derajat keanggotaan fuzzy pelanggan ke SEMUA klaster."""

    membership_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="memberships"
    )
    cluster = models.ForeignKey(
        Cluster, on_delete=models.CASCADE, related_name="memberships"
    )
    membership_degree = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "cluster"], name="unique_customer_cluster"
            )
        ]

    def __str__(self):
        return f"{self.customer_id} -> {self.cluster} ({self.membership_degree:.4f})"


class AssociationRule(models.Model):
    """Tabel 3.16 — aturan asosiasi FP-Growth per klaster, beserta parameter
    dan periode analisis yang dipakai saat aturan dibentuk."""

    rule_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster = models.ForeignKey(
        Cluster, on_delete=models.CASCADE, related_name="association_rules"
    )
    antecedent = models.TextField()
    consequent = models.TextField()
    support = models.FloatField()
    confidence = models.FloatField()
    lift_ratio = models.FloatField()
    min_support = models.FloatField()
    min_confidence = models.FloatField()
    period_type = models.CharField(max_length=20)
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.antecedent} -> {self.consequent}"


class CrmScenario(models.Model):
    """Tabel 3.17 — basis pengetahuan skenario CRM (5 baris, di-seed)."""

    scenario_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loyalty_label = models.CharField(max_length=30, unique=True)
    strategy_name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.loyalty_label


class Recommendation(models.Model):
    """Tabel 3.18 — rekomendasi CRM final, tiga narasi self-explainable terpisah."""

    recommendation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster = models.ForeignKey(
        Cluster, on_delete=models.CASCADE, related_name="recommendations"
    )
    scenario = models.ForeignKey(
        CrmScenario, on_delete=models.PROTECT, related_name="recommendations"
    )
    characteristics_text = models.TextField()
    strategy_text = models.TextField()
    reason_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rekomendasi klaster {self.cluster_id}"