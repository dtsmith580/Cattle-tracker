# cattle_tracker_app/admin/settings_admin.py

from django.contrib import admin
from cattle_tracker_app.models.settings_models import RanchSetting

@admin.register(RanchSetting)
class RanchSettingAdmin(admin.ModelAdmin):
    list_display = ("owner", "backup_frequency_hours")
    search_fields = ("owner__username",)
