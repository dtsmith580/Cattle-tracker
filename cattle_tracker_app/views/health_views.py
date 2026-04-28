# cattle_tracker_app/views/health_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import HealthRecord, VaccinationRecord, CastrationRecord, Cattle
from ..forms.health_forms import (
    HealthRecordForm,
    HerdVaccinationForm,
    VaccinationFormSet,  # multi-vaccine formset
)
from ..models.ownership_models import user_can_access_cattle, get_user_allowed_owners


@login_required
def health_list(request):
    """Paginated list of health records."""
    qs = HealthRecord.objects.select_related("cattle").order_by("-date")
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "health/health_list.html",
        {
            "page_obj": page_obj,
            "is_paginated": page_obj.paginator.num_pages > 1,
            "object_list": page_obj.object_list,
        },
    )


@login_required
def health_create(request, cattle_pk=None):
    """
    Create a HealthRecord and optionally 0..N VaccinationRecord rows.
    - Requires ≥1 vaccine when event_type == VACCINATION
    - Allows 0+ vaccines when event_type == ILLNESS
    """
    initial = {}
    if cattle_pk:
        cattle = get_object_or_404(Cattle, pk=cattle_pk)
        if not user_can_access_cattle(request.user, cattle):
            messages.error(request, "You do not have access to this animal.")
            return redirect("health_list")
        initial["cattle"] = cattle

    if request.method == "POST":
        form = HealthRecordForm(
            request.POST, request.FILES, request=request, use_vax_formset=True
        )
        formset = VaccinationFormSet(
            request.POST,
            queryset=VaccinationRecord.objects.none(),
            prefix="vax",
        )

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        # Enforce at least one vaccine when event is Vaccination
        if form_valid:
            etype = form.cleaned_data.get("event_type")
            must_have_vax = etype == HealthRecord.EventType.VACCINATION

            if formset_valid and must_have_vax:
                nonempty = 0
                for f in formset.forms:
                    cd = getattr(f, "cleaned_data", {}) or {}
                    if cd.get("DELETE"):
                        continue
                    if cd.get("vaccine_name"):
                        nonempty += 1
                if nonempty == 0:
                    formset_valid = False
                    messages.error(
                        request, "Add at least one vaccine for Vaccination events."
                    )

        if form_valid and formset_valid:
            with transaction.atomic():
                record = form.save()  # Castration cleanup handled by form when use_vax_formset=True
                etype = form.cleaned_data.get("event_type")

                if etype in (
                    HealthRecord.EventType.VACCINATION,
                    HealthRecord.EventType.ILLNESS,
                ):
                    # Save 0..N vaccinations for this encounter
                    instances = formset.save(commit=False)
                    for inst in instances:
                        # Skip rows that are effectively blank
                        if not getattr(inst, "vaccine_name", ""):
                            continue
                        inst.health_record = record
                        inst.save()
                    # Handle deletions (should be none on create, but harmless)
                    for obj in formset.deleted_objects:
                        obj.delete()
                else:
                    # Not vaccination/illness: ensure no stray vaccinations
                    VaccinationRecord.objects.filter(health_record=record).delete()

            messages.success(request, "Health record added.")
            next_url = request.POST.get("next") or reverse("health_list")
            return redirect(next_url)

        # Errors fall-through
        return render(
            request, "health/health_form.html", {"form": form, "formset": formset}
        )

    # GET
    form = HealthRecordForm(initial=initial, request=request, use_vax_formset=True)
    formset = VaccinationFormSet(
        queryset=VaccinationRecord.objects.none(), prefix="vax"
    )
    return render(
        request, "health/health_form.html", {"form": form, "formset": formset}
    )


