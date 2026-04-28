from __future__ import annotations

from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from cattle_tracker_app.forms.alert_forms import AlertRuleForm


from cattle_tracker_app.models import Alert, AlertRule, UserAlertPreference
from cattle_tracker_app.utils.access import (
    get_user_allowed_owners,
    user_can_access_cattle,
    user_is_admin_like,
)


# ---------------------------------------------------------
# ALERT INBOX
# ---------------------------------------------------------

@login_required
def alerts_inbox_view(request):
    allowed_owners = get_user_allowed_owners(request.user)
    now = timezone.now()

    alerts = (
        Alert.objects
        .filter(
            cattle__owner__in=allowed_owners,
            resolved=False,
            dismissed=False,
        )
        .exclude(snoozed_until__gt=now)
        .select_related("cattle", "cattle__owner")
        .order_by("alert_date")
    )

    # Apply per-user mute
    prefs = UserAlertPreference.objects.filter(
        user=request.user,
        muted_until__gt=now
    )

    muted_pairs = {(p.owner_id, p.alert_type) for p in prefs if p.owner_id}
    muted_global = {p.alert_type for p in prefs if not p.owner_id}

    filtered_alerts = []
    for alert in alerts:
        if alert.alert_type in muted_global:
            continue
        if (alert.cattle.owner_id, alert.alert_type) in muted_pairs:
            continue
        filtered_alerts.append(alert)

    return render(request, "alerts/inbox.html", {
        "alerts": filtered_alerts
    })


# ---------------------------------------------------------
# ALERT ACTIONS
# ---------------------------------------------------------

@login_required
def alert_resolve_view(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()

    alert = get_object_or_404(Alert, pk=pk)

    if not user_can_access_cattle(request.user, alert.cattle):
        return HttpResponseForbidden()

    alert.resolved = True
    alert.save(update_fields=["resolved"])

    return redirect("alerts_inbox")


@login_required
def alert_dismiss_view(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()

    alert = get_object_or_404(Alert, pk=pk)

    if not user_can_access_cattle(request.user, alert.cattle):
        return HttpResponseForbidden()

    alert.dismissed = True
    alert.save(update_fields=["dismissed"])

    return redirect("alerts_inbox")


@login_required
def alert_snooze_view(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()

    alert = get_object_or_404(Alert, pk=pk)

    if not user_can_access_cattle(request.user, alert.cattle):
        return HttpResponseForbidden()

    days = int(request.POST.get("days", 7))
    alert.snoozed_until = timezone.now() + timedelta(days=days)
    alert.save(update_fields=["snoozed_until"])

    return redirect("alerts_inbox")


# ---------------------------------------------------------
# ALERT RULES (Managers/Admin Only)
# ---------------------------------------------------------

@login_required
def alert_rules_list_view(request):
    if not user_is_admin_like(request.user):
        return HttpResponseForbidden()

    allowed_owners = get_user_allowed_owners(request.user)

    rules = (
        AlertRule.objects
        .filter(owner__in=allowed_owners)
        .select_related("owner")
        .order_by("owner__name", "alert_type")
    )

    return render(request, "alerts/rules_list.html", {
        "rules": rules
    })


@login_required
def alert_rule_toggle_view(request, pk: int):
    if not user_is_admin_like(request.user):
        return HttpResponseForbidden()

    rule = get_object_or_404(AlertRule, pk=pk)

    rule.enabled = not rule.enabled
    rule.save(update_fields=["enabled"])

    return redirect("alert_rules_list")


# ---------------------------------------------------------
# USER ALERT PREFERENCES
# ---------------------------------------------------------

@login_required
def alert_preferences_view(request):
    allowed_owners = get_user_allowed_owners(request.user)

    prefs = (
        UserAlertPreference.objects
        .filter(user=request.user)
        .select_related("owner")
    )

    return render(request, "alerts/preferences.html", {
        "preferences": prefs,
        "owners": allowed_owners,
    })


@login_required
def alert_preference_mute_view(request):
    if request.method != "POST":
        return HttpResponseForbidden()

    alert_type = request.POST.get("alert_type")
    owner_id = request.POST.get("owner_id")
    days = int(request.POST.get("days", 30))

    muted_until = timezone.now() + timedelta(days=days)

    pref, _ = UserAlertPreference.objects.get_or_create(
        user=request.user,
        owner_id=owner_id if owner_id else None,
        alert_type=alert_type,
    )

    pref.muted_until = muted_until
    pref.save(update_fields=["muted_until"])

    return redirect("alert_preferences")
    
@login_required
def alert_rule_create_view(request):
    if not user_is_admin_like(request.user):
        return HttpResponseForbidden()

    allowed_owners = get_user_allowed_owners(request.user)

    if request.method == "POST":
        form = AlertRuleForm(request.POST, allowed_owners=allowed_owners)
        if form.is_valid():
            form.save()
            messages.success(request, "Alert rule created.")
            return redirect("alert_rules_list")
    else:
        form = AlertRuleForm(allowed_owners=allowed_owners)

    return render(request, "alerts/rule_form.html", {"form": form, "mode": "create"})


@login_required
def alert_rule_edit_view(request, pk: int):
    if not user_is_admin_like(request.user):
        return HttpResponseForbidden()

    allowed_owners = get_user_allowed_owners(request.user)
    rule = get_object_or_404(AlertRule, pk=pk)

    # prevent editing rules for owners you can’t access
    if rule.owner not in allowed_owners:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = AlertRuleForm(request.POST, instance=rule, allowed_owners=allowed_owners)
        if form.is_valid():
            form.save()
            messages.success(request, "Alert rule updated.")
            return redirect("alert_rules_list")
    else:
        form = AlertRuleForm(instance=rule, allowed_owners=allowed_owners)

    return render(request, "alerts/rule_form.html", {"form": form, "mode": "edit", "rule": rule})
    
@login_required
def alert_rule_toggle_view(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()

    if not user_is_admin_like(request.user):
        return HttpResponseForbidden()

    rule = get_object_or_404(AlertRule, pk=pk)

    allowed_owners = get_user_allowed_owners(request.user)
    if rule.owner not in allowed_owners:
        return HttpResponseForbidden()

    rule.enabled = not rule.enabled
    rule.save(update_fields=["enabled"])

    return redirect("alert_rules_list")