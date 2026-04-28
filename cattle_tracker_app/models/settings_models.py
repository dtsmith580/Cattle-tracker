from django.db import models
from django.conf import settings

class RanchSetting(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Or link to a Ranch/Company model if multi-tenant
    backup_frequency_hours = models.PositiveIntegerField(default=24, help_text="Backup frequency in hours (e.g., 24 for daily backups)")
    # Add more fields as needed
    name = models.CharField(max_length=200)
    mailing_address = models.TextField(blank=True, null=True, help_text="Mailing address for correspondence and reports.")
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"{self.owner}'s settings"
