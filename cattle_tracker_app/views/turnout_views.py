# cattle_tracker_app/views/turnout_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from ..forms.turnout_forms import TurnoutGroupForm
from ..models import TurnoutGroup

from django.views.generic.edit import CreateView, UpdateView

from django.views.generic.edit import CreateView, UpdateView
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.forms.models import model_to_dict
from django.db import transaction
import json

from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.paddock_models import Paddock
from cattle_tracker_app.forms.cattle_forms import CattleForm  # adjust path if different

class TurnoutGroupListView(ListView):
    model = TurnoutGroup
    template_name = "turnout/turnoutgroup_list.html"
    context_object_name = "groups"
    paginate_by = 25

class TurnoutGroupDetailView(LoginRequiredMixin, DetailView):
    model = TurnoutGroup
    template_name = "turnout/turnoutgroup_detail.html"
    context_object_name = "group"

class TurnoutGroupCreateView(LoginRequiredMixin, CreateView):
    model = TurnoutGroup
    form_class = TurnoutGroupForm
    template_name = "turnout/turnoutgroup_form.html"
    success_url = None  # we’ll compute dynamically

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        return self.redirect_to_detail()

    def redirect_to_detail(self):
        return self.response_class(
            request=self.request,
            redirect_to=self.object.get_absolute_url()
        )

class TurnoutGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = TurnoutGroup
    form_class = TurnoutGroupForm
    template_name = "turnout/turnoutgroup_form.html"  # reuse the same form template

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return self.object.get_absolute_url()
