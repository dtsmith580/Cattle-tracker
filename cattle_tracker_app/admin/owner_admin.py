
from django.contrib import admin
from cattle_tracker_app.models.ownership_models import Owner, OwnerUserAccess

class OwnerUserAccessInline(admin.TabularInline):
    model = OwnerUserAccess
    extra = 1
    autocomplete_fields = ['user']

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    inlines = [OwnerUserAccessInline]
