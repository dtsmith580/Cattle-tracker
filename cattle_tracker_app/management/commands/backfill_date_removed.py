# management/commands/backfill_date_removed.py
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from cattle_tracker_app.models.cattle_models import Cattle

class Command(BaseCommand):
    help = "Backfill date_removed where status is sold/dead but date_removed is null."

    def handle(self, *args, **opts):
        qs = Cattle.objects.filter(status__in=["sold","dead"], date_removed__isnull=True)
        updated = qs.update(date_removed=now().date())
        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} rows"))
