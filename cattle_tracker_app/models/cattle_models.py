from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from datetime import date, datetime
from datetime import date
from dateutil.relativedelta import relativedelta
import csv
from django.core.validators import FileExtensionValidator
# ✅ Correct
from .herd_sire_models import HerdSire
from django.utils import timezone


# Modular models
from django.db import models
from .breeding_models import BreedingHistory
from .health_models import HealthRecord
from .ownership_models import Owner, OwnerUserAccess
from .weight_models import WeightLog
from .alert_models import Alert
from .importlog_models import ImportLog
from .pasture_models import Pasture
from .leasedbull_models import LeasedBull  # adjust the import to your structure

class CattleQuerySet(models.QuerySet):
    def active_as_of(self, as_of_date):
        return (self.filter(date_added__lte=as_of_date)
                    .filter(Q(date_removed__isnull=True) | Q(date_removed__gt=as_of_date))
                    .exclude(status__in=["sold","dead"]))

class Cattle(models.Model):
    ANIMAL_TYPE_CHOICES = [
        ('heifer', 'Heifer'),
        ('cow', 'Cow'),
        ('bull', 'Bull'),
        ('steer', 'Steer'),
    ]

    STATUS_CHOICES = [
        ('alive', 'Alive'),
        ('sold', 'Sold'),
        ('deceased', 'Deceased'),
        ('missing', 'Missing'),
        ('stolen', 'Stolen'),
    ]
    
    BREEDING_METHOD_CHOICES = [
    ('natural', 'Natural'),
    ('ai', 'Artificial Insemination'),
    ]
    
    SIRE_TYPE_CHOICES = [
        ('owned', 'Owned'),
        ('donor', 'Donor'),
        ('leased', 'Leased'),
    ]
    sex_choices = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    PREGNANCY_STATUS_CHOICES = [
    ('open', 'Open'),
    ('bred', 'Bred'),
]
    objects = CattleQuerySet.as_manager()
    pregnancy_status = models.CharField(
        max_length=10,
        choices=PREGNANCY_STATUS_CHOICES,
        null=True,
        blank=True,
        default='',
        help_text="Current pregnancy status"
    )
    pasture = models.ForeignKey(Pasture, null=True, blank=True, on_delete=models.SET_NULL, related_name='cattle')
    ear_tag = models.CharField(max_length=20, unique=True)
    owner = models.ForeignKey('cattle_tracker_app.Owner', on_delete=models.SET_NULL, null=True, blank=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    breed = models.CharField(max_length=50)
    dob = models.DateField()
    sex = models.CharField(max_length=6, choices=sex_choices)
    
    # New: Breeding method and associated sire type
    breeding_method = models.CharField(
        max_length=10,
        choices=BREEDING_METHOD_CHOICES,
        default='',
        help_text="How the animal was bred"
    )
    paddock = models.ForeignKey(
        'cattle_tracker_app.Paddock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cattle_here'
    )

    sire = models.ForeignKey('Cattle', on_delete=models.SET_NULL, null=True, blank=True)
    herd_sire = models.ForeignKey('HerdSire', on_delete=models.SET_NULL, null=True, blank=True)
    # … your existing fields …
    date_added = models.DateField(default=timezone.now, editable=True, db_index=True)

    # Optionally: track removals (sold / deceased) similarly
    date_removed = models.DateTimeField(null=True, blank=True)
    
    sire_type = models.CharField(null=True, blank=True, max_length=10, choices=SIRE_TYPE_CHOICES)
    dam = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='dam_of')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='alive')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_date = models.DateField(null=True, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchased_from = models.CharField(max_length=255, blank=True, null=True)
    sold_to = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(
        upload_to='cattle_photos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    animal_type = models.CharField(
        max_length=10,
        choices=ANIMAL_TYPE_CHOICES,
        default=''
    )
    is_leased = models.BooleanField(default=False)
    
    
    leased_bull = models.ForeignKey(
        'cattle_tracker_app.LeasedBull',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cattle_bred_by_leased_bull'
    )
    
    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"{self.ear_tag} - {self.breed} ({self.get_status_display()})"

    @property
    def age(self):
        return self.paddock.pasture if self.paddock else None

    @property
    def land_property(self):
        return (self.paddock.pasture.land_property
                if self.paddock and self.paddock.pasture else None)
                
        today = date.today()
        delta = relativedelta(today, self.dob)

        parts = []
        if delta.years:
            parts.append(f"{delta.years} year{'s' if delta.years != 1 else ''}")
        if delta.months:
            parts.append(f"{delta.months} month{'s' if delta.months != 1 else ''}")
        if delta.days:
            parts.append(f"{delta.days} day{'s' if delta.days != 1 else ''}")

        return ", ".join(parts) if parts else "0 days"