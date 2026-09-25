# -*- coding: utf-8 -*-
"""Utilitários para isolamento de dados por escola."""
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import Equipamento, Sala, Reserva, HorarioAula


def obter_escola_ativa(request):
    """Retorna a escola ativa do usuário, ou lança PermissionDenied."""
    if not request.escola_ativa:
        raise PermissionDenied("Você não tem escola ativa selecionada.")
    return request.escola_ativa


def obter_equipamento_seguro(request, equipamento_id):
    """Obtém um equipamento garantindo que pertence à escola ativa do usuário."""
    escola = obter_escola_ativa(request)
    equipamento = get_object_or_404(Equipamento, id=equipamento_id, escola=escola)
    return equipamento


def obter_sala_segura(request, sala_id):
    """Obtém uma sala garantindo que pertence à escola ativa do usuário."""
    escola = obter_escola_ativa(request)
    sala = get_object_or_404(Sala, id=sala_id, escola=escola)
    return sala


def obter_reserva_segura(request, reserva_id):
    """Obtém uma reserva garantindo que pertence à escola ativa do usuário."""
    escola = obter_escola_ativa(request)
    reserva = get_object_or_404(Reserva, id=reserva_id, escola=escola)
    return reserva


def obter_horarios_aula(request):
    """Retorna apenas os horários de aula da escola ativa."""
    escola = obter_escola_ativa(request)
    return HorarioAula.objects.filter(escola=escola, ativo=True).order_by('periodo', 'numero')


def filtrar_equipamentos(request, queryset=None):
    """Filtra equipamentos pela escola ativa."""
    escola = obter_escola_ativa(request)
    if queryset is None:
        queryset = Equipamento.objects.all()
    return queryset.filter(escola=escola)


def filtrar_salas(request, queryset=None):
    """Filtra salas pela escola ativa."""
    escola = obter_escola_ativa(request)
    if queryset is None:
        queryset = Sala.objects.all()
    return queryset.filter(escola=escola)


def filtrar_reservas(request, queryset=None):
    """Filtra reservas pela escola ativa."""
    escola = obter_escola_ativa(request)
    if queryset is None:
        queryset = Reserva.objects.all()
    return queryset.filter(escola=escola)