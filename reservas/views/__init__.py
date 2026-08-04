from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import date, datetime
from django.db.models import Sum
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from ..models import (
    Aluno, NumeroReservaQuantidade, RegistroUso, Reserva,
    Equipamento, Sala, PerfilAdm, Notebook
)
from ..forms import ReservaForm

from .area_usuario import (
    home, CriarConta, Entrar, mural, excluir_reserva,
    listar_disponiveis, numeros_disponiveis, carregar_mural,
    carregar_mural_publico, carrinho_principal, atualizar_quantidade,
    importar_de_excel,confirmar_cadastro, reenviar_codigo_cadastro, view_tablet, status_tablet, camera_contagem,
    pagina_unico, reserva_quantidade, preencher_numeracao_quantidade, criar_pin,
)

from .are_admin import (
    aprovar_reserva, recusar_reserva, painel_reservas_dia,
    exportar_todas_fichas, exportar_ficha_excel, exportar_reservas_excel,
    painel_fichas, ficha_detalhe_json, verificar_fichas_ausentes,
    verificar_carrinho, atualizar_faixa_numeracao, alternar_status_notebook,
    pendentes_numeracao, painel_reservas_quantidade, menu_ajax,
)

from .redefinir_senha import (
    redefinir_senha_usuario,
    redefinir_senha_confirmar,
)

from .foto import analisar_foto

__all__ = [
    'home','confirmar_cadastro','reenviar_codigo_cadastro', 'CriarConta', 'Entrar',
    'mural', 'excluir_reserva','listar_disponiveis', 'numeros_disponiveis', 'carregar_mural',
    'carregar_mural_publico', 'carrinho_principal', 'atualizar_quantidade',
    'importar_de_excel', 'view_tablet', 'status_tablet', 'camera_contagem',
    'pagina_unico', 'reserva_quantidade', 'preencher_numeracao_quantidade', 'criar_pin',
    'aprovar_reserva', 'recusar_reserva', 'painel_reservas_dia',
    'exportar_todas_fichas', 'exportar_ficha_excel', 'exportar_reservas_excel',
    'painel_fichas', 'ficha_detalhe_json', 'verificar_fichas_ausentes',
    'verificar_carrinho', 'atualizar_faixa_numeracao', 'alternar_status_notebook',
    'pendentes_numeracao', 'painel_reservas_quantidade', 'menu_ajax',
    'analisar_foto','redefinir_senha_usuario', 'redefinir_senha_confirmar',
]