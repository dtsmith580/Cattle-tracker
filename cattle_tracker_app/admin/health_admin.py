# cattle_tracker_app/admin.py  (append to your existing admin setup)
from django.contrib import admin
from cattle_tracker_app.models import HealthRecord, VaccinationRecord, CastrationRecord  # ✅ correct

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'cattle', 'event_type', 'title', 'performed_by', 'cost', 'next_due')
    list_filter  = ('event_type', 'date', 'next_due')
    search_fields = ('cattle__ear_tag', 'title', 'description', 'performed_by__username')
    autocomplete_fields = ('cattle', 'performed_by')
    date_hierarchy = 'date'
    ordering = ('-date', '-id')

@admin.register(VaccinationRecord)
class VaccinationRecordAdmin(admin.ModelAdmin):
    list_display = ('health_record', 'vaccine_name', 'dose', 'administration_method', 'batch_number', 'withdrawal_date')
    search_fields = ('vaccine_name', 'batch_number', 'health_record__cattle__ear_tag')

@admin.register(CastrationRecord)
class CastrationRecordAdmin(admin.ModelAdmin):
    list_display = ('health_record', 'method', 'age_days')
    list_filter  = ('method',)
    search_fields = ('health_record__cattle__ear_tag',)
