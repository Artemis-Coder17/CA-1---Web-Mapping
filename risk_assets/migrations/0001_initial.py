from django.db import migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RiskAsset",
            fields=[
                ("id", django.db.models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", django.db.models.CharField(max_length=255)),
                ("asset_type", django.db.models.CharField(choices=[("hospital", "Hospital"), ("school", "School"), ("fire_station", "Fire Station"), ("garda", "Garda Station"), ("community", "Community Centre"), ("utility", "Utility Infrastructure")], max_length=20)),
                ("county", django.db.models.CharField(max_length=100)),
                ("address", django.db.models.CharField(blank=True, max_length=255)),
                ("population_served", django.db.models.IntegerField(default=0)),
                ("is_critical", django.db.models.BooleanField(default=False)),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
        migrations.AddIndex(
            model_name="riskasset",
            index=django.db.models.Index(fields=["asset_type", "county"], name="risk_assets_asset_ty_idx"),
        ),
    ]
