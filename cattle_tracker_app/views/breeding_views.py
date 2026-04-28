# cattle_tracker_app/views/breeding_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from cattle_tracker_app.models.breeding_models import BreedingRecord
from cattle_tracker_app.forms.breeding_forms import BreedingHistoryAdminForm

@login_required
def breeding_history_view(request):
    """
    Normal (non-admin) breeding history page.
    Template: templates/breeding/breeding_history.html
    """
    # Optional: later filter by allowed owners / ranch access
    records = BreedingRecord.objects.select_related(
        "cow", "bull", "herd_sire", "cleanup_sire", "cleanup_herd_sire"
    ).order_by("-breeding_date")

    return render(request, "breeding/breeding_history.html", {
        "breeding_records": records,
    })
    
    
@login_required
def breeding_admin_view(request):
    record_id = request.GET.get("edit")
    instance = get_object_or_404(BreedingRecord, pk=record_id) if record_id else None
    
    form = BreedingHistoryAdminForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        if instance:
            messages.success(request, "✅ Breeding record updated successfully.")
        else:
            messages.success(request, "✅ Breeding record created.")
        return redirect("breeding_admin")

    breeding_records = BreedingRecord.objects.order_by("-breeding_date")[:10]
    return render(request, "admin/breeding_admin.html", {
        "form": form,
        "breeding_records": breeding_records,
    })


@login_required
def edit_breeding_record(request, pk):
    return redirect(f"{reverse('breeding_admin')}?edit={pk}")


@login_required
def delete_breeding_record(request, pk):
    record = get_object_or_404(BreedingRecord, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑 Breeding record deleted successfully.")
    return redirect('breeding_admin')
