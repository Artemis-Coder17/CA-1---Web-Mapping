from django.contrib.gis.db import models


class FloodZone(models.Model):
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
    geometry = models.MultiPolygonField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["risk_level", "county"])]

    def __str__(self):
        return f"{self.name} ({self.get_risk_level_display()})"


class River(models.Model):
    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    length_km = models.FloatField()
    geometry = models.MultiLineStringField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["county"])]

    def __str__(self):
        return self.name
