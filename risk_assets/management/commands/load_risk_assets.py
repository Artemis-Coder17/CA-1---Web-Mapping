"""
Management command to load Irish risk asset data.
Follows the load_cities pattern: --clear flag, update_or_create, GeoJSON import.
Data sources:
  - Wicklow Fire Stations: Wicklow County Council via ArcGIS Open Data
  - Dublin Fire Stations: Dublin Fire Brigade (real GeoJSON)
  - Dublin Garda Stations: An Garda Síochána (real GeoJSON)
  - Hospitals: real HSE facility coordinates
"""

import json
import os
import urllib.request

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from risk_assets.models import RiskAsset

WICKLOW_FIRE_URL = (
    "https://opendata.arcgis.com/datasets/2648559d3ba049ce88099f16180e395f_0.geojson"
)

def _data(filename):
    return os.path.join(settings.BASE_DIR, "data", filename)

DUBLIN_FIRE_PATH  = _data("dublin_fire_stations.geojson")
DUBLIN_GARDA_PATH = _data("dublin_garda_stations.geojson")


class Command(BaseCommand):
    help = "Load Irish risk assets (fire stations, Garda stations, hospitals)"

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

        self._load_wicklow_fire_stations()
        self._load_dublin_fire_stations()
        self._load_dublin_garda_stations()
        self._load_wicklow_garda_stations()
        self._load_hospitals()
        self.stdout.write(self.style.SUCCESS("Risk asset load complete."))

    def _load_wicklow_fire_stations(self):
        self.stdout.write("  Fetching Wicklow fire stations …")
        try:
            with urllib.request.urlopen(WICKLOW_FIRE_URL, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            self.stderr.write(f"  Could not fetch Wicklow fire stations: {e}")
            return

        loaded = 0
        for feat in data["features"]:
            p = feat["properties"]
            coords = feat["geometry"]["coordinates"]
            name = p.get("BUILDING_N", "Unknown").title()
            addr_parts = [p.get(f"ADDR_{i}", "") for i in range(1, 5)]
            address = ", ".join(a for a in addr_parts if a)
            RiskAsset.objects.update_or_create(
                name=name,
                defaults={
                    "asset_type": "fire_station", "county": "Wicklow",
                    "address": address[:255], "population_served": 5000,
                    "is_critical": True,
                    "location": Point(coords[0], coords[1], srid=4326),
                },
            )
            loaded += 1
        self.stdout.write(f"  Wicklow fire stations: {loaded}")

    def _load_dublin_fire_stations(self):
        self.stdout.write("  Loading Dublin fire stations …")
        try:
            with open(DUBLIN_FIRE_PATH, encoding="latin-1") as f:
                data = json.load(f)
        except Exception as e:
            self.stderr.write(f"  Could not read Dublin fire stations: {e}")
            return

        loaded = 0
        for feat in data["features"]:
            p = feat["properties"]
            coords = feat["geometry"]["coordinates"]
            name = f"{p.get('StationName', 'Unknown')} Fire Station"
            RiskAsset.objects.update_or_create(
                name=name,
                defaults={
                    "asset_type": "fire_station", "county": "Dublin",
                    "address": p.get("Address", "")[:255],
                    "population_served": 8000, "is_critical": True,
                    "location": Point(coords[0], coords[1], srid=4326),
                },
            )
            loaded += 1
        self.stdout.write(f"  Dublin fire stations: {loaded}")

    def _load_dublin_garda_stations(self):
        self.stdout.write("  Loading Dublin Garda stations …")
        try:
            with open(DUBLIN_GARDA_PATH, encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except Exception as e:
            self.stderr.write(f"  Could not read Dublin Garda stations: {e}")
            return

        loaded = 0
        for feat in data["features"]:
            p = feat["properties"]
            coords = feat["geometry"]["coordinates"]
            name = f"{p.get('Station', 'Unknown').strip()} Garda Station"
            addr = ", ".join(
                filter(None, [p.get("Address1", ""), p.get("Address2", ""), p.get("Address3", "")])
            )
            RiskAsset.objects.update_or_create(
                name=name,
                defaults={
                    "asset_type": "garda", "county": "Dublin",
                    "address": addr[:255],
                    "population_served": 12000, "is_critical": True,
                    "location": Point(coords[0], coords[1], srid=4326),
                },
            )
            loaded += 1
        self.stdout.write(f"  Dublin Garda stations: {loaded}")

    def _load_wicklow_garda_stations(self):
        stations = [
            {"name": "Wicklow Garda Station",    "address": "Market Square, Wicklow Town",        "lon": -6.0419, "lat": 52.9800},
            {"name": "Bray Garda Station",        "address": "Eglinton Road, Bray",                "lon": -6.0985, "lat": 53.2024},
            {"name": "Arklow Garda Station",      "address": "Ferrybank, Arklow",                  "lon": -6.1480, "lat": 52.7982},
            {"name": "Greystones Garda Station",  "address": "Trafalgar Road, Greystones",         "lon": -6.0625, "lat": 53.1426},
            {"name": "Baltinglass Garda Station", "address": "Mill Street, Baltinglass",           "lon": -6.7063, "lat": 52.9412},
            {"name": "Rathdrum Garda Station",    "address": "Main Street, Rathdrum",              "lon": -6.2250, "lat": 52.9283},
        ]
        loaded = 0
        for s in stations:
            RiskAsset.objects.update_or_create(
                name=s["name"],
                defaults={
                    "asset_type": "garda", "county": "Wicklow",
                    "address": s["address"], "population_served": 10000,
                    "is_critical": True,
                    "location": Point(s["lon"], s["lat"], srid=4326),
                },
            )
            loaded += 1
        self.stdout.write(f"  Wicklow Garda stations: {loaded}")

    def _load_hospitals(self):
        hospitals = [
            {"name": "Wicklow General Hospital",      "county": "Wicklow", "address": "Knockrobin, Wicklow Town",           "lon": -6.0390, "lat": 52.9756, "pop": 80000},
            {"name": "Arklow Community Hospital",     "county": "Wicklow", "address": "Arklow, Co. Wicklow",                "lon": -6.1540, "lat": 52.7980, "pop": 25000},
            {"name": "St. Vincent's University Hospital", "county": "Dublin", "address": "Elm Park, Dublin 4",             "lon": -6.2180, "lat": 53.3070, "pop": 200000},
            {"name": "St. James's Hospital",          "county": "Dublin", "address": "James's Street, Dublin 8",           "lon": -6.2960, "lat": 53.3380, "pop": 180000},
            {"name": "Mater Misericordiae University Hospital", "county": "Dublin", "address": "Eccles Street, Dublin 7",  "lon": -6.2720, "lat": 53.3590, "pop": 160000},
            {"name": "Tallaght University Hospital",  "county": "Dublin", "address": "Tallaght, Dublin 24",                "lon": -6.3720, "lat": 53.2870, "pop": 150000},
        ]
        loaded = 0
        for h in hospitals:
            RiskAsset.objects.update_or_create(
                name=h["name"],
                defaults={
                    "asset_type": "hospital", "county": h["county"],
                    "address": h["address"], "population_served": h["pop"],
                    "is_critical": True,
                    "location": Point(h["lon"], h["lat"], srid=4326),
                },
            )
            loaded += 1
        self.stdout.write(f"  Hospitals: {loaded}")
