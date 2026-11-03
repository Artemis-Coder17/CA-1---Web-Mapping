from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class RiskAsset(models.Model):
    # Critical infrastructure points used in containment and proximity queries
    # Covers fire stations, hospitals, and Garda stations across flood risk counties

    ASSET_TYPES = [
        ("fire_station", "Fire Station"),
        ("hospital", "Hospital"),
        ("garda", "Garda Station"),
    ]

    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    county = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    population_served = models.IntegerField(default=0)
    is_critical = models.BooleanField(default=False)
    # Point location used for proximity and buffer spatial queries
    location = models.PointField(srid=4326)

    class Meta:
        indexes = [
            models.Index(fields=["asset_type", "county"]),
            # GiST index for fast distance and containment queries
            GistIndex(fields=["location"], name="riskasset_location_gist_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"
