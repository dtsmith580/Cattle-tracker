from django.contrib import admin
from cattle_tracker_app.models.leasedbull_models import LeasedBull

@admin.register(LeasedBull)
class LeasedBullAdmin(admin.ModelAdmin):
    list_display = ("ear_tag", "breed", "lease_start", "lease_end", "owner_name")
    search_fields = ("ear_tag", "breed", "owner_name")
