# herd_sire_models.py
from django.db import models
from cattle_tracker_app.constants.choices import CLEANUP_METHOD_CHOICES

class HerdSire(models.Model):
    SEMEN_TYPE_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('regular', 'Regular'),
    ]
    
    CLEANUP_METHOD_CHOICES = [
        ('natural', 'Natural'),
        ('ai', 'Artificial Insemination'),
    ]
    
    image = models.ImageField(upload_to='herd_sires/', null=True, blank=True)
    name = models.CharField(max_length=100)
    semen_type = models.CharField(max_length=10, choices=SEMEN_TYPE_CHOICES, default='regular')
    profile_link = models.URLField(blank=True, null=True)
    cleanup_method = models.CharField(max_length=10, choices=CLEANUP_METHOD_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"{self.name} ({self.get_semen_type_display()})"
