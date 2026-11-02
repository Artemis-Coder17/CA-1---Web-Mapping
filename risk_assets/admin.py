from django.contrib.gis import admin
from .models import RiskAsset


@admin.register(RiskAsset)
class RiskAssetAdmin(admin.GeoModelAdmin):
    list_display = ["name", "asset_type", "county", "is_critical", "population_served"]
    list_filter = ["asset_type", "county", "is_critical"]
    search_fields = ["name", "county", "address"]
