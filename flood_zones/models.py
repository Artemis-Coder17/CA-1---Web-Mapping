from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class FloodZone(models.Model):
    # Flood risk zone polygons based on OPW Ireland PFRA data
    # Risk levels: A = high risk, B = moderate, AO = overtopping

    RISK_LEVELS = [
        ("A", "Zone A - High Risk"),
        ("B", "Zone B - Moderate Risk"),
        ("AO", "Zone AO - High Risk with Overtopping"),
    ]

    name = models.CharField(max_length=255)
    risk_level = models.CharField(max_length=2, choices=RISK_LEVELS)
    river_catchment = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    area_km2 = models.FloatField()
    description = models.TextField(blank=True)
    # MultiPolygon used as some zones have non-contiguous areas
    geometry = models.MultiPolygonField(srid=4326)

    class Meta:
        indexes = [
            models.Index(fields=["risk_level", "county"]),
            # GiST index for fast spatial queries on zone geometry
            GistIndex(fields=["geometry"], name="floodzone_geometry_gist_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_risk_level_display()})"


class River(models.Model):
    # River line geometries used in intersection queries with flood zones

    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    length_km = models.FloatField()
    # MultiLineString handles rivers with tributaries or split reaches
    geometry = models.MultiLineStringField(srid=4326)

    class Meta:
        indexes = [
            models.Index(fields=["county"]),
            # GiST index for fast intersection queries
            GistIndex(fields=["geometry"], name="river_geometry_gist_idx"),
        ]

    def __str__(self):
        return self.name
