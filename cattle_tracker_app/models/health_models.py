# cattle_tracker_app/models/health_models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

# TIP: import the Cattle model via string to avoid circulars.
# Your Cattle model should already have: owner, status, etc.
# related_name choices align with your existing style.

class HealthRecord(models.Model):
    class EventType(models.TextChoices):
        VACCINATION = 'vaccination', 'Vaccination'
        PREGCHECK   = 'pregcheck',   'Pregcheck'
        CASTRATION  = 'castration',  'Castration'
        TREATMENT   = 'treatment',   'Treatment'
        ILLNESS     = 'illness',     'Illness'
        INJURY      = 'injury',      'Injury'
        DEWORMING   = 'deworming',   'Deworming'
        HOOF_TRIM   = 'hoof_trim',   'Hoof Trim'
        OTHER       = 'other',       'Other'

    cattle       = models.ForeignKey('Cattle', on_delete=models.CASCADE, related_name='health_records')
    date         = models.DateField(default=timezone.now)
    event_type   = models.CharField(max_length=20, choices=EventType.choices, null=True, blank=True, )
    title        = models.CharField(max_length=120, blank=True, help_text="Short label (optional)")
    description  = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    cost         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_due     = models.DateField(default=timezone.now, blank=True, help_text="For boosters, follow-ups, deworming schedules, etc.")
    attachment   = models.FileField(upload_to='health_records/', blank=True, null=True)

    created_at   = models.DateTimeField(default=timezone.now, editable=False,db_index=True,)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['event_type', 'date']),
            models.Index(fields=['next_due']),
        ]

    def __str__(self):
        animal = getattr(self.cattle, 'ear_tag', self.cattle_id)
        return f"{animal} · {self.get_event_type_display()} · {self.date:%Y-%m-%d}"


class VaccinationRecord(models.Model):
    #"""
    #Optional details for event_type=vaccination. Kept separate to keep HealthRecord lean.
    #"""
    health_record          = models.ForeignKey('HealthRecord', related_name='vaccinations', on_delete=models.CASCADE, null=True, blank=True, )
    vaccine_name           = models.CharField(max_length=100)
    dose                   = models.CharField(max_length=50, blank=True, help_text="e.g., 5 mL")
    administration_method  = models.CharField(max_length=50, blank=True, help_text="e.g., SubQ, IM, intranasal")
    batch_number           = models.CharField(max_length=50, blank=True)
    withdrawal_date        = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Vaccination: {self.vaccine_name} ({self.health_record})"


class CastrationRecord(models.Model):
    #"""
    #Optional details for event_type=castration.
    #"""
    METHOD_CHOICES = [
        ('banding', 'Banding/Elastrator'),
        ('surgical', 'Surgical'),
        ('burdizzo', 'Burdizzo/Emasculatome'),
        ('other', 'Other'),
    ]
    health_record   = models.OneToOneField('HealthRecord', on_delete=models.CASCADE, related_name='castration_detail')
    method          = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True)
    age_days        = models.PositiveIntegerField(null=True, blank=True)
    complications   = models.TextField(blank=True)

    def __str__(self):
        return f"Castration ({self.get_method_display() or 'Unspecified'}) for {self.health_record}"
