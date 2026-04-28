# cattle_tracker_app/admin/cattle_admin.py
# Re-wired admin with:
#  - Date Added column (created_at/date_added fallback)
#  - Owner-scoped paddock choices
#  - Safe imports (no circulars)
#  - Clean list display & filters

from django.contrib import admin
from django.utils.html import format_html
from django.apps import apps

from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.forms import CattleAdminForm

# Access helper (robust fallback if utils.access is absent)
try:
    from cattle_tracker_app.utils.access import get_user_allowed_owners  # type: ignore
except Exception:  # pragma: no cover
    def get_user_allowed_owners(user):
        from cattle_tracker_app.models.ownership_models import OwnerUserAccess
        return list(OwnerUserAccess.objects.filter(user=user).values_list('owner_id', flat=True))


@admin.register(Cattle)
class CattleAdmin(admin.ModelAdmin):
    form = CattleAdminForm

    class Media:
        css = {'all': ('css/admin.css',)}
        js = ('js/cattle_admin_form.js', 'js/cattle_form.js',)

    # Cleaned, non-duplicated list_display
    list_display = (
        'ear_tag', 'owner', 'registration_number', 'breed', 'animal_type',
        'photo_preview', 'dob', 'get_age', 'sex', 'sire', 'sire_type', 'status',
        'purchase_price', 'sale_price', 'sale_date', 'pregnancy_status',
        'pasture_column', 'paddock', 'date_added', 'date_removed',
    )

    search_fields = (
        'ear_tag', 'registration_number', 'breed', 'owner__name',
    )

    # Dynamic date filters so we don't crash if created_at is missing
    def get_list_filter(self, request):
        base = list(super().get_list_filter(request))
        field_names = {f.name for f in self.model._meta.get_fields()}
        if 'created_at' in field_names:
            base.append(('created_at', admin.DateFieldListFilter))
        base.extend(['status', 'animal_type'])
        return tuple(base)

    def get_date_hierarchy(self, request):
        field_names = {f.name for f in self.model._meta.get_fields()}
        return 'created_at' if 'created_at' in field_names else None

    ordering = ('-id',)  # override if you prefer '-created_at'

    readonly_fields = ('get_age',)

    fieldsets = (
        ('Identification', {
            'fields': (
                'ear_tag', 'owner', 'registration_number', 'breed', 'animal_type',
                'sex', 'dob', 'get_age', 'pregnancy_status', 'status'
            )
        }),
        ('Lineage', {
            'fields': ('breeding_method', 'sire', 'sire_type', 'herd_sire', 'dam')
        }),
        ('Location', {
            'fields': ('pasture','paddock',)
        }),
        ('Transaction Info', {
            'fields': ('purchased_from', 'purchase_price', 'sold_to', 'sale_date', 'sale_price', 'date_added', 'date_removed')
        }),
    )

    actions = ['mark_as_steer', 'mark_as_cow', 'mark_as_bull', 'mark_as_heifer']

    # Photo preview
    @admin.display(description="Photo")
    def photo_preview(self, obj):
        img = getattr(obj, 'image', None)
        if img and getattr(img, 'url', None):
            return format_html('<img src="{}" style="height:50px; width:auto; border-radius:6px;" />', img.url)
        return '—'

    # Age (read-only)
    def get_age(self, obj):
        return getattr(obj, 'age', '—')
    get_age.short_description = 'Age'

    # Pasture column (resilient whether or not Cattle has a .pasture property)
    @admin.display(description='Pasture')
    def pasture_column(self, obj):
        try:
            p = getattr(obj, 'pasture', None)
            if p:
                return getattr(p, 'name', '—')
            pad = getattr(obj, 'paddock', None)
            if pad and getattr(pad, 'pasture', None):
                return pad.pasture.name
        except Exception:
            pass
        return '—'

    # Date added column that prefers created_at, then date_added, else '—'
    @admin.display(ordering='created_at', description='Date added')
    def date_added(self, obj):
        dt = getattr(obj, 'created_at', None) or getattr(obj, 'date_added', None)
        try:
            return dt.date() if hasattr(dt, 'date') else dt or '—'
        except Exception:
            return '—'

    # Scope paddock choices by allowed owners + active flags
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'paddock':
            Paddock = apps.get_model('cattle_tracker_app', 'Paddock')
            qs = Paddock.objects.filter(is_active=True, pasture__is_active=True)
            owner_ids = get_user_allowed_owners(request.user)
            if owner_ids:
                qs = qs.filter(pasture__owner_id__in=owner_ids)
            kwargs['queryset'] = qs.select_related('pasture', 'pasture__land_property') \
                                 .order_by('pasture__land_property__name', 'pasture__name', 'name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Optionally auto select_related to speed list view
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'paddock', 'paddock__pasture', 'paddock__pasture__land_property')
