from __future__ import annotations

from datetime import date, timedelta
import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Sum, Value, DecimalField, Q, Prefetch
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

# --- App models ---
from cattle_tracker_app.models.weight_models import WeightLog
from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.breeding_models import BreedingHistory
from cattle_tracker_app.models.health_models import HealthRecord
from cattle_tracker_app.models.alert_models import Alert
from cattle_tracker_app.models.pasture_models import Pasture

# RanchSetting (singular) for manual map center (lat/lng) — adjust path if needed
try:
    from cattle_tracker_app.models import RanchSetting
    HAS_SETTING = True
except Exception:
    HAS_SETTING = False
    RanchSetting = None

# --- Access / roles ---
from cattle_tracker_app.utils.access import get_user_allowed_owners
from cattle_tracker_app.utils.roles import is_admin, is_manager, is_vet

# -------------------- Role helpers --------------------

def has_dashboard_access(user):
    return is_admin(user) or is_manager(user) or is_vet(user)


def access_denied_view(request):
    allowed_owners = get_user_allowed_owners(request.user)
    return render(request, "access_denied.html", {"allowed_owners": allowed_owners})


def is_dashboard_user(user):
    from cattle_tracker_app.utils.roles import has_role
    return user.is_superuser or any([
        has_role(user, r) for r in ["Managers", "Veterinarians", "Admin", "Dev"]
    ])

# -------------------- Map helpers (no geocoding) --------------------

def _get_primary_owner_for_user(user):
    """Return one Owner the user can access (or None)."""
    qs = get_user_allowed_owners(user)
    return qs.first() if qs is not None else None


def _setting_for_owner(owner):
    """Fetch RanchSetting (singular) for the given owner, if available."""
    if not owner or not HAS_SETTING:
        return None
    try:
        return RanchSetting.objects.filter(owner=owner).first()
    except Exception:
        return None


def _setting_to_center(setting) -> Optional[dict]:
    """Convert RanchSetting.map_lat/map_lng into {'lat','lng','zoom'} if present."""
    if not setting:
        return None
    lat = getattr(setting, "map_lat", None)
    lng = getattr(setting, "map_lng", None)
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return {"lat": float(lat), "lng": float(lng), "zoom": 12}
    return None


def _pasture_centroid_for_user(user) -> Optional[dict]:
    """
    Compute centroid for all allowed Pasture geometries (no geocoder).
    Returns {'lat','lng','zoom'} or None.
    """
    try:
        owners_qs = get_user_allowed_owners(user)
        qs = Pasture.objects.filter(owner__in=owners_qs).exclude(geometry__isnull=True)
        # Prefer GIS centroid of the collection
        try:
            from django.contrib.gis.db.models.aggregates import Collect
            from django.contrib.gis.db.models.functions import Centroid
            agg = qs.aggregate(c=Centroid(Collect("geometry")))
            c = agg.get("c")
            if c:
                return {"lat": float(c.y), "lng": float(c.x), "zoom": 12}
        except Exception:
            # Fallback: centroid of first pasture geometry
            p = qs.first()
            if p and getattr(p, "geometry", None):
                try:
                    cent = p.geometry.centroid
                    return {"lat": float(cent.y), "lng": float(cent.x), "zoom": 12}
                except Exception:
                    pass
    except Exception:
        pass
    return None

# -------------------- Snapshot helpers --------------------

def month_ends(now_dt: datetime.datetime | None = None) -> tuple[datetime.datetime, datetime.date]:
    """Return (previous_month_end_as_datetime, today_date)."""
    now_dt = now_dt or timezone.now()
    start_this_month = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = start_this_month - timedelta(seconds=1)
    return prev_month_end, now_dt.date()


def herd_size_as_of(as_of_date: date, owner_ids: list[int] | tuple[int, ...]) -> int:
    """Snapshot herd size as of a given date."""
    qs = Cattle.objects.all()
    if owner_ids:
        qs = qs.filter(owner__id__in=owner_ids)

    today = timezone.localdate()
    if as_of_date == today:
        qs = qs.filter(date_removed__isnull=True, status__iexact='alive')
        return qs.count()

    qs = qs.filter(date_added__lte=as_of_date)
    qs = qs.filter(Q(date_removed__isnull=True) | Q(date_removed__gt=as_of_date))
    try:
        qs = qs.exclude(status__regex=r'(?i)^(sold|dead)')
    except Exception:
        qs = qs.exclude(status__in=["sold","Sold","SOLD","dead","Dead","DEAD"])
    return qs.count()


