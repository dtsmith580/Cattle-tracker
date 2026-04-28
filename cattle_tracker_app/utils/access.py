# cattle_tracker_app/utils/access.py
from django.contrib.auth.models import Group
from django.apps import apps

ADMIN_GROUP_NAMES = {"Admin", "Dev", "Managers", "Veterinarians"}

def user_is_admin_like(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ADMIN_GROUP_NAMES).exists()

def _get_models():
    """
    Resolve models via the app registry to avoid ModuleNotFoundError and
    circular imports regardless of how your modules are organized.
    """
    OwnerUserAccess = apps.get_model("cattle_tracker_app", "OwnerUserAccess")
    Owner = apps.get_model("cattle_tracker_app", "Owner")
    Cattle = apps.get_model("cattle_tracker_app", "Cattle")
    return OwnerUserAccess, Owner, Cattle

def get_user_allowed_owners(user):
    """Return a queryset of Owner the user can access."""
    OwnerUserAccess, Owner, Cattle = _get_models()
    if user_is_admin_like(user):
        owner_ids = (Cattle.objects.values_list("owner_id", flat=True).distinct())
        return Owner.objects.filter(id__in=owner_ids)
    return Owner.objects.filter(
        id__in=OwnerUserAccess.objects.filter(user=user)
                                      .values_list("owner_id", flat=True)
                                      .distinct()
    )

def get_user_allowed_owner_ids(user):
    return get_user_allowed_owners(user).values_list("id", flat=True)

def user_can_access_cattle(user, cattle):
    if user_is_admin_like(user):
        return True
    # DB-side check
    return get_user_allowed_owners(user).filter(id=cattle.owner_id).exists()
