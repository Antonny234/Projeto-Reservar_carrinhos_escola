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


def CriarConta(request):
    # Cadastro de professor: valida e-mail institucional, cria usuário inativo e envia código por e-mail
    if request.method == "POST":
        usuario = request.POST.get('usuario').strip()
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        confirmar = request.POST.get('confirmar_senha')

        dominios_permitidos = ("@professor.educacao.sp.gov.br", "@prof.educacao.sp.gov.br")

        if not usuario or not email or not senha:
            messages.error(request, "Preencha todos os campos!")
            return render(request, 'index.html')

        if not email.lower().endswith(dominios_permitidos):
            messages.error(request, "Erro: Apenas e-mails corporativos SEDUC!")
            return render(request, 'index.html')

        if senha != confirmar:
            messages.error(request, "As senhas não coincidem!")
            return render(request, 'index.html')

        if User.objects.filter(username=usuario).exists():
            messages.error(request, "Este nome de usuário já está em uso.")
            return render(request, 'index.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Este e-mail já está em uso.")
            return render(request, 'index.html')

        user = User.objects.create_user(username=usuario, email=email, password=senha)
        user.is_active = False  # só ativa depois de confirmar o código
        user.save()


        from ..models import PerfilProfessor
        PerfilProfessor.objects.create(usuario=user)

        codigo_obj = CodigoVerificacao.gerar(user, tipo='cadastro')
        try:
            enviar_codigo_email(email, codigo_obj.codigo)
        except EmailError as e:
            user.delete()
            messages.error(request, str(e))
            return render(request, 'index.html')

        request.session['cadastro_pendente_user_id'] = user.id
        messages.success(request, "Cadastro quase concluído! Enviamos um código para o seu e-mail.")
        return redirect('confirmar_cadastro')

    return render(request, 'index.html')


def Entrar(request):
    # Login: valida credenciais e redireciona pendências de confirmação de cadastro
    if request.method == "POST":
        usuario_digitado = request.POST.get('usuario').strip()
        senha_digitada = request.POST.get('senha').strip()

        user_obj = User.objects.filter(username=usuario_digitado).first()

        if not user_obj:
            messages.error(request, "Usuário não encontrado!")
            return render(request, 'longa.html')

        if not user_obj.is_active:
            messages.error(request, "Você ainda não confirmou seu cadastro pelo e-mail.")
            request.session['cadastro_pendente_user_id'] = user_obj.id
            return redirect('confirmar_cadastro')

        user = authenticate(request, username=usuario_digitado, password=senha_digitada)

        if user is None:
            messages.error(request, "Senha incorreta!")
            return render(request, 'longa.html')

        login(request, user)
        return redirect('mural')

    return render(request, 'longa.html')


def confirmar_cadastro(request):
    # Confirma o código enviado por e-mail e ativa a conta do professor
    user_id = request.session.get('cadastro_pendente_user_id')
    if not user_id:
        messages.error(request, "Nenhum cadastro pendente encontrado. Cadastre-se novamente.")
        return redirect('index')

    user = get_object_or_404(User, id=user_id, is_active=False)

    if request.method == "POST":
        codigo_digitado = request.POST.get('codigo', '').strip()
        codigo_obj = CodigoVerificacao.objects.filter(
            usuario=user, tipo='cadastro', codigo=codigo_digitado
        ).order_by('-criado_em').first()

        if not codigo_obj or not codigo_obj.valido():
            messages.error(request, "Código inválido ou expirado.")
            return render(request, 'confirmar_cadastro.html')

        codigo_obj.usado = True
        codigo_obj.save()

        user.is_active = True
        user.save()

        # perfil já foi criado no cadastro; nada extra a fazer aqui além do save
        perfil = user.perfil_professor
        perfil.save()

        del request.session['cadastro_pendente_user_id']
        messages.success(request, "Conta confirmada com sucesso! Faça login.")
        return redirect('longa')

    return render(request, 'confirmar_cadastro.html')


def reenviar_codigo_cadastro(request):
    # Gera e reenvia um novo código de confirmação para cadastro pendente
    user_id = request.session.get('cadastro_pendente_user_id')
    if not user_id:
        messages.error(request, "Nenhum cadastro pendente encontrado.")
        return redirect('index')

    user = get_object_or_404(User, id=user_id, is_active=False)
    codigo_obj = CodigoVerificacao.gerar(user, tipo='cadastro')
    try:
        enviar_codigo_email(user.email, codigo_obj.codigo)
        messages.success(request, "Reenviamos o código para o seu e-mail.")
    except EmailError as e:
        messages.error(request, str(e))

    return redirect('confirmar_cadastro')
