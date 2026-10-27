from django.contrib import admin

from .models import (
    RfmValue,
    Cluster,
    ClusterMembership,
    AssociationRule,
    CrmScenario,
    Recommendation,
)

admin.site.register(RfmValue)
admin.site.register(Cluster)
admin.site.register(ClusterMembership)
admin.site.register(AssociationRule)
admin.site.register(CrmScenario)
admin.site.register(Recommendation)