from django.contrib.gis.db import models


class RiskAsset(models.Model):
    ASSET_TYPES = [
        ("hospital", "Hospital"),
        ("school", "School"),
        ("fire_station", "Fire Station"),
        ("garda", "Garda Station"),
        ("community", "Community Centre"),
        ("utility", "Utility Infrastructure"),
    ]

    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    county = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    population_served = models.IntegerField(default=0)
    is_critical = models.BooleanField(default=False)
    location = models.PointField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["asset_type", "county"])]

    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"
