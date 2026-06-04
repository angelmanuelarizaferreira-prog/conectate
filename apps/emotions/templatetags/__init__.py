from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allows accessing dict items in templates: {{ dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
