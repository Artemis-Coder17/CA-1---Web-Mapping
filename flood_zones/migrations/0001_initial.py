from django.db import migrations
import django.contrib.gis.db.models.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FloodZone",
            fields=[
                ("id", django.db.models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", django.db.models.CharField(max_length=255)),
                ("risk_level", django.db.models.CharField(choices=[("A", "Zone A - High Risk"), ("B", "Zone B - Moderate Risk"), ("AO", "Zone AO - High Risk with Overtopping")], max_length=2)),
                ("river_catchment", django.db.models.CharField(max_length=255)),
                ("county", django.db.models.CharField(max_length=100)),
                ("area_km2", django.db.models.FloatField()),
                ("description", django.db.models.TextField(blank=True)),
                ("geometry", django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name="River",
            fields=[
                ("id", django.db.models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", django.db.models.CharField(max_length=255)),
                ("county", django.db.models.CharField(max_length=100)),
                ("length_km", django.db.models.FloatField()),
                ("geometry", django.contrib.gis.db.models.fields.MultiLineStringField(srid=4326)),
            ],
        ),
        migrations.AddIndex(
            model_name="floodzone",
            index=django.db.models.Index(fields=["risk_level", "county"], name="flood_zones_risk_le_idx"),
        ),
        migrations.AddIndex(
            model_name="river",
            index=django.db.models.Index(fields=["county"], name="flood_zones_river_county_idx"),
        ),
    ]
