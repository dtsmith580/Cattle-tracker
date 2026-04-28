# cattle_tracker_app/views/settings_alerts_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def alerts_settings_view(request):
    # For now: just render the page so /settings/alerts/ stops 404'ing.
    return render(request, "settings/alerts_settings.html", {})