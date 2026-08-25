from django import template

register = template.Library()

@register.filter
def has_perm(user, perm_code):
    if not user.is_authenticated:
        return False
    if hasattr(user, 'has_perm_code'):
        return user.has_perm_code(perm_code)
    return False
