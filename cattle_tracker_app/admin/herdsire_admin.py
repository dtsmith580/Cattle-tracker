
from django.contrib import admin
from cattle_tracker_app.models.herd_sire_models import HerdSire

@admin.register(HerdSire)
class HerdSireAdmin(admin.ModelAdmin):
    list_display = ('name', 'semen_type', 'cleanup_method','profile_link' )
    search_fields = ('name',)
    list_filter = ('semen_type', 'cleanup_method')
