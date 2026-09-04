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
    Equipamento, Sala, PerfilAdm, Notebook, HorarioAula
)
from ..forms import ReservaForm,EquipamentoForm, HorarioAulaForm

from .area_usuario import (
    home, CriarConta, Entrar, mural, excluir_reserva,
    listar_disponiveis, numeros_disponiveis, carregar_mural,
    carregar_mural_publico, carrinho_principal, atualizar_quantidade,
    importar_de_excel,confirmar_cadastro, reenviar_codigo_cadastro, view_tablet, status_tablet, camera_contagem,
    pagina_unico, reserva_quantidade, preencher_numeracao_quantidade, criar_pin,buscar_reserva_ativa,
    notificar_erro_telegram, reportar_notebook_quebrado,todos_horarios,_proximo_horario,
    _horario_existe,escolher_carrinho,login_ajax,logout_ajax,
)

from .are_admin import (
    aprovar_reserva, excluir_reserva_fixa, recusar_reserva, painel_reservas_dia,
    exportar_todas_fichas, exportar_ficha_excel, exportar_reservas_excel,
    painel_fichas, ficha_detalhe_json, verificar_fichas_ausentes,
    verificar_carrinho, atualizar_faixa_numeracao, alternar_status_notebook,
    pendentes_numeracao, painel_reservas_quantidade, menu_ajax,reserva_fixas_web,lista_reservas_fixas,
    excluir_reserva_fixa,analise_sistema, notebooks_quebrados, reativar_notebook,
)
from .cadastro import (
    cadastros,adicionar_equipamento,
    editar_equipamento,excluir_equipamento,adicionar_horario,editar_horario,excluir_horario,
    remover_liberacao,remover_bloqueio,

)
from .inventario import(
    is_staff,inventario_lista,inventario_detalhe,equipamento_novo,
    equipamento_novo,grupo_novo,transferir_equipamento,equipamento_excluir,
    equipamento_editar,grupo_equipamentos,grupo_excluir
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
    'aprovar_reserva', 'excluir_reserva_fixa', 'recusar_reserva', 'painel_reservas_dia',
    'exportar_todas_fichas', 'exportar_ficha_excel', 'exportar_reservas_excel',
    'painel_fichas', 'ficha_detalhe_json', 'verificar_fichas_ausentes',
    'verificar_carrinho', 'atualizar_faixa_numeracao', 'alternar_status_notebook',
    'pendentes_numeracao', 'painel_reservas_quantidade', 'menu_ajax',
    'analisar_foto','redefinir_senha_usuario', 'redefinir_senha_confirmar','buscar_reserva_ativa',
    'notificar_erro_telegram','reportar_notebook_quebrado','reserva_fixas_web','lista_reservas_fixas','analise_sistema',
    'notebooks_quebrados','reativar_notebook','cadastros,adicionar_equipamento',
    'editar_equipamento','excluir_equipamento','adicionar_horario,editar_horario','excluir_horario','todos_horarios',
    '_proximo_horario','_horario_existe','remover_liberacao','remover_bloqueio','escolher_carrinho','login_ajax',
    'logout_ajax','is_staff','inventario_lista','inventario_detalhe','equipamento_novo','grupo_novo','transferir_equipamento',
    'cadastros','adicionar_equipamento','equipamento_excluir','equipamento_editar','grupo_equipamentos','grupo_excluir'
]
