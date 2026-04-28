# cattle_tracker_app/management/commands/list_calf_mothers.py
from django.core.management.base import BaseCommand
from django.db.models import Count
from cattle_tracker_app.models import Cattle

class Command(BaseCommand):
    help = "List calf → mother pairings and count calves per dam"

    def handle(self, *args, **options):
        self.stdout.write("\n=== Calf → Mother Pairings ===")
        # Use the 'dam' field and reverse relation 'dam_of' to find all calves with a linked mother
        pairs = Cattle.objects.filter(dam__isnull=False).select_related('dam')
        if not pairs:
            self.stdout.write("No calves linked to a dam found.")
        for calf in pairs:
            self.stdout.write(f"Calf {calf.ear_tag} → Mother {calf.dam.ear_tag}")

        self.stdout.write("\n=== Dam → Number of Calves ===")
        # Annotate each cow (dam) with the number of related calves via the 'dam_of' reverse name
        dams = Cattle.objects.annotate(num_calves=Count('dam_of')).filter(num_calves__gt=0)
        if not dams:
            self.stdout.write("No dams with calves found.")
        for dam in dams:
            self.stdout.write(f"Dam {dam.ear_tag} has {dam.num_calves} calves")
