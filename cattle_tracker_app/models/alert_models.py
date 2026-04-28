from django.db import models
from django.conf import settings
from django.utils import timezone


class Alert(models.Model):
    ALERT_TYPES = [
        ('pregnancy_check', 'Pregnancy Confirmation Reminder'),
        ('calving_reminder', 'Upcoming Calving Reminder'),
        ('missed_pregnancy', 'Missed Pregnancy Alert'),
        ('failed_pregnancy', 'Failed Pregnancy Alert'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    dismissed = models.BooleanField(default=False)  # differs from resolved; "dismiss" = hide but not "handled"
    cattle = models.ForeignKey('cattle_tracker_app.Cattle', on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    alert_date = models.DateTimeField()  # When the alert should trigger
    resolved = models.BooleanField(default=False)

    def is_snoozed(self) -> bool:
        return self.snoozed_until is not None and self.snoozed_until > timezone.now()

    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return f"Alert for {self.cattle.ear_tag}: {self.get_alert_type_display()} ({self.alert_date})"


class UserAlertPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    owner = models.ForeignKey("cattle_tracker_app.Owner", on_delete=models.CASCADE, null=True, blank=True)
    alert_type = models.CharField(max_length=50)
    muted_until = models.DateTimeField(null=True, blank=True)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    sms_enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "owner", "alert_type")
        app_label = "cattle_tracker_app"


class AlertRule(models.Model):
    ALERT_TYPES = Alert.ALERT_TYPES  # reuse same list

    owner = models.ForeignKey("cattle_tracker_app.Owner", on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)

    lead_days = models.PositiveIntegerField(default=7)  # "how far in advance"
    enabled = models.BooleanField(default=True)

    # channels (start with in-app, keep email/sms ready)
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=False)
    sms = models.BooleanField(default=False)

    class Meta:
        app_label = "cattle_tracker_app"

    def __str__(self):
        return f"{self.owner} - {self.alert_type} ({self.lead_days}d)"
