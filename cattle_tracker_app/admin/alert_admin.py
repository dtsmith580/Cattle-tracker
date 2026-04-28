from django.contrib import admin

from cattle_tracker_app.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("cattle", "alert_type", "alert_date", "resolved")
    list_filter = ("alert_type", "resolved")
    search_fields = ("cattle__ear_tag", "message")
    ordering = ("-alert_date",)
    autocomplete_fields = ("cattle",)