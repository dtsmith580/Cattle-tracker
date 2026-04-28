from django.db import models

class LeasedBull(models.Model):
    ear_tag = models.CharField(max_length=20)
    breed = models.CharField(max_length=50, blank=True)
    breed_reg_num = models.CharField(null=True, blank=True, max_length=20)
    breed_reg_url = models.CharField(null=True, blank=True, max_length=100)
    dob = models.DateField(null=True, blank=True)
    lease_start = models.DateField()
    lease_end = models.DateField(null=True, blank=True)
    owner_name = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='leased_bulls/', null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.ear_tag} ({self.breed})"
