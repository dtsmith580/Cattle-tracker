# cattle_tracker_app/admin/herd_bull_admin.py
from django.contrib import admin
from cattle_tracker_app.models.herd_bull_models import HerdBull

@admin.register(HerdBull)
class HerdBullAdmin(admin.ModelAdmin):
    list_display = ("__str__", "fertility_status", "fertility_test_date", "semen_collected", "semen_straws_on_hand")
    search_fields = ("cattle__ear_tag", "cattle__registration_number")
    autocomplete_fields = ("cattle",)
    list_filter = ("semen_collected", "fertility_status")
