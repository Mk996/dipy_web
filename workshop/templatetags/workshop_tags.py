
from django import template
# from django.conf import settings
from workshop.models import Workshop

register = template.Library()


@register.inclusion_tag('workshop/workshop_menu.html')
def show_workshop_menu():
    all_workshops = Workshop.objects.filter(is_published=True).order_by('-start_date')
    return {'all_workshops': all_workshops}


@register.filter(name='is_lesson')
def is_lesson(track):
    return hasattr(track, 'lesson')
