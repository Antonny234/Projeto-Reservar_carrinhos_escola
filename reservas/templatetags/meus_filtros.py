# app/reservas/templatetags/meus_filtros.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(f'aluno_{key}')


@register.filter
def get_value(dictionary, key):
    """Obtém um valor de um dicionário por sua chave no template."""
    return dictionary.get(key, '') if dictionary else ''
