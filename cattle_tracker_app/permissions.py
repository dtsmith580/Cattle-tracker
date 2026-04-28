# cattle_tracker_app/permissions.py
from cattle_tracker_app.models.ownership_models import OwnerUserAccess

def user_can_edit_paddock(user, paddock):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Managers/Vets/Admin/Dev groups could be allowed as you prefer.
    # Owner-based check:
    if paddock.owner_id is None:
        return False
    allowed_owner_ids = set(
        OwnerUserAccess.objects
        .filter(user=user)
        .values_list('owner_id', flat=True)
    )
    return paddock.owner_id in allowed_owner_ids
