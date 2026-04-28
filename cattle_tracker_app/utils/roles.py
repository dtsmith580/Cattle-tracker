# utils/roles.py

def has_role(user, role_name):
    return user.groups.filter(name=role_name).exists()

def is_admin(user):
    return user.is_superuser or has_role(user, 'Admin')

def is_dev(user):
    return has_role(user, 'Dev')

def is_manager(user):
    return has_role(user, 'Managers')

def is_owner(user):
    return has_role(user, 'Owners')

def is_ranch_hand(user):
    return has_role(user, 'Ranch Hand')

def is_vet(user):
    return has_role(user, 'Veterinarians')
