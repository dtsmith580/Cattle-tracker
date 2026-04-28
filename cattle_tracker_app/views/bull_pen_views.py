# cattle_tracker_app/views/bull_pen_views.py
from django.core.paginator import Paginator
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cattle_tracker_app.models.herd_bull_models import HerdBull
from cattle_tracker_app.models.cattle_models import Cattle  # adjust to your hub import
from cattle_tracker_app.forms.herd_bull_forms import HerdBullForm

def _allowed_owner_ids(user):
    try:
        from cattle_tracker_app.utils.access import get_user_allowed_owners
        return list(get_user_allowed_owners(user).values_list("id", flat=True))
    except Exception:
        return []

@login_required
def bull_pen_list(request):
    qs = HerdBull.objects.select_related("cattle", "cattle__owner")

    # Role-based bypass: admins/devs/managers/vets see all by default
    is_power_user = (
        request.user.is_superuser
        or request.user.groups.filter(name__in=["Admin", "Dev", "Managers", "Veterinarians"]).exists()
    )

    if not is_power_user:
        owner_ids = _allowed_owner_ids(request.user)
        # Only filter if we actually got a list; if helper returns empty/None, don't box the user out
        if owner_ids:
            qs = qs.filter(cattle__owner_id__in=owner_ids)

    # Keep live bulls; be flexible about status casing/labels
    qs = (
        qs.filter(cattle__animal_type__iexact="bull")
          .exclude(cattle__status__iexact="sold")
          .exclude(cattle__status__iexact="dead")
          .order_by("cattle__owner__name", "cattle__ear_tag")
    )

    paginator = Paginator(qs, 24)
    bulls = paginator.get_page(request.GET.get("page"))
    return render(request, "cattle/bull_pen_list.html", {"bulls": bulls})

@login_required
def herd_bull_detail(request, pk):
    hb = get_object_or_404(HerdBull.objects.select_related("cattle", "cattle__owner"), pk=pk)
    owner_ids = _allowed_owner_ids(request.user)
    if owner_ids and hb.cattle.owner_id not in owner_ids:
        messages.error(request, "You do not have access to this bull.")
        return redirect("bull_pen_list")

    offspring = hb.calves_sired_qs  # derived from Cattle.sire
    return render(request, "cattle/herd_bull_detail.html", {"hb": hb, "offspring": offspring})

@login_required
def herd_bull_create(request):
    if request.method == "POST":
        form = HerdBullForm(request.POST, request=request)
        if form.is_valid():
            hb = form.save()
            messages.success(request, "Herd bull profile created.")
            return redirect(hb.get_absolute_url())
    else:
        form = HerdBullForm(request=request)
    return render(request, "cattle/herd_bull_form.html", {"form": form})

@login_required
def herd_bull_edit(request, pk):
    hb = get_object_or_404(HerdBull, pk=pk)
    if request.method == "POST":
        form = HerdBullForm(request.POST, instance=hb, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, "Herd bull profile updated.")
            return redirect(hb.get_absolute_url())
    else:
        form = HerdBullForm(instance=hb, request=request)
    return render(request, "cattle/herd_bull_form.html", {"form": form, "hb": hb})
