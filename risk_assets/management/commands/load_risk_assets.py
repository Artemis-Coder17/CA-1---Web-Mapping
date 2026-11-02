"""
Management command to load real Irish risk asset data.
Pattern follows Lab 3/4 load_cities approach: --clear flag, update_or_create.
Data sources:
  - Wicklow Fire Stations: Wicklow County Council via ArcGIS Open Data
  - Wicklow Hospitals: real facility coordinates from HSE/OSM data
  - Wicklow Garda Stations: real OPW/Garda locations
"""

import urllib.request
import json

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from risk_assets.models import RiskAsset


FIRE_STATIONS_URL = (
    "https://opendata.arcgis.com/datasets/2648559d3ba049ce88099f16180e395f_0.geojson"
)


class Command(BaseCommand):
    help = "Load Wicklow risk assets (fire stations, hospitals, Garda stations) from real open data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing risk assets before loading",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count = RiskAsset.objects.count()
            RiskAsset.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count} risk assets"))

        self._load_fire_stations()
        self._load_hospitals()
        self._load_garda_stations()
        self.stdout.write(self.style.SUCCESS("Risk asset load complete."))

    # ------------------------------------------------------------------
    # Fire stations — Wicklow County Council ArcGIS Open Data
    # ------------------------------------------------------------------

    def _load_fire_stations(self):
        self.stdout.write("  Fetching Wicklow fire stations …")
        try:
            with urllib.request.urlopen(FIRE_STATIONS_URL, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            self.stderr.write(f"  Could not fetch fire stations: {e}")
            return

        loaded = 0
        for feat in data["features"]:
            p = feat["properties"]
            coords = feat["geometry"]["coordinates"]  # [lon, lat]

            name = p.get("BUILDING_N", "Unknown Fire Station").title()
            addr_parts = [p.get(f"ADDR_{i}", "") for i in range(1, 5)]
            address = ", ".join(a for a in addr_parts if a)

            point = Point(coords[0], coords[1], srid=4326)

            RiskAsset.objects.update_or_create(
                name=name,
                defaults={
                    "asset_type": "fire_station",
                    "county": "Wicklow",
                    "address": address[:255],
                    "population_served": 5000,
                    "is_critical": True,
                    "location": point,
                },
            )
            loaded += 1

        self.stdout.write(f"  Fire stations loaded: {loaded}")

    # ------------------------------------------------------------------
    # Hospitals — HSE / OSM verified Wicklow county coordinates
    # ------------------------------------------------------------------

    def _load_hospitals(self):
        hospitals = [
            {
                "name": "Wicklow General Hospital",
                "address": "Knockrobin, Wicklow Town, Co. Wicklow",
                "lon": -6.0390,
                "lat": 52.9756,
                "population_served": 80000,
                "is_critical": True,
            },
            {
                "name": "St. Columcille's Hospital",
                "address": "Loughlinstown, Co. Dublin (serving S. Wicklow)",
                "lon": -6.1780,
                "lat": 53.2390,
                "population_served": 50000,
                "is_critical": True,
            },
            {
                "name": "Arklow Community Hospital",
                "address": "Arklow, Co. Wicklow",
                "lon": -6.1540,
                "lat": 52.7980,
                "population_served": 25000,
                "is_critical": True,
            },
        ]

        loaded = 0
        for h in hospitals:
            RiskAsset.objects.update_or_create(
                name=h["name"],
                defaults={
                    "asset_type": "hospital",
                    "county": "Wicklow",
                    "address": h["address"],
                    "population_served": h["population_served"],
                    "is_critical": h["is_critical"],
                    "location": Point(h["lon"], h["lat"], srid=4326),
                },
            )
            loaded += 1

        self.stdout.write(f"  Hospitals loaded: {loaded}")

    # ------------------------------------------------------------------
    # Garda stations — real Wicklow Garda locations
    # ------------------------------------------------------------------

    def _load_garda_stations(self):
        stations = [
            {"name": "Wicklow Garda Station", "address": "Market Square, Wicklow Town", "lon": -6.0419, "lat": 52.9800},
            {"name": "Bray Garda Station", "address": "Eglinton Road, Bray, Co. Wicklow", "lon": -6.0985, "lat": 53.2024},
            {"name": "Arklow Garda Station", "address": "Ferrybank, Arklow, Co. Wicklow", "lon": -6.1480, "lat": 52.7982},
            {"name": "Greystones Garda Station", "address": "Trafalgar Road, Greystones, Co. Wicklow", "lon": -6.0625, "lat": 53.1426},
            {"name": "Baltinglass Garda Station", "address": "Mill Street, Baltinglass, Co. Wicklow", "lon": -6.7063, "lat": 52.9412},
            {"name": "Rathdrum Garda Station", "address": "Main Street, Rathdrum, Co. Wicklow", "lon": -6.2250, "lat": 52.9283},
        ]

        loaded = 0
        for s in stations:
            RiskAsset.objects.update_or_create(
                name=s["name"],
                defaults={
                    "asset_type": "garda",
                    "county": "Wicklow",
                    "address": s["address"],
                    "population_served": 10000,
                    "is_critical": True,
                    "location": Point(s["lon"], s["lat"], srid=4326),
                },
            )
            loaded += 1

        self.stdout.write(f"  Garda stations loaded: {loaded}")
