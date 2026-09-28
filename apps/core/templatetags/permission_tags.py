from django import template

register = template.Library()

@register.filter
def has_perm(user, perm_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return user.has_perm_code(perm_code)
    return False

@register.filter
def can_edit(user, submodule_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return (
            user.has_perm_code(f"{submodule_code}.edit")
            or user.has_perm_code(f"{submodule_code}.update")
            or user.has_perm_code(f"patients.{submodule_code}.edit")
            or user.has_perm_code(f"patients.{submodule_code}.update")
        )
    return False

@register.filter
def can_delete(user, submodule_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return (
            user.has_perm_code(f"{submodule_code}.delete")
            or user.has_perm_code(f"patients.{submodule_code}.delete")
        )
    return False

@register.filter
def can_create(user, submodule_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return (
            user.has_perm_code(f"{submodule_code}.add")
            or user.has_perm_code(f"{submodule_code}.create")
            or user.has_perm_code(f"patients.{submodule_code}.add")
            or user.has_perm_code(f"patients.{submodule_code}.create")
        )
    return False

@register.filter
def can_export(user, submodule_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return (
            user.has_perm_code(f"{submodule_code}.export")
            or user.has_perm_code(f"{submodule_code}.print")
            or user.has_perm_code(f"patients.{submodule_code}.export")
            or user.has_perm_code(f"patients.{submodule_code}.print")
        )
    return False

@register.filter
def can_view(user, submodule_code):
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return (
            user.has_perm_code(f"{submodule_code}.view")
            or user.has_perm_code(submodule_code)
            or user.has_perm_code(f"patients.{submodule_code}.view")
            or user.has_perm_code(f"patients.{submodule_code}")
        )
    return False

@register.filter
def has_any_perm(user, perm_csv):
    if not user or not user.is_authenticated:
        return False
    if not hasattr(user, 'has_perm_code'):
        return False
    perms = [p.strip() for p in perm_csv.split(',') if p.strip()]
    return any(user.has_perm_code(p) for p in perms)
