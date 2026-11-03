"""
Management command to load Irish flood zone and river data.
Follows the load_cities pattern: --clear flag, update_or_create, GeoJSON import.
Data sources:
  - Wicklow Zone A/B: OPW SFRA 2021 via data.gov.ie (WGS84)
  - Wicklow/Dublin Zone AO + Dublin Zone A/B: generated river-corridor polygons
  - Rivers: Wicklow and Dublin waterways (WGS84 centrelines)
"""

import json
import os

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, MultiLineString, LineString
from django.core.management.base import BaseCommand

from flood_zones.models import FloodZone, River

# (filename, risk_level, county, catchment_label)
ZONE_FILES = [
    ("flood_zone_a.geojson",      "A",  "Wicklow", "Wicklow Coastal / Avoca"),
    ("flood_zone_b.geojson",      "B",  "Wicklow", "Wicklow Coastal / Avoca"),
    ("flood_zone_ao.geojson",     "AO", "Wicklow", "Wicklow Coastal / Avoca"),
    ("dublin_zone_a.geojson",     "A",  "Dublin",  "Liffey / Dodder / Tolka"),
    ("dublin_zone_b.geojson",     "B",  "Dublin",  "Liffey / Dodder / Tolka"),
    ("dublin_zone_ao.geojson",    "AO", "Dublin",  "Liffey / Dodder / Tolka"),
]

RIVERS = [
    # Wicklow
    {"name": "River Avoca",               "county": "Wicklow", "length_km": 20.0,
     "coords": [(-6.3545,52.8635),(-6.3102,52.8820),(-6.2670,52.9010),(-6.2238,52.9280),
                (-6.1965,52.9490),(-6.1719,52.9670),(-6.1543,52.9840),(-6.1504,52.9972)]},
    {"name": "River Vartry",              "county": "Wicklow", "length_km": 34.0,
     "coords": [(-6.3892,53.0650),(-6.3544,53.0502),(-6.3098,53.0340),(-6.2688,53.0180),
                (-6.2238,53.0080),(-6.1720,52.9990),(-6.1295,53.0005),(-6.0879,53.0105),(-6.0627,53.0340)]},
    {"name": "River Slaney (Upper Wicklow)", "county": "Wicklow", "length_km": 30.0,
     "coords": [(-6.6540,53.0120),(-6.6210,52.9840),(-6.5880,52.9560),(-6.5522,52.9280),
                (-6.5160,52.9010),(-6.4788,52.8740),(-6.4401,52.8480),(-6.4010,52.8220)]},
    {"name": "Potters River",             "county": "Wicklow", "length_km": 8.0,
     "coords": [(-6.2500,52.8700),(-6.2320,52.8820),(-6.2142,52.8960),(-6.1960,52.9090)]},
    # Dublin
    {"name": "River Liffey (Dublin)",     "county": "Dublin",  "length_km": 18.0,
     "coords": [(-6.390,53.349),(-6.355,53.349),(-6.320,53.346),(-6.290,53.344),
                (-6.260,53.343),(-6.240,53.342),(-6.220,53.341),(-6.200,53.340)]},
    {"name": "River Dodder",              "county": "Dublin",  "length_km": 16.0,
     "coords": [(-6.305,53.287),(-6.285,53.295),(-6.265,53.307),(-6.250,53.314),
                (-6.242,53.322),(-6.237,53.331),(-6.232,53.339)]},
    {"name": "River Tolka",               "county": "Dublin",  "length_km": 14.0,
     "coords": [(-6.380,53.400),(-6.340,53.390),(-6.310,53.382),(-6.285,53.375),
                (-6.260,53.368),(-6.240,53.360),(-6.220,53.354)]},
]


class Command(BaseCommand):
    help = "Load Irish flood zone polygons and river lines (Wicklow + Dublin)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing flood zones and rivers before loading",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count_z = FloodZone.objects.count()
            count_r = River.objects.count()
            FloodZone.objects.all().delete()
            River.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count_z} flood zones and {count_r} rivers"))

        self._load_flood_zones()
        self._load_rivers()
        self.stdout.write(self.style.SUCCESS("Flood data load complete."))

    def _load_flood_zones(self):
        base = os.path.join(settings.BASE_DIR, "data")
        loaded = 0

        for filename, risk_level, county, catchment in ZONE_FILES:
            filepath = os.path.join(base, filename)
            if not os.path.exists(filepath):
                self.stdout.write(self.style.ERROR(f"File not found: {filename}"))
                continue

            with open(filepath) as f:
                data = json.load(f)

            for i, feature in enumerate(data["features"]):
                geom_raw = json.dumps(feature["geometry"])
                try:
                    geom = GEOSGeometry(geom_raw, srid=4326)
                except Exception as e:
                    self.stderr.write(f"Skipping {filename} feature {i}: {e}")
                    continue

                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom)

                props = feature["properties"]
                area_m2 = props.get("SHAPE__Area") or props.get("SUM_SUM_AR") or 0
                area_km2 = round(float(area_m2) / 1_000_000, 4) if area_m2 else 0.0
                name = f"{county} Zone {risk_level} — Feature {i + 1}"
                layer = props.get("layer", "")
                description = f"OPW SFRA 2021. Layer: {layer}. AEP: {props.get('AEP', 'N/A')}"

                FloodZone.objects.update_or_create(
                    name=name,
                    defaults={
                        "risk_level": risk_level,
                        "river_catchment": catchment,
                        "county": county,
                        "area_km2": area_km2,
                        "description": description,
                        "geometry": geom,
                    },
                )
                loaded += 1

        self.stdout.write(f"  Flood zones loaded: {loaded}")

    def _load_rivers(self):
        loaded = 0
        for r in RIVERS:
            line = LineString(r["coords"], srid=4326)
            geom = MultiLineString(line, srid=4326)
            River.objects.update_or_create(
                name=r["name"],
                defaults={"county": r["county"], "length_km": r["length_km"], "geometry": geom},
            )
            loaded += 1
        self.stdout.write(f"  Rivers loaded: {loaded}")
