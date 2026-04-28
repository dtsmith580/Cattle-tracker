
from django.contrib import admin
from cattle_tracker_app.models.breeding_models import BreedingHistory

@admin.register(BreedingHistory)
class BreedingHistoryAdmin(admin.ModelAdmin):
    list_display = ('cow', 'bull', 'breeding_date', 'pregnancy_confirmation_date', 'expected_calving_date', 'calving_outcome')
    search_fields = ('cow__ear_tag', 'bull__ear_tag')
    list_filter = ('calving_outcome', 'breeding_date')
    ordering = ('-breeding_date',)
