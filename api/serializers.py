from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from flood_zones.models import FloodZone, River
from risk_assets.models import RiskAsset


class FloodZoneSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = FloodZone
        geo_field = "geometry"
        fields = ["id", "name", "risk_level", "river_catchment", "county", "area_km2", "description"]


class RiverSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = River
        geo_field = "geometry"
        fields = ["id", "name", "county", "length_km"]


class RiskAssetSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = RiskAsset
        geo_field = "location"
        fields = ["id", "name", "asset_type", "county", "address", "population_served", "is_critical"]


class RiskAssetWithDistanceSerializer(GeoFeatureModelSerializer):
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = RiskAsset
        geo_field = "location"
        fields = ["id", "name", "asset_type", "county", "address", "is_critical", "distance_km"]

    def get_distance_km(self, obj):
        if hasattr(obj, "distance"):
            return round(obj.distance.km, 3)
        return None
