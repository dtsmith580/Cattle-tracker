# cattle_tracker_app/models/herd_bull_models.py
from django.db import models
from django.urls import reverse

class HerdBull(models.Model):
    """
    Profile for an owned, live herd bull you keep for breeding.
    One-to-one with a Cattle row whose animal_type='Bull' and status active.
    """
    cattle = models.OneToOneField(
        "cattle_tracker_app.Cattle",
        on_delete=models.CASCADE,
        related_name="herd_bull_profile"
    )

    # Repro / soundness tracking
    fertility_test_date = models.DateField(blank=True, null=True)
    fertility_status = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., Satisfactory, Questionable")
    scrotal_circumference_cm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    frame_score = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)

    # Semen / genetics
    semen_collected = models.BooleanField(default=False)
    semen_straws_on_hand = models.PositiveIntegerField(default=0)
    semen_storage_location = models.CharField(max_length=120, blank=True, null=True)
    epd_profile_url = models.URLField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    class Meta:
        app_label = "cattle_tracker_app"
        verbose_name = "Herd Bull"
        verbose_name_plural = "Herd Bulls"

    def __str__(self):
        tag = self.cattle.ear_tag or f"ID {self.cattle.pk}"
        return f"Herd Bull: {tag}"

    # --- Useful rollups ---
    @property
    def total_calves_sired(self):
        # Uses your existing parentage link: offspring have sire = this bull
        return self.cattle.cattle_set.filter().count()  # reverse FK default: Cattle -> sire

    @property
    def calves_sired_qs(self):
        # Handy queryset for detail page tables
        return self.cattle.cattle_set.select_related("owner").order_by("-dob")

    def get_absolute_url(self):
        return reverse("herd_bull_detail", args=[self.pk])
