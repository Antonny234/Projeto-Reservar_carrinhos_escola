from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from datetime import date, datetime, timedelta
from django.db.models import Sum
from ..models import PerfilProfessor, CodigoVerificacao
from ..whatsapp_utils import enviar_codigo_email, EmailError
from ..models import (
    Aluno, NumeroReservaQuantidade, RegistroUso, Reserva, Equipamento, Sala, Notebook, PerfilAdm,
    HorarioAula,BloqueioEquipamento,
)
from ..forms import ReservaForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
import pandas as pd
import re
from django.urls import reverse
from urllib.parse import urlencode

import logging

logger = logging.getLogger(__name__)

# Helper
from .helpers import _professor_requer_aprovacao, _requer_aprovacao_para_reserva, _equipamentos_bloqueados, enviar_telegram

def _todos_horarios_por_periodo():
    """Dict {periodo: [(inicio, fim), ...]} com os horários ativos, ordenados."""
    horarios = HorarioAula.objects.filter(ativo=True).order_by('periodo', 'numero')
    agrupado = {}
    for h in horarios:
        agrupado.setdefault(h.periodo, []).append((h.horario_inicio, h.horario_fim))
    return agrupado


def _proximo_horario(horario_inicio):
    if isinstance(horario_inicio, str):
        try:
            horario_inicio = datetime.strptime(horario_inicio[:5], '%H:%M').time()
        except ValueError:
            return None

    agrupado = _todos_horarios_por_periodo()
    for lista_periodo in agrupado.values():
        for indice, (ini, fim) in enumerate(lista_periodo):
            if ini == horario_inicio:
                if indice + 1 < len(lista_periodo):
                    return lista_periodo[indice + 1]
                return None
    return None


def _horario_existe(horario_inicio, horario_fim):
    return HorarioAula.objects.filter(
        ativo=True, horario_inicio=horario_inicio, horario_fim=horario_fim
    ).exists()

def home(request):
    return render(request, 'apresentacao.html')