def percent_change(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0

# -------------------- Dashboard --------------------

@login_required
@user_passes_test(has_dashboard_access, login_url='/access-denied/')
def dashboard_view(request):
    # ---------- Access scope ----------
    owner_access_qs = get_user_allowed_owners(request.user)
    model_name = getattr(owner_access_qs.model._meta, 'model_name', None)
    if model_name == 'owneruseraccess':
        owner_ids = list(owner_access_qs.values_list('owner_id', flat=True))
    else:
        owner_ids = list(owner_access_qs.values_list('pk', flat=True))
    if not owner_ids:
        owner_ids = [-1]  # force empty result sets where appropriate

    # ---------- Pasture metrics ----------
    total_pasture_acres = Pasture.objects.filter(owner__id__in=owner_ids).aggregate(
        total_acres=Coalesce(Sum('size_acres'), Value(0), output_field=DecimalField())
    )['total_acres'] or 0

    # ---------- Time boundaries ----------
    prev_month_end_dt, today_date = month_ends()

    # Previous month pasture acres if timestamped
    pasture_fields = [f.name for f in Pasture._meta.get_fields()]
    if 'created_at' in pasture_fields:
        prev_month_pasture_acres = Pasture.objects.filter(
            owner__id__in=owner_ids,
            created_at__lte=prev_month_end_dt
        ).aggregate(
            total_acres=Coalesce(Sum('size_acres'), Value(0), output_field=DecimalField())
        )['total_acres'] or 0
        pasture_delta = total_pasture_acres - prev_month_pasture_acres
        pasture_percent = (pasture_delta / prev_month_pasture_acres * 100) if prev_month_pasture_acres else 0
    else:
        prev_month_pasture_acres = None
        pasture_delta = 0
        pasture_percent = 0

    # ---------- Herd MoM (snapshot-based) ----------
    previous_count = herd_size_as_of(prev_month_end_dt.date(), owner_ids)
    current_count = herd_size_as_of(today_date, owner_ids)
    delta = current_count - previous_count
    mom_pct = percent_change(current_count, previous_count)

    # ---------- Other metrics ----------
    breeding_count = BreedingHistory.objects.filter(
        cow__owner__id__in=owner_ids,
        pregnancy_confirmation_date__isnull=False
    ).count()

    health_alerts_count = HealthRecord.objects.filter(
        cattle__owner__id__in=owner_ids,
        event_type='alert'
    ).count()

    unresolved_alerts_count = Alert.objects.filter(
        cattle__owner__id__in=owner_ids,
        resolved=False
    ).count()

    # ---------- Recent cattle preview ----------
    hr_fields = {f.name for f in HealthRecord._meta.get_fields()}
    if 'date' in hr_fields:
        order_field = '-date'
    elif 'created_at' in hr_fields:
        order_field = '-created_at'
    else:
        order_field = '-id'

    health_qs = HealthRecord.objects.all().order_by(order_field)

    cattle_list = (
        Cattle.objects.select_related('paddock')
        .prefetch_related(Prefetch('health_records', queryset=health_qs))
        .only('ear_tag', 'dob', 'owner', 'paddock', 'date_removed', 'status')
        .filter(owner__id__in=owner_ids)
        .order_by('-dob')[:6]
    )

    for cow in cattle_list:
        hrs = list(cow.health_records.all())
        latest_hr = hrs[0] if hrs else None

        if latest_hr:
            label = None
            for candidate in ('event_type', 'type', 'status', 'outcome', 'category', 'label'):
                if candidate in hr_fields:
                    val = getattr(latest_hr, candidate, None)
                    if val:
                        label = val
                        break
            if not label:
                for textish in ('diagnosis', 'description', 'notes', 'treatment'):
                    if textish in hr_fields:
                        txt = getattr(latest_hr, textish, '') or ''
                        txt = txt.strip()
                        if txt:
                            label = (txt[:40] + ('…' if len(txt) > 40 else ''))
                            break
            cow.health_status = label or 'Recorded'
        else:
            cow.health_status = 'None'

        lw = getattr(cow, 'latest_weight', None)
        cow.weight = lw() if callable(lw) else (lw if lw is not None else '—')
        cow.location = getattr(cow.paddock, 'name', '—')

    # ---------- Weight history / percent change ----------
    today = today_date
    start_30 = today - timedelta(days=30)
    last_period_start = start_30 - timedelta(days=30)
    last_period_end = start_30 - timedelta(days=1)

    weights_current = WeightLog.objects.filter(
        cattle__owner__id__in=owner_ids,
        date__gte=start_30
    )
    avg_current = weights_current.aggregate(
        avg=Coalesce(Avg('weight'), Value(0), output_field=DecimalField())
    )['avg'] or 0

    weights_prev = WeightLog.objects.filter(
        cattle__owner__id__in=owner_ids,
        date__gte=last_period_start,
        date__lte=last_period_end
    )
    avg_prev = weights_prev.aggregate(
        avg=Coalesce(Avg('weight'), Value(0), output_field=DecimalField())
    )['avg'] or 0

    weight_delta = (avg_current - avg_prev)
    weight_percent = (weight_delta / avg_prev * 100) if avg_prev else 0

    # ---------- Three most recent logs (with percent change) ----------
    recent_logs_qs = (
        WeightLog.objects.filter(cattle__owner__id__in=owner_ids)
        .select_related('cattle')
        .order_by('-date')[:3]
    )
    recent_weight_logs = []
    for log in recent_logs_qs:
        prev_log = (
            WeightLog.objects.filter(
                cattle=log.cattle,
                date__lt=log.date
            )
            .order_by('-date')
            .only('weight')
            .first()
        )
        pct_change = None
        if prev_log and prev_log.weight not in (None, 0):
            try:
                pct_change = 100 * (float(log.weight) - float(prev_log.weight)) / float(prev_log.weight)
            except (ZeroDivisionError, ValueError, TypeError):
                pct_change = None
        recent_weight_logs.append({'log': log, 'percent_change': pct_change})

    # ---------- Monthly sparkline (last 12 months) ----------
    one_year_ago = today - relativedelta(months=12)
    monthly_qs = (
        WeightLog.objects
        .filter(
            cattle__owner__id__in=owner_ids,
            date__gte=one_year_ago
        )
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(avg_weight=Avg('weight'))
        .order_by('month')
    )
    weight_daily = [
        {'date': item['month'].strftime('%b'), 'avg_weight': float(item['avg_weight'] or 0)}
        for item in monthly_qs
    ]

    # ---------- Build context ----------
    context = {
        # Total Cattle card (snapshot)
        'total_cattle': current_count,
        'delta': delta,
        'percent': mom_pct if mom_pct is not None else 0,
        'total_cattle_prev': previous_count,

        # KPIs
        'breeding_count': breeding_count,
        'health_alerts_count': health_alerts_count,
        'unresolved_alerts_count': unresolved_alerts_count,
        'total_pasture_acres': total_pasture_acres,
        'prev_month_pasture_acres': prev_month_pasture_acres,
        'pasture_delta': pasture_delta,
        'pasture_percent': pasture_percent,

        # Lists / charts
        'cattle_list': cattle_list,
        'avg_current_weight': avg_current,
        'avg_prev_weight': avg_prev,
        'weight_delta': weight_delta,
        'weight_percent': weight_percent,
        'recent_weight_logs': recent_weight_logs,
        'weight_daily': weight_daily,
    }

    # ---------- Map center selection (no geocoding required) ----------
    primary_owner = _get_primary_owner_for_user(request.user)
    setting = _setting_for_owner(primary_owner)
    ranch_center = _setting_to_center(setting)
    if not ranch_center:
        ranch_center = _pasture_centroid_for_user(request.user)
    if ranch_center:
        context["ranch_center"] = ranch_center
    # else: template will fall back to CONUS

    return render(request, 'dashboard.html', context)

# -------------------- Misc --------------------

@login_required
def root_redirect_view(request):
    return redirect('dashboard')


@login_required
def get_user_cattle(user):
    if user.is_superuser:
        return Cattle.objects.all()
    owners = get_user_allowed_owners(user)
    return Cattle.objects.filter(owner__in=owners)
