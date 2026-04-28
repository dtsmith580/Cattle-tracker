
from django.contrib import admin
from django.utils import timezone
from django.db.models import Q
from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.ownership_models import Owner

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from cattle_tracker_app.models.turnout_models import TurnoutGroup
from cattle_tracker_app.forms.turnout_forms import TurnoutGroupForm

@admin.register(TurnoutGroup)
class TurnoutGroupAdmin(admin.ModelAdmin):
    # ... your other admin options

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        #"""
        #In ADMIN we do NOT restrict by owner. Only basic eligibility:
        ### age >= 16 months for bulls; cows/heifers >= 13 months (optional)
        #"""
        today = timezone.now().date()

        alive_like = Q(status__in=['alive']) | Q(status__isnull=True)
        not_removed = ~Q(status__in=['deceased', 'sold'])

        if db_field.name == 'bulls':
            cutoff = today - relativedelta(months=15)

            type_is_bull = Q(animal_type='bull') | Q(animal_type__isnull=True, sex__in=['M', 'male', 'bull'])
            kwargs['queryset'] = (
                Cattle.objects
                .filter(type_is_bull, dob__lte=cutoff)
                .filter(alive_like)
                .filter(not_removed)
                .order_by('ear_tag')
            )

        elif db_field.name == 'cows':
            cutoff = today - relativedelta(months=13)

            type_is_cow = (
                Q(animal_type__in=['cow', 'heifer']) |
                Q(animal_type__isnull=True, sex__in=['F', 'female', 'cow', 'heifer'])
            )
            kwargs['queryset'] = (
                Cattle.objects
                .filter(type_is_cow, dob__lte=cutoff)
                .filter(alive_like)
                .filter(not_removed)
                .order_by('ear_tag')
            )

        return super().formfield_for_manytomany(db_field, request, **kwargs)