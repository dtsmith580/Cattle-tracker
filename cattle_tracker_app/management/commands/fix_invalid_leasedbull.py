from django.core.management.base import BaseCommand
from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.leasedbull_models import LeasedBull

class Command(BaseCommand):
    help = "Fixes invalid leased_bull references in the Cattle table"

    def handle(self, *args, **kwargs):
        invalid_refs = []
        fixed = 0

        for cow in Cattle.objects.exclude(leased_bull=None):
            try:
                if not isinstance(cow.leased_bull, LeasedBull):
                    self.stdout.write(f"❌ Invalid Leased Bull on Cattle ID {cow.id}: leased_bull_id={cow.leased_bull_id}")
                    cow.leased_bull = None
                    cow.save()
                    fixed += 1
            except Exception as e:
                self.stdout.write(f"⚠️ Error on Cattle ID {cow.id}: {e}")
                cow.leased_bull = None
                cow.save()
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Cleanup complete. Fixed {fixed} invalid leased_bull references."))
