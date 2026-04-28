from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ImportLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    record_type = models.CharField(max_length=50)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True)

    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"{self.record_type} import by {self.imported_by or 'Unknown'} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
