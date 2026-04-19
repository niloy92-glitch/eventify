from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def brand_token(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default))
