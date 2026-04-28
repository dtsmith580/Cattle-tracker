from django.db import models


class WeightLog(models.Model):
    cattle = models.ForeignKey(
        'Cattle',
        on_delete=models.CASCADE,
        related_name='weight_logs'
    )
    # Automatically record when this log entry was created
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        #app_label = 'cattle_tracker_app'
        ordering = ['-date']

    def __str__(self):
        return f"{self.cattle.ear_tag} - {self.weight} lbs on {self.date}"
