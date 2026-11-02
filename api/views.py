from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from flood_zones.models import FloodZone, River
from risk_assets.models import RiskAsset
from .serializers import (
    FloodZoneSerializer,
    RiverSerializer,
    RiskAssetSerializer,
    RiskAssetWithDistanceSerializer,
)


class FloodZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FloodZone.objects.all()
    serializer_class = FloodZoneSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["risk_level", "county"]
    search_fields = ["name", "river_catchment", "county"]
    ordering_fields = ["name", "area_km2"]

    @action(detail=True, methods=["get"], url_path="assets-within")
    def assets_within(self, request, pk=None):
        """Spatial query 1 — Containment: return all risk assets inside this flood zone."""
        zone = self.get_object()
        assets = RiskAsset.objects.filter(location__within=zone.geometry)
        serializer = RiskAssetSerializer(assets, many=True)
        return Response({
            "zone": zone.name,
            "risk_level": zone.get_risk_level_display(),
            "asset_count": assets.count(),
            "assets": serializer.data,
        })

    @action(detail=True, methods=["get"], url_path="intersecting-rivers")
    def intersecting_rivers(self, request, pk=None):
        """Spatial query 2 — Intersection: return rivers that cross this flood zone."""
        zone = self.get_object()
        rivers = River.objects.filter(geometry__intersects=zone.geometry)
        serializer = RiverSerializer(rivers, many=True)
        return Response({
            "zone": zone.name,
            "river_count": rivers.count(),
            "rivers": serializer.data,
        })

    @action(detail=True, methods=["get"], url_path="buffer")
    def buffer_zone(self, request, pk=None):
        """Spatial query 3 — Buffer: return assets within a danger radius of this flood zone.
        Optional query param: radius_km (default 1km).
        """
        zone = self.get_object()
        try:
            radius_km = float(request.query_params.get("radius_km", 1.0))
        except ValueError:
            return Response({"error": "radius_km must be a number."}, status=status.HTTP_400_BAD_REQUEST)

        assets = RiskAsset.objects.filter(
            location__distance_lte=(zone.geometry, D(km=radius_km))
        ).annotate(distance=Distance("location", zone.geometry))

        serializer = RiskAssetWithDistanceSerializer(assets, many=True)
        return Response({
            "zone": zone.name,
            "radius_km": radius_km,
            "asset_count": assets.count(),
            "assets": serializer.data,
        })


class RiverViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = River.objects.all()
    serializer_class = RiverSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["county"]
    search_fields = ["name", "county"]


class RiskAssetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiskAsset.objects.all()
    serializer_class = RiskAssetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["asset_type", "county", "is_critical"]
    search_fields = ["name", "county", "address"]
    ordering_fields = ["name", "population_served"]

    @action(detail=False, methods=["get"], url_path="nearest")
    def nearest(self, request):
        """Spatial query 4 — Proximity: return nearest assets to a given lat/lng point.
        Required params: lat, lng
        Optional: limit (default 10)
        """
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response(
                {"error": "lat and lng query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10

        point = Point(lng, lat, srid=4326)
        assets = (
            RiskAsset.objects.annotate(distance=Distance("location", point))
            .order_by("distance")[:limit]
        )
        serializer = RiskAssetWithDistanceSerializer(assets, many=True)
        return Response({
            "reference_point": {"lat": lat, "lng": lng},
            "limit": limit,
            "assets": serializer.data,
        })
