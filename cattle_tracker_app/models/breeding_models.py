from django.db import models 
from datetime import date  
from django.utils.timezone import now
#from .herd_sire_models import HerdSire
from .herd_sire_models import HerdSire 
from cattle_tracker_app.constants.choices import CLEANUP_METHOD_CHOICES, BREEDING_METHOD_CHOICES

class BreedingRecord(models.Model):
    cow = models.ForeignKey(
        'cattle_tracker_app.Cattle',
        
        on_delete=models.CASCADE,
        related_name="breeding_attempts"
    )
    bull = models.ForeignKey(
        'cattle_tracker_app.Cattle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sired_offspring"
    )
    breeding_date = models.DateField()
    method = models.CharField(max_length=10, choices=BREEDING_METHOD_CHOICES)
    notes = models.TextField(blank=True, null=True)
    is_leased = models.BooleanField(default=False)

    # Primary AI sire
    herd_sire = models.ForeignKey(
        HerdSire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='breeding_usages',
        help_text="AI sire used for this breeding"
    )

    # Cleanup breeding setup
    cleanup_method = models.CharField(
        null=True,
        blank=True,
        max_length=10,
        choices=CLEANUP_METHOD_CHOICES,
        help_text="How the cow was cleaned up after initial breeding"
    )
    cleanup_sire = models.ForeignKey(
        'cattle_tracker_app.Cattle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cleanup_breedings',
        help_text="Used for natural breeding cleanup"
    )
    cleanup_herd_sire = models.ForeignKey(
        HerdSire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cleanup_breeding_usages',
        help_text="AI sire used for cleanup"
    )

    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"{self.cow.ear_tag} x {self.bull.ear_tag if self.bull else 'Unknown'} ({self.breeding_date})"
        
class BreedingHistory(models.Model):
    cow = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.CASCADE, related_name="breeding_records")
    bull = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.SET_NULL, null=True, related_name="offspring_records")
    breeding_date = models.DateField(default=now)
    pregnancy_confirmation_date = models.DateField(blank=True, null=True)
    expected_calving_date = models.DateField(blank=True, null=True)
    calving_outcome = models.CharField(
        max_length=20,
        choices=[('successful', 'Successful'), ('miscarriage', 'Miscarriage'), ('stillborn', 'Stillborn')],
        blank=True, null=True
    )
    offspring = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.SET_NULL, null=True, blank=True, related_name="born_from")
    class Meta:
        app_label = 'cattle_tracker_app'
    def save(self, *args, **kwargs):
        # Auto-calculate expected calving date (283 days from breeding)
        if self.breeding_date and not self.expected_calving_date:
            from datetime import timedelta
            self.expected_calving_date = self.breeding_date + timedelta(days=283)
        super().save(*args, **kwargs)
        
        
class PregnancyRecord(models.Model):
    STATUS_CHOICES = [
        ('pregnant', 'Pregnant'),
        ('aborted', 'Aborted'),
        ('stillbirth', 'Stillbirth'),
        ('successful', 'Successful'),
    ]
    
    cow = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.CASCADE, related_name="pregnancies")
    breeding_record = models.ForeignKey(BreedingRecord, on_delete=models.CASCADE, related_name="pregnancy")
    pregnancy_confirmed = models.BooleanField(default=False)
    expected_due_date = models.DateField(null=True, blank=True)
    pregnancy_status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='ongoing')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        app_label = 'cattle_tracker_app'
    def __str__(self):
        return f"Pregnancy for {self.cow.ear_tag} - {self.get_pregnancy_status_display()}"


class CalvingRecord(models.Model):
    dam = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.CASCADE, related_name="calves_birthed")
    sire = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.SET_NULL, null=True, blank=True, related_name="calves_sired")
    calf = models.OneToOneField('cattle_tracker_app.Cattle', on_delete=models.CASCADE, related_name="birth_record")
    birth_date = models.DateField()
    birth_weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    health_notes = models.TextField(blank=True, null=True)
    class Meta:
        app_label = 'cattle_tracker_app'
    def __str__(self):
        return f"Calving Record: {self.dam.ear_tag} → {self.calf.ear_tag} ({self.birth_date})"
 
 
