import json
from django.core.management.base import BaseCommand
from shapely.geometry import shape
from cattle_tracker_app.models.pasture_models import Pasture, Paddock

class Command(BaseCommand):
    help = 'Backfills acres based on geometry for pastures and paddocks.'

    def handle(self, *args, **options):
        self.stdout.write("🔁 Backfilling paddock acres...")
        for paddock in Paddock.objects.all():
            if paddock.geometry:
                try:
                    geo = json.loads(paddock.geometry) if isinstance(paddock.geometry, str) else paddock.geometry
                    geom = shape(geo)
                    paddock.acres = round(geom.area * 0.000247105, 2)
                    paddock.save()
                    self.stdout.write(f"✅ {paddock.name}: {paddock.acres} acres")
                except Exception as e:
                    self.stderr.write(f"❌ Error with paddock {paddock.name}: {e}")

        self.stdout.write("🔁 Backfilling pasture acres...")
        for pasture in Pasture.objects.all():
            if pasture.geometry:
                try:
                    geo = json.loads(pasture.geometry) if isinstance(pasture.geometry, str) else pasture.geometry
                    geom = shape(geo)
                    pasture.acres = round(geom.area * 0.000247105, 2)
                    pasture.save()
                    self.stdout.write(f"✅ {pasture.name}: {pasture.acres} acres")
                except Exception as e:
                    self.stderr.write(f"❌ Error with pasture {pasture.name}: {e}")
