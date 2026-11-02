from django.contrib.gis import admin
from .models import FloodZone, River


@admin.register(FloodZone)
class FloodZoneAdmin(admin.GeoModelAdmin):
    list_display = ["name", "risk_level", "county", "river_catchment", "area_km2"]
    list_filter = ["risk_level", "county"]
    search_fields = ["name", "county", "river_catchment"]


@admin.register(River)
class RiverAdmin(admin.GeoModelAdmin):
    list_display = ["name", "county", "length_km"]
    list_filter = ["county"]
    search_fields = ["name", "county"]
