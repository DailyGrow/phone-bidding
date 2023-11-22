from django import template
from core.models import Order

register = template.Library()


@register.filter
def notification_count(user):
    return 0