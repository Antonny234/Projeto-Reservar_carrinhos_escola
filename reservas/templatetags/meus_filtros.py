# app/reservas/templatetags/meus_filtros.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(f'aluno_{key}')