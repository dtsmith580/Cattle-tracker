# cattle_tracker_app/views/settings_views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from cattle_tracker_app.models.settings_models import RanchSetting
from cattle_tracker_app.forms.settings_forms import RanchSettingForm

@login_required
def edit_ranch_settings(request):
    settings_obj, _ = RanchSetting.objects.get_or_create(owner=request.user)
    if request.method == "POST":
        form = RanchSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            # Optional: Add success message
            return redirect("edit_ranch_settings")
    else:
        form = RanchSettingForm(instance=settings_obj)
    return render(request, "settings/edit_ranch_settings.html", {"form": form})


@login_required
def ranch_settings_view(request):
    ranch = RanchSettings.objects.first()
    form = RanchSettingsForm(request.POST or None, instance=ranch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Ranch settings updated successfully.")
        return redirect('ranch_settings')

    return render(request, 'settings/ranch_settings.html', {'form': form})