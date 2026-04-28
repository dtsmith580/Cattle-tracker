from django.db import models
from django.contrib.auth.models import User

class Owner(models.Model):
    name = models.CharField(max_length=100)
    # Renamed for clarity: the primary account user for this owner profile
    User = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_profile'
    )
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'cattle_tracker_app'

    def __str__(self):
        return self.name

class OwnerUserAccess(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('manager', 'Manager'),
        ('vet', 'Veterinarian'),
        ('farmhand', 'Farmhand'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owner_access_records'
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name='access_records'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        app_label = 'cattle_tracker_app'
        unique_together = ('user', 'owner')

    def __str__(self):
        return f"{self.user.username} → {self.owner.name} ({self.role})"

# Add a ManyToManyField on User for quick access to associated Owners
User.add_to_class(
    'owners',
    models.ManyToManyField(
        Owner,
        through='cattle_tracker_app.OwnerUserAccess',
        related_name='users_with_access'
    )
)


# ---- Access helpers (used across the app) ----

def get_user_allowed_owners(user):
    """
    Return a queryset of Owner rows the user can access.
    Superusers see all owners; everyone else is limited by OwnerUserAccess.
    """
    if getattr(user, "is_superuser", False):
        return Owner.objects.all()
    owner_ids = OwnerUserAccess.objects.filter(user=user).values_list('owner_id', flat=True)
    return Owner.objects.filter(id__in=owner_ids)

def get_user_allowed_owner_ids(user):
    return get_user_allowed_owners(user).values_list("id", flat=True)

def user_can_access_cattle(user, cattle):
    """
    True if the cattle's owner is in the user's allowed owners.
    Uses a DB-side filter (no big lists in Python).
    """
    return get_user_allowed_owners(user).filter(id=getattr(cattle, "owner_id", None)).exists()
