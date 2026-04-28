# cattle_tracker_app/utils/access.py
from django.contrib.auth.models import Group
from cattle_tracker_app.ownership_models import OwnerUserAccess, Owner
from cattle_tracker_app.models import Cattle  # import from aggregator to avoid circulars

# Adjust the set to your policy. These are treated “admin-like” for owner scoping.
ADMIN_GROUP_NAMES = {"Admin", "Dev", "Managers", "Veterinarians"}

def user_is_admin_like(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ADMIN_GROUP_NAMES).exists()

def get_user_allowed_owners(user):
    """
    Returns a queryset of Owner objects the user can access.
    - Admin-like users: all owners that appear on any Cattle record.
    - Standard users: owners granted via OwnerUserAccess.
    """
    if user_is_admin_like(user):
        owner_ids = (Cattle.objects
                     .values_list("owner_id", flat=True)
                     .distinct())
        return Owner.objects.filter(id__in=owner_ids)
    return Owner.objects.filter(
        id__in=OwnerUserAccess.objects.filter(user=user)
                                      .values_list("owner_id", flat=True)
                                      .distinct()
    )

def get_user_allowed_owner_ids(user):
    """Convenience helper: owner IDs (flat list/queryset)."""
    return get_user_allowed_owners(user).values_list("id", flat=True)

def user_can_access_cattle(user, cattle):
    """
    Returns True if the user can access the given cattle record.
    Fast DB-side check; avoids materializing all owners in Python.
    """
    if user_is_admin_like(user):
        return True
    return get_user_allowed_owners(user).filter(id=cattle.owner_id).exists()
