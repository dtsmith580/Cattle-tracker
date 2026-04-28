#cattle_tracker_app/turnout_models.py
from django.db import models
from django.utils.timezone import now
from .cattle_models import Cattle
from .ownership_models import Owner
from django.core.exceptions import ValidationError
from django.urls import reverse

class TurnoutGroup(models.Model):
    name = models.CharField(max_length=100, help_text="Optional name for this group (e.g., Spring Breeding 2025)")
    turn_in_date = models.DateField()
    turn_out_date = models.DateField(null=True, blank=True)
    bulls = models.ManyToManyField(Cattle, related_name="turnout_groups_as_bull", help_text="Bulls used for natural breeding")
    cows = models.ManyToManyField(Cattle, related_name="turnout_groups_as_cow", help_text="Cows/Heifers turned out for breeding")
    owners = models.ManyToManyField(Owner, help_text="Owner involved with this group (optional)")
       

    notes = models.TextField(blank=True, null=True)
    list_display = ['name', 'turn_in_date', 'turn_out_date']  # make sure these match the actual model fields
    

    class Meta:
        app_label = "cattle_tracker_app"
        verbose_name = "Turnout Group"
        verbose_name_plural = "Turnout Groups"

    def __str__(self):
        return self.name or f"Turnout Group {self.pk}"
        
    def get_absolute_url(self):
        return reverse("turnoutgroup_detail", args=[self.pk])
        
        