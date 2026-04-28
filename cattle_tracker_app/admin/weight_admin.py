
from django.contrib import admin
from cattle_tracker_app.models.weight_models import WeightLog

@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ('cattle', 'date', 'weight', 'notes')
    list_filter = ('date', 'cattle')
    search_fields = ('cattle__ear_tag',)
