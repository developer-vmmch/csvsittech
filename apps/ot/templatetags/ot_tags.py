from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access dict item by key in templates: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, False)
    return False