@login_required
def health_edit(request, cattle_pk):
    """
    Edit a HealthRecord and its 0..N VaccinationRecord rows in one page.
    - Requires ≥1 vaccine when event_type == VACCINATION
    - Allows 0+ vaccines when event_type == ILLNESS
    - If event_type is switched away from VACCINATION/ILLNESS, associated vaccines will be cleared.
    """
    record = get_object_or_404(HealthRecord.objects.select_related("cattle"), pk=cattle_pk)
    if not user_can_access_cattle(request.user, record.cattle):
        messages.error(request, "You do not have access to this health record.")
        return redirect("health_list")

    if request.method == "POST":
        form = HealthRecordForm(
            request.POST,
            request.FILES,
            instance=record,
            request=request,
            use_vax_formset=True,
        )
        # Use current record's vaccines as queryset so edits/deletes work
        formset = VaccinationFormSet(
            request.POST,
            queryset=VaccinationRecord.objects.filter(health_record=record),
            prefix="vax",
        )

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        if form_valid:
            etype = form.cleaned_data.get("event_type")
            must_have_vax = etype == HealthRecord.EventType.VACCINATION
            if formset_valid and must_have_vax:
                nonempty = 0
                for f in formset.forms:
                    cd = getattr(f, "cleaned_data", {}) or {}
                    if cd.get("DELETE"):
                        continue
                    if cd.get("vaccine_name"):
                        nonempty += 1
                if nonempty == 0:
                    formset_valid = False
                    messages.error(
                        request, "Add at least one vaccine for Vaccination events."
                    )

        if form_valid and formset_valid:
            with transaction.atomic():
                record = form.save()  # castration logic handled by form when use_vax_formset=True
                etype = form.cleaned_data.get("event_type")

                if etype in (
                    HealthRecord.EventType.VACCINATION,
                    HealthRecord.EventType.ILLNESS,
                ):
                    # Save edits/additions
                    instances = formset.save(commit=False)
                    for inst in instances:
                        if not getattr(inst, "vaccine_name", ""):
                            continue
                        inst.health_record = record
                        inst.save()

                    # Deletions
                    for obj in formset.deleted_objects:
                        obj.delete()
                else:
                    # Switched to a non-vaccination/illness event: clear vaccines
                    VaccinationRecord.objects.filter(health_record=record).delete()

            messages.success(request, "Health record updated.")
            return redirect("health_list")

        # Errors fall-through
        return render(
            request,
            "health/health_form.html",
            {"form": form, "formset": formset, "record": record},
        )

    # GET: Pre-populate legacy extra fields (harmless if not shown in template)
    initial = {}
    if hasattr(record, "vaccination_detail"):
        v = record.vaccination_detail
        initial.update(
            {
                "vaccine_name": v.vaccine_name,
                "dose": v.dose,
                "administration_method": v.administration_method,
                "batch_number": v.batch_number,
                "withdrawal_date": v.withdrawal_date,
            }
        )
    if hasattr(record, "castration_detail"):
        c = record.castration_detail
        initial.update(
            {"method": c.method, "age_days": c.age_days, "complications": c.complications}
        )

    form = HealthRecordForm(
        instance=record, initial=initial, request=request, use_vax_formset=True
    )
    formset = VaccinationFormSet(
        queryset=VaccinationRecord.objects.filter(health_record=record),
        prefix="vax",
    )
    return render(
        request,
        "health/health_form.html",
        {"form": form, "formset": formset, "record": record},
    )


@login_required
def health_delete(request, pk):
    record = get_object_or_404(HealthRecord, pk=pk)
    if not user_can_access_cattle(request.user, record.cattle):
        messages.error(request, "You do not have access to this health record.")
        return redirect("health_list")

    if request.method == "POST":
        record.delete()
        messages.success(request, "Health record deleted.")
        return redirect("health_list")

    return render(request, "health/health_confirm_delete.html", {"record": record})


@login_required
def cattle_health_list(request, cattle_pk):
    cattle = get_object_or_404(Cattle, pk=cattle_pk)
    if not user_can_access_cattle(request.user, cattle):
        messages.error(request, "You do not have access to this animal.")
        return redirect("health_list")
    records = cattle.health_records.select_related("performed_by").order_by("-date", "-id")
    return render(
        request, "health/cattle_health_list.html", {"cattle": cattle, "records": records}
    )


@login_required
def herd_vaccination(request):
    """
    Bulk create vaccination HealthRecords + VaccinationRecord details for selected animals.
    """
    if request.method == "POST":
        form = HerdVaccinationForm(request.POST, request=request)
        if form.is_valid():
            data = form.cleaned_data
            count = 0
            for animal in data["cattle"]:
                if not user_can_access_cattle(request.user, animal):
                    continue
                hr = HealthRecord.objects.create(
                    cattle=animal,
                    date=data["date"],
                    event_type=HealthRecord.EventType.VACCINATION,
                    title=f"Vaccination: {data['vaccine_name']}",
                    description="Bulk herd vaccination entry.",
                    cost=data.get("cost"),
                    next_due=data.get("next_due"),
                )
                VaccinationRecord.objects.create(
                    health_record=hr,
                    vaccine_name=data["vaccine_name"],
                    dose=data.get("dose", ""),
                    administration_method=data.get("administration_method", ""),
                    batch_number=data.get("batch_number", ""),
                    withdrawal_date=data.get("withdrawal_date"),
                )
                count += 1
            messages.success(request, f"Saved vaccination for {count} animals.")
            return redirect("health_list")
    else:
        form = HerdVaccinationForm(request=request)

    return render(request, "health/herd_vaccination_form.html", {"form": form})
