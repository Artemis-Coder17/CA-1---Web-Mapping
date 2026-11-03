from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance, MakeValid
from django.contrib.gis.measure import D
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter

from flood_zones.models import FloodZone, River
from risk_assets.models import RiskAsset
from .serializers import (
    FloodZoneSerializer,
    RiverSerializer,
    RiskAssetSerializer,
    RiskAssetWithDistanceSerializer,
)


# ModelViewSet covers all CRUD routes — the router handles URL generation
class FloodZoneViewSet(viewsets.ModelViewSet):
    """Flood zone polygons from OPW PFRA data. Supports filtering by risk_level and county."""
    queryset = FloodZone.objects.all()
    serializer_class = FloodZoneSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["risk_level", "county"]
    search_fields = ["name", "river_catchment", "county"]
    ordering_fields = ["name", "area_km2"]

    # Spatial Query 1 — which critical assets are inside this flood zone?
    @extend_schema(responses=RiskAssetSerializer, description="ST_Within — returns all risk assets contained inside this flood zone.")
    @action(detail=True, methods=["get"], url_path="assets-within")
    def assets_within(self, request, pk=None):
        zone = self.get_object()
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Had to use raw SQL with ST_MakeValid — the OPW data has invalid geometries
                # (self-intersections) that cause a PostGIS TopologyException with the ORM __within
                cursor.execute(
                    """
                    SELECT a.id FROM risk_assets_riskasset a
                    JOIN flood_zones_floodzone z ON z.id = %s
                    WHERE ST_Within(a.location, ST_MakeValid(z.geometry))
                    """,
                    [zone.pk],
                )
                asset_ids = [row[0] for row in cursor.fetchall()]
            assets = RiskAsset.objects.filter(id__in=asset_ids)
            serializer = RiskAssetSerializer(assets, many=True)
            return Response({
                "zone": zone.name,
                "risk_level": zone.get_risk_level_display(),
                "asset_count": len(asset_ids),
                "assets": serializer.data,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Spatial Query 2 — which rivers pass through this flood zone?
    @extend_schema(responses=RiverSerializer, description="ST_Intersects — returns rivers whose geometry crosses this flood zone.")
    @action(detail=True, methods=["get"], url_path="intersecting-rivers")
    def intersecting_rivers(self, request, pk=None):
        zone = self.get_object()
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Same ST_MakeValid fix needed here — same invalid geometry issue
                cursor.execute(
                    """
                    SELECT r.id FROM flood_zones_river r
                    JOIN flood_zones_floodzone z ON z.id = %s
                    WHERE ST_Intersects(r.geometry, ST_MakeValid(z.geometry))
                    """,
                    [zone.pk],
                )
                river_ids = [row[0] for row in cursor.fetchall()]
            rivers = River.objects.filter(id__in=river_ids)
            serializer = RiverSerializer(rivers, many=True)
            return Response({
                "zone": zone.name,
                "river_count": len(river_ids),
                "rivers": serializer.data,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Spatial Query 3 — assets within X km of the zone boundary
    @extend_schema(
        parameters=[OpenApiParameter("radius_km", float, description="Search radius in kilometres (default 2.0)")],
        responses=RiskAssetWithDistanceSerializer,
        description="distance_lte — returns assets within radius_km of this zone. Includes calculated distance_km per asset."
    )
    @action(detail=True, methods=["get"], url_path="buffer")
    def buffer_zone(self, request, pk=None):
        zone = self.get_object()
        try:
            radius_km = float(request.query_params.get("radius_km", 2.0))
        except ValueError:
            return Response({"error": "radius_km must be a number."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            valid_geom = zone.geometry.make_valid()
            # distance_lte with D(km=) stays in WGS84 and uses the GiST index — fast
            # tried ::geography cast in raw SQL first but it was taking 57 seconds
            assets = RiskAsset.objects.filter(
                location__distance_lte=(valid_geom, D(km=radius_km))
            ).annotate(distance=Distance("location", valid_geom))
            serializer = RiskAssetWithDistanceSerializer(assets, many=True)
            return Response({
                "zone": zone.name,
                "radius_km": radius_km,
                "asset_count": assets.count(),
                "assets": serializer.data,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RiverViewSet(viewsets.ModelViewSet):
    """River line geometries. Used in intersection queries with flood zones."""
    queryset = River.objects.all()
    serializer_class = RiverSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["county"]
    search_fields = ["name", "county"]


class RiskAssetViewSet(viewsets.ModelViewSet):
    """Critical infrastructure — hospitals, fire stations, Garda stations."""
    queryset = RiskAsset.objects.all()
    serializer_class = RiskAssetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["asset_type", "county", "is_critical"]
    search_fields = ["name", "county", "address"]
    ordering_fields = ["name", "population_served"]

    # Spatial Query 4 — click anywhere on the map, get the closest assets to that point
    # detail=False because this query isn't tied to a specific asset record
    @extend_schema(
        parameters=[
            OpenApiParameter("lat", float, description="Latitude of the search point", required=True),
            OpenApiParameter("lng", float, description="Longitude of the search point", required=True),
            OpenApiParameter("limit", int, description="Number of results to return (default 10)"),
        ],
        responses=RiskAssetWithDistanceSerializer,
        description="Distance annotation — returns the nearest assets to a given lat/lng point, ordered by distance."
    )
    @action(detail=False, methods=["get"], url_path="nearest")
    def nearest(self, request):
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

        # PostGIS Point takes (lng, lat) — longitude is x-axis, latitude is y-axis
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
