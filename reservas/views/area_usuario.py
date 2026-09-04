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
    return render(request, 'longa.html')


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


@login_required
def listar_disponiveis(request):
    # Retorna via AJAX os equipamentos disponíveis (e quantidade livre) para um horário.
    # Se aula_seguida=sim, só lista carrinhos livres nos DOIS horários seguidos
    # (o selecionado E o próximo horário real da grade).
    data_sel = request.GET.get('data')
    horario_inicio_sel = request.GET.get('horario_inicio')
    horario_fim_sel = request.GET.get('horario_fim')
    aula_seguida = request.GET.get('aula_seguida') == 'sim'

    try:
        data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_sel, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_sel, '%H:%M').time()

        # Monta a lista de horários que precisam estar livres
        slots = [(horario_inicio_obj, horario_fim_obj)]
        proximo_info = None
        if aula_seguida:
            proximo = _proximo_horario(horario_inicio_obj)
            if proximo:
                slots.append(proximo)
                proximo_info = {
                    'inicio': proximo[0].strftime('%H:%M'),
                    'fim': proximo[1].strftime('%H:%M'),
                }

       
        for slot_ini, slot_fim in slots:
            ocupados_inteiro = set(Reserva.objects.filter(
                data_uso=data_sel_obj,
                horario_inicio=slot_ini,
                horario_fim=slot_fim,
                status__in=['confirmada', 'pendente'],
                numero_notebook_unico__isnull=True,
                quantidade__isnull=True,
            ).values_list('equipamento_id', flat=True))

            bloqueados = _equipamentos_bloqueados(data_sel_obj, slot_ini, slot_fim)

            disponiveis = Equipamento.objects.exclude(id__in=ocupados_inteiro | bloqueados)

        # Soma das quantidades já reservadas via unico.html, por carrinho, EM CADA horário
        reservado_por_slot = []
        for slot_ini, slot_fim in slots:
            reservas_quantidade = Reserva.objects.filter(
                data_uso=data_sel_obj,
                horario_inicio=slot_ini,
                horario_fim=slot_fim,
                status__in=['confirmada', 'pendente'],
                quantidade__isnull=False,
            ).values('equipamento_id').annotate(total=Sum('quantidade'))

            reservado_por_slot.append({r['equipamento_id']: r['total'] for r in reservas_quantidade})

        data = []
        for e in disponiveis:
            # Disponível = menor sobra entre todos os horários exigidos
            quantidades_por_slot = [
                max(e.quantidade - slot_map.get(e.id, 0), 0)
                for slot_map in reservado_por_slot
            ]
            qtd_disponivel = min(quantidades_por_slot) if quantidades_por_slot else 0
            data.append({
                'id': e.id,
                'nome': e.nome,
                'quantidade': qtd_disponivel,
                'tem_numeracao': bool(e.numero_inicial and e.numero_final),
            })

        return JsonResponse({
            'equipamentos': data,
            'proximo_horario': proximo_info,
            'aula_dupla_valida': bool(aula_seguida and proximo_info),
        })

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)

# Mural / Reservas

@login_required
def mural(request):
    # Tela principal: lista reservas do dia e processa criação de nova reserva (com opção de aula seguida)
    agora = timezone.localtime(timezone.now())
    hoje = agora.date()
    hora_atual = agora.time()

    data_param = request.GET.get('data')
    data_selecionada = data_param if data_param else hoje.strftime('%Y-%m-%d')
    data_selecionada_obj = datetime.strptime(data_selecionada, '%Y-%m-%d').date()
    if request.method == "POST":
        data_reserva_str = request.POST.get('data')
        horario_inicio = request.POST.get('horario_inicio')
        horario_fim = request.POST.get('horario_fim')

        data_reservae = datetime.strptime(data_reserva_str, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim, '%H:%M').time()

        # 1) Bloqueia data/horário que já passou
        if data_reservae < hoje:
            messages.error(
                request,
                f"⚠️ Não é possível reservar para o dia {data_reservae.strftime('%d/%m/%Y')}, "
                f"pois hoje é {hoje.strftime('%d/%m/%Y')}."
            )
            return redirect(f"/Logar/?data={data_reserva_str}")

        if data_reservae == hoje and horario_fim_obj < hora_atual:
            messages.error(request, "Este horário já passou e não pode ser reservado!")
            return redirect(f"/Logar/?data={data_reserva_str}")

        # 2) Busca o equipamento (precisa existir antes de checar bloqueio/aprovação)
        equipamento_reserva = Equipamento.objects.get(id=request.POST.get('equipamento'))

        # 3) Checa se o carrinho está bloqueado nesse horário
        if BloqueioEquipamento.objects.filter(
            equipamento=equipamento_reserva,
            data=data_reservae,
            horario_inicio__lt=horario_fim_obj,
            horario_fim__gt=horario_inicio_obj,
        ).exists():
            messages.error(
                request,
                f"O carrinho '{equipamento_reserva.nome}' está indisponível para este horário no momento."
            )
            return redirect(f"/Logar/?data={data_reserva_str}")

        # 4) Só aceita horários de aula que realmente existem na grade da escola
        if not _horario_existe(horario_inicio_obj, horario_fim_obj):
            messages.error(
                request,
                f"O horário {horario_inicio}-{horario_fim} não existe na grade de aulas. "
                "Selecione um dos horários disponíveis no formulário."
            )
            return redirect(f"/Logar/?data={data_reserva_str}")

        # 5) Checa se o carrinho inteiro já está reservado nesse horário
        carrinho_inteiro_ocupado = Reserva.objects.filter(
            equipamento_id=request.POST.get('equipamento'),
            data_uso=data_reservae,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
            numero_notebook_unico__isnull=True,
            quantidade__isnull=True,
        ).exists()

        if carrinho_inteiro_ocupado:
            messages.error(
                request,
                f"O carrinho '{equipamento_reserva.nome}' já está reservado inteiro para este horário!"
            )
            return redirect(f"/Logar/?data={data_reserva_str}")

        # 6) Resolve quem é o professor da reserva
        professor_reserva = request.user
        if request.user.is_staff and request.POST.get('professor'):
            try:
                professor_reserva = User.objects.get(id=request.POST.get('professor'))
            except User.DoesNotExist:
                messages.error(request, "Erro: Professor não encontrado!")
                return redirect(f"/Logar/?data={data_reserva_str}")

        # 7) Define se precisa de aprovação (regra global + lista de liberados do carrinho)
        status_reserva = 'confirmada'
        if _requer_aprovacao_para_reserva(professor_reserva, equipamento_reserva):
            status_reserva = 'pendente'

        nova_reserva = Reserva.objects.create(
            professor=professor_reserva,
            equipamento=equipamento_reserva,
            sala=Sala.objects.get(id=request.POST.get('sala')),
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            data_uso=data_reservae,
            status=status_reserva,
        )

        if request.POST.get('aula_seguida') == 'sim':

            proximo = _proximo_horario(horario_inicio_obj)

            if proximo is None:
                messages.warning(
                    request,
                    f"Reserva feita! Atenção: não existe um próximo horário de aula depois "
                    f"de {horario_inicio}-{horario_fim}. Somente este horário foi reservado."
                )
            else:
                proximo_horario_inicio, proximo_horario_fim = proximo

                colisao = Reserva.objects.filter(
                    equipamento=nova_reserva.equipamento,
                    data_uso=data_reservae,
                    horario_inicio=proximo_horario_inicio,
                    status__in=['confirmada', 'pendente']
                ).first()

                bloqueio_proximo = BloqueioEquipamento.objects.filter(
                    equipamento=equipamento_reserva,
                    data=data_reservae,
                    horario_inicio__lt=proximo_horario_fim,
                    horario_fim__gt=proximo_horario_inicio,
                ).exists()

                if colisao:
                    messages.warning(
                        request,
                        f"Reserva feita! Atenção: O próximo horário ({proximo_horario_inicio.strftime('%H:%M')}–"
                        f"{proximo_horario_fim.strftime('%H:%M')}) está reservado pelo professor "
                        f"{colisao.professor.username}. Por favor, converse com ele."
                    )
                elif bloqueio_proximo:
                    messages.warning(
                        request,
                        f"Reserva feita! Atenção: O próximo horário ({proximo_horario_inicio.strftime('%H:%M')}–"
                        f"{proximo_horario_fim.strftime('%H:%M')}) está bloqueado. Somente este horário foi reservado."
                    )
                else:
                    Reserva.objects.create(
                        professor=professor_reserva,
                        equipamento=nova_reserva.equipamento,
                        sala=nova_reserva.sala,
                        horario_inicio=proximo_horario_inicio,
                        horario_fim=proximo_horario_fim,
                        data_uso=data_reservae,
                        status=status_reserva
                    )
                    messages.success(
                        request,
                        f"Reserva realizada para os dois horários com sucesso! "
                        f"({horario_inicio}–{horario_fim} e "
                        f"{proximo_horario_inicio.strftime('%H:%M')}–{proximo_horario_fim.strftime('%H:%M')})"
                    )
        else:
            messages.success(request, "Reserva realizada com sucesso!")

        return redirect(f"/Logar/?data={data_reserva_str}")
    filtro_reservas = {
        'data_uso': data_selecionada_obj,
        'status__in': ['confirmada', 'pendente'],
    }
    if data_selecionada_obj == hoje:
        filtro_reservas['horario_fim__gte'] = hora_atual

    reservas_hoje = Reserva.objects.filter(**filtro_reservas).order_by('horario_inicio')

    equipamentos = Equipamento.objects.all()

    reservas_com_fichas = Reserva.objects.filter(
        registrouso__isnull=False
    ).select_related(
        'professor', 'equipamento'
    ).prefetch_related(
        'registrouso_set__aluno__sala'
    ).distinct().order_by('-data_uso')

    reservas_pendentes = []
    if request.user.is_staff:
        reservas_pendentes = Reserva.objects.filter(
            status='pendente'
        ).select_related('professor', 'equipamento').order_by('data_criacao')

    tem_pin = False
    try:
        tem_pin = bool(request.user.perfil_adm.pin_envio)
    except PerfilAdm.DoesNotExist:
        tem_pin = False

    return render(request, 'mural.html', {
        'reservas': reservas_hoje,
        'equipamentos': equipamentos,
        'hoje': data_selecionada,
        'reservas_com_fichas': reservas_com_fichas,
        'reservas_pendentes': reservas_pendentes,
        'form': ReservaForm(),
        'tem_pin': tem_pin,
        'horarios': HorarioAula.objects.filter(ativo=True).order_by('periodo', 'numero'),
    })

def todos_horarios():
    """Lista (inicio, fim) de todos os horários ativos, na ordem, direto do banco."""
    return list(
        HorarioAula.objects.filter(ativo=True)
        .order_by('numero')
        .values_list('horario_inicio', 'horario_fim')
    )


@login_required
def excluir_reserva(request, reserva_id):
    # Exclui uma reserva (somente o professor dono da Reserva ou um staff pode excluir)
    data_param = request.GET.get('data')
    if not data_param:
        data_param = timezone.localtime(timezone.now()).date().strftime('%Y-%m-%d')

    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.user == reserva.professor or request.user.is_staff:
        reserva.delete()
        messages.success(request, "Reserva excluída com sucesso!")
    else:
        messages.error(request, "Você não tem permissão para excluir esta reserva.")

    query_string = urlencode({'data': data_param})
    return redirect(f"{reverse('mural')}?{query_string}")


@login_required
def numeros_disponiveis(request):
    # Retorna via AJAX os números de notebook livres de um carrinho específico num horário
    equipamento_id = request.GET.get('equipamento_id')
    data_sel = request.GET.get('data')
    horario_inicio_sel = request.GET.get('horario_inicio')
    horario_fim_sel = request.GET.get('horario_fim')

    try:
        equip = Equipamento.objects.get(id=equipamento_id)
        data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_sel, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_sel, '%H:%M').time()

        carrinho_inteiro_ocupado = Reserva.objects.filter(
            equipamento=equip,
            data_uso=data_sel_obj,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
            numero_notebook_unico__isnull=True,
        ).exists()

        if carrinho_inteiro_ocupado:
            return JsonResponse({'numeros': [], 'carrinho_indisponivel': True})

        numeros_reservados = set(Reserva.objects.filter(
            equipamento=equip,
            data_uso=data_sel_obj,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
            numero_notebook_unico__isnull=False,
        ).values_list('numero_notebook_unico', flat=True))

        inativos = set(
            Notebook.objects.filter(equipamento=equip, ativo=False).values_list('numero', flat=True)
        )

        numeros = [
            n for n in equip.lista_numeros()
            if n not in numeros_reservados and n not in inativos
        ]

        return JsonResponse({'numeros': numeros, 'carrinho_indisponivel': False})

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@login_required
def carregar_mural(request):
    # Retorna via AJAX o parcial HTML com a lista de reservas do dia.
    # Se 'inicio' e 'fim' vierem na query string (horário selecionado no formulário),
    # filtra só as reservas daquele período específico — é isso que faz as fichas
    # de outros horários sumirem do grid quando o professor escolhe um horário.
    data_sel = request.GET.get('data')
    inicio_sel = request.GET.get('inicio')
    fim_sel = request.GET.get('fim')

    if not data_sel:
        data_sel = date.today().strftime('%Y-%m-%d')
    data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date() if isinstance(data_sel, str) else data_sel

    agora_local = timezone.localtime(timezone.now())
    hora_atual = agora_local.time()
    hoje = agora_local.date()

    filtro = {
        'data_uso': data_sel_obj,
        'status__in': ['confirmada', 'pendente'],
    }

    if inicio_sel and fim_sel:
        # Horário específico selecionado: mostra só as fichas desse período
        try:
            filtro['horario_inicio'] = datetime.strptime(inicio_sel, '%H:%M').time()
            filtro['horario_fim'] = datetime.strptime(fim_sel, '%H:%M').time()
        except ValueError:
            pass  
    elif data_sel_obj == hoje:
        filtro['horario_fim__gte'] = hora_atual

    reservas = list(Reserva.objects.filter(**filtro).order_by('horario_inicio'))

    for r in reservas:
        r.mostrar_botao_numeracao = bool(
            r.quantidade and not r.numeracao_preenchida and hora_atual >= r.horario_inicio
        )

    return render(request, 'partials/lista_reservas.html', {
        'reservas': reservas,
        'user': request.user,
    })


def carregar_mural_publico(request):
    # Versão pública (sem login) do parcial de reservas do dia, só mostra confirmadas
    data_sel = request.GET.get('data')

    if not data_sel:
        data_sel = date.today().strftime('%Y-%m-%d')

    data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date() if isinstance(data_sel, str) else data_sel

    agora_local = timezone.localtime(timezone.now())
    hora_atual = agora_local.time()
    hoje = agora_local.date()

    if data_sel_obj == hoje:
        reservas = Reserva.objects.filter(
            data_uso=data_sel_obj,
            horario_fim__gte=hora_atual,
            status='confirmada'
        ).order_by('horario_inicio')
    else:
        reservas = Reserva.objects.filter(
            data_uso=data_sel_obj,
            status='confirmada'
        ).order_by('horario_inicio')

    return render(request, 'partials/lista_reservas_consulta.html', {'reservas': reservas})


def carrinho_principal(request):
    # Página pública de consulta do mural do dia atual
    hoje = date.today()
    hora_atual = timezone.localtime(timezone.now()).time()
    data_sel = date.today().strftime('%Y-%m-%d')
    data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date()

    reservas_hoje = Reserva.objects.filter(
        data_uso=data_sel_obj,
        horario_fim__gte=hora_atual,
        status='confirmada'
    ).order_by('horario_inicio')

    return render(request, 'mural_consulta.html', {
        'hoje': hoje.strftime('%d/%m/%Y'),
        'reservas': reservas_hoje
    })


@login_required
def atualizar_quantidade(request):
    # Permite a um staff atualizar a quantidade total de unidades de um equipamento
    if not request.user.is_staff:
        messages.error(request, "Sem permissão.")
        return redirect('mural')

    if request.method == "POST":
        equipamento_id = request.POST.get('equipamento_id')
        quantidade = request.POST.get('quantidade')
        try:
            equip = Equipamento.objects.get(id=equipamento_id)
            equip.quantidade = int(quantidade)
            equip.save()
            messages.success(request, f"Quantidade de '{equip.nome}' atualizada!")
        except Exception as e:
            messages.error(request, f"Erro: {e}")

    return redirect('mural')


def importar_de_excel(caminho_arquivo):
    # Importa alunos e salas em massa a partir de uma planilha Excel
    df = pd.read_excel(caminho_arquivo)
    for index, row in df.iterrows():
        sala_obj, _ = Sala.objects.get_or_create(nome=row['sala'])
        Aluno.objects.get_or_create(nome=row['nome'], sala=sala_obj)


# PIN de envio para tablet

@login_required
def criar_pin(request):
    # Professor cria/atualiza seu PIN de 4 dígitos usado para confirmar o envio da ficha no tablet
    if request.method == "POST":
        pin = request.POST.get('pin', '').strip()

        if not pin.isdigit() or len(pin) != 4:
            messages.error(request, "O PIN deve ter exatamente 4 dígitos numéricos.")
            return redirect('mural')

        perfil, created = PerfilAdm.objects.get_or_create(usuario=request.user)
        perfil.pin_envio = pin
        perfil.save()

        messages.success(request, "PIN de envio criado com sucesso!")
        return redirect('mural')

    return redirect('mural')


# Tablet / Fichas

MINIMO_ALUNOS_PADRAO = 5

LIMITES_CARRINHO = {
    1: (1, 40),
    2: (41, 80),
    3: (81, 120),
    4: (121, 160),
    5: (161, 200),
    6: (1, 20),
    7: (2, 111),
}


def notificar_erro_telegram(titulo: str, detalhes: str, equipamento_id, agora, extra: str = ""):
    """Centraliza o envio de alertas de erro para o Telegram."""
    try:
        enviar_telegram(
            f"🔴 <b>{titulo}</b>\n"
            f"Equipamento ID: {equipamento_id}\n"
            f"Horário: {agora.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Detalhes: {detalhes}\n"
            f"{extra}"
        )
    except Exception:
        # Se o próprio envio do Telegram falhar, não pode derrubar a view.
        logger.exception("Falha ao enviar notificação de erro pro Telegram")


def buscar_reserva_ativa(equipamento_id, agora):
    # Busca a reserva confirmada em andamento agora, para esse equipamento, ainda sem ficha preenchida
    return Reserva.objects.filter(
        equipamento_id=equipamento_id,
        status='confirmada',
        data_uso=agora.date(),
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time(),
        quantidade__isnull=True,
        numeracao_preenchida=False,
    ).first()


@login_required
def reportar_notebook_quebrado(request):
    # Marca UM OU VÁRIOS notebooks como inativos/quebrados. Aceita uma lista de
    # números separados por vírgula/espaço (além de envio repetido do campo).
    # Opcionalmente cria um pedido avulso (reserva por quantidade) para repor.
    if request.method != "POST":
        return JsonResponse({'sucesso': False, 'erro': 'Método inválido'}, status=405)


    numeros_texto = request.POST.get('numeros_notebook', '') or request.POST.get('numero_notebook', '')
    numeros_brutos = request.POST.getlist('numeros_notebook') or request.POST.getlist('numero_notebook')
    numeros_notebook = []
    for valor in [numeros_texto] + numeros_brutos:
        numeros_notebook.extend(re.findall(r'\d+', valor))


    numeros_notebook = list(dict.fromkeys(numeros_notebook))

    equipamento_id = request.POST.get('equipamento_id')
    carrinho_avulso_id = request.POST.get('carrinho_avulso_id')
    qtd_avulso = request.POST.get('quantidade_avulso')

    if not numeros_notebook:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Informe pelo menos um número de notebook.'
        }, status=400)

    try:
        equip = Equipamento.objects.get(id=equipamento_id)

        numeros_marcados = []
        for num_str in numeros_notebook:
            num_int = int(num_str)
            notebook, _ = Notebook.objects.get_or_create(
                equipamento=equip, numero=num_int, defaults={'ativo': False}
            )
            notebook.ativo = False
            notebook.save()
            numeros_marcados.append(num_int)

        enviar_telegram(
            f"🔧 <b>Notebook(s) Quebrado(s)</b>\n"
            f"Carrinho: {equip.nome}\n"
            f"Notebook(s): {', '.join(map(str, numeros_marcados))}\n"
            f"Professor: {request.user.username}"
        )

        mensagem = f"Notebook(s) {', '.join(map(str, numeros_marcados))} marcado(s) como quebrado(s)."

        if carrinho_avulso_id and qtd_avulso:
            try:
                qtd = int(qtd_avulso)
                if qtd <= 0:
                    raise ValueError("Quantidade inválida")

                sala = Sala.objects.get(id=request.POST.get('sala_id'))
                data_uso = datetime.strptime(request.POST.get('data_uso'), '%Y-%m-%d').date()
                horario_inicio = datetime.strptime(request.POST.get('horario_inicio'), '%H:%M').time()
                horario_fim = datetime.strptime(request.POST.get('horario_fim'), '%H:%M').time()

                equip_avulso = Equipamento.objects.get(id=carrinho_avulso_id)

                Reserva.objects.create(
                    professor=request.user,
                    equipamento=equip_avulso,
                    sala=sala,
                    horario_inicio=horario_inicio,
                    horario_fim=horario_fim,
                    data_uso=data_uso,
                    quantidade=qtd,
                    status='confirmada',
                )

                mensagem += f" Pedido de {qtd} unidade(s) do carrinho '{equip_avulso.nome}' realizado."
            except (Sala.DoesNotExist, Equipamento.DoesNotExist, ValueError, TypeError) as e:
                return JsonResponse({
                    'sucesso': False,
                    'erro': f"Falha ao criar pedido avulso: {e}",
                    'notebooks_marcados': numeros_marcados,
                }, status=400)

        return JsonResponse({
            'sucesso': True,
            'mensagem': mensagem,
            'notebooks_marcados': numeros_marcados,
        })

    except Exception as e:
        logger.exception("Erro ao reportar notebook")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)

def escolher_carrinho(request):
    """
    Não usa @login_required com redirect.
    Se o usuário não estiver logado, renderiza a MESMA página
    mostrando o modal de login (via AJAX).
    Se estiver logado, mostra a lista de equipamentos.
    """
    if request.user.is_authenticated:
        equipamentos = Equipamento.objects.all().order_by('nome')
        return render(request, 'escolher_carrinho.html', {
            'autenticado': True,
            'equipamentos': equipamentos,
        })
    else:
        return render(request, 'escolher_carrinho.html', {
            'autenticado': False,
            'equipamentos': None,
        })


@require_POST
@csrf_protect
def login_ajax(request):
    username = request.POST.get('username')
    password = request.POST.get('password')

    if not username or not password:
        return JsonResponse({'success': False, 'error': 'Preencha usuário e senha.'}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse(
            {'success': False, 'error': 'Usuário ou senha inválidos, ou conta não cadastrada.'},
            status=401
        )


@login_required
def view_tablet(request, equipamento_id):
    # Tela do tablet: no GET busca a reserva ativa, no POST valida e salva a ficha de uso dos alunos
    agora = timezone.localtime()
    if request.method == "POST":
        reserva_id = request.POST.get('reserva_id')


        try:
            if not reserva_id:
                raise ValueError("Campo reserva_id ausente no POST (formulário sem hidden input).")

            reserva = Reserva.objects.filter(
                id=reserva_id,
                equipamento_id=equipamento_id,
            ).first()

            if not reserva:
                raise ValueError(f"Nenhuma reserva encontrada com id={reserva_id} para equipamento_id={equipamento_id}.")

            if reserva.status != 'confirmada':
                raise ValueError(
                    f"Reserva {reserva.id} encontrada, mas está com status '{reserva.status}' "
                    f"(esperado 'confirmada'). Provável mudança de status entre a abertura da página e o envio."
                )
            if reserva.numeracao_preenchida:
                raise ValueError(
                    f"Reserva {reserva.id} já teve a ficha enviada anteriormente. "
                    f"Provável reenvio/duplo clique ou página recarregada após envio."
                )

        except ValueError as e:
            logger.warning(f"Falha ao localizar reserva no envio de ficha: {e}")
            notificar_erro_telegram(
                "ERRO NO ENVIO DE FICHA — Reserva não encontrada",
                str(e),
                equipamento_id,
                agora,
            )
            messages.error(
                request,
                "Não foi possível confirmar sua reserva no momento do envio. "
                "Isso pode acontecer se a página ficou aberta por muito tempo, "
                "ou se a ficha já foi enviada antes. "
                "Recarregue a página e tente novamente. A coordenação já foi avisada."
            )
            return redirect('tablet_checkin', equipamento_id=equipamento_id)

        sala = reserva.sala
        alunos = Aluno.objects.filter(sala=sala)
        minimo_alunos = MINIMO_ALUNOS_PADRAO
        carrinho_id = reserva.equipamento.id

        contexto_erro = {
            'reserva': reserva,
            'alunos': alunos,
            'dados_anteriores': request.POST,
            'minimo_alunos': minimo_alunos,
        }

        try:
            numeros_usados = {}
            erros = False
            limites = LIMITES_CARRINHO.get(carrinho_id)

            for aluno in alunos:
                numero_str = request.POST.get(f'aluno_{aluno.id}')
                if not numero_str:
                    continue

                if not numero_str.strip().isdigit():
                    messages.error(request, f"Erro: {aluno.nome} tem um valor inválido ('{numero_str}').")
                    erros = True
                    continue

                num = int(numero_str)

                if limites:
                    minimo, maximo = limites
                    if num < minimo or num > maximo:
                        messages.error(
                            request,
                            f"Erro: {aluno.nome} colocou {num}, mas só tem notebooks de {minimo} a {maximo}."
                        )
                        erros = True

                if num in numeros_usados:
                    messages.error(
                        request,
                        f"Erro: {aluno.nome} e {numeros_usados[num]} colocaram o mesmo número ({num})!"
                    )
                    erros = True
                else:
                    numeros_usados[num] = aluno.nome

            if erros:
                return render(request, 'tablet_checkin.html', contexto_erro)

        except Exception as e:
            logger.exception("Erro inesperado ao processar envio de ficha")
            notificar_erro_telegram(
                "ERRO CRÍTICO NO ENVIO DE FICHA",
                f"{type(e).__name__}: {e}",
                equipamento_id,
                agora,
                extra=f"Professor: {reserva.professor.username if reserva else 'desconhecido'}",
            )
            messages.error(
                request,
                "Ocorreu um erro inesperado ao processar sua ficha. "
                "A coordenação já foi avisada automaticamente. Tente novamente em instantes."
            )
            return render(request, 'tablet_checkin.html', contexto_erro)

        pin_digitado = request.POST.get('pin_envio', '').strip()
        professor = reserva.professor

        try:
            pin_correto = professor.perfil_adm.pin_envio
        except PerfilAdm.DoesNotExist:
            pin_correto = None

        if not pin_correto:
            messages.error(request, "Professor não possui PIN cadastrado. Crie um PIN no mural primeiro.")
            return render(request, 'tablet_checkin.html', contexto_erro)

        if not pin_digitado or pin_digitado != pin_correto:
            messages.error(request, "PIN inválido! Digite o PIN de 4 dígitos correto.")
            return render(request, 'tablet_checkin.html', contexto_erro)

    
        registros = []
        for aluno in alunos:
            numero_str = request.POST.get(f'aluno_{aluno.id}')
            if numero_str and numero_str.strip().isdigit():
                registros.append(
                    RegistroUso(
                        reserva=reserva,
                        aluno=aluno,
                        numero_notebook=int(numero_str)
                    )
                )

        RegistroUso.objects.filter(reserva=reserva).delete()
        RegistroUso.objects.bulk_create(registros)

        reserva.numeracao_preenchida = True
        reserva.save(update_fields=['numeracao_preenchida'])

        return render(request, 'enviado.html', {
            'id': equipamento_id,
            'reserva_id': reserva.id,
            'professor_id': reserva.professor_id,
            'carrinho_id': carrinho_id,
            'sala': sala.id,
        })


    reserva = buscar_reserva_ativa(equipamento_id, agora)

    if not reserva:
        return render(request, 'tablet_sem_reserva.html', {
            'equipamento_id': equipamento_id,
            'agora': agora,
        })

    sala = reserva.sala
    alunos = Aluno.objects.filter(sala=sala)


    equipamentos_geral = Equipamento.objects.all()

    return render(request, 'tablet_checkin.html', {
        'reserva': reserva,
        'alunos': alunos,
        'minimo_alunos': MINIMO_ALUNOS_PADRAO,
        'equipamentos_geral': equipamentos_geral,
    })


@login_required
def status_tablet(request, equipamento_id):
    # Endpoint de polling: informa ao tablet se já existe uma nova reserva diferente da atual
    agora = timezone.localtime()

    nova_reserva = Reserva.objects.filter(
        equipamento_id=equipamento_id,
        status__in=['confirmada', 'pendente'],
        data_uso=agora.date(),
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time(),
        quantidade__isnull=True,
        numeracao_preenchida=False,
    ).exclude(id=request.GET.get('reserva_atual')).exists()

    if not nova_reserva:
        return render(request, 'tablet_sem_reserva.html', {
            'equipamento_id': equipamento_id,
            'agora': agora,
        })

    return JsonResponse({'nova_reserva': nova_reserva})


@login_required
def camera_contagem(request):
    return render(request, 'camera.html')

# Página do formulário de reserva por quantidade (sem bloquear o carrinho inteiro)

@login_required
def pagina_unico(request):
    equipamentos = Equipamento.objects.all()
    form = ReservaForm()

    context = {
        'hoje': timezone.now().date().strftime('%Y-%m-%d'),
        'equipamentos': equipamentos,
        'form': form,
        'horarios': HorarioAula.objects.filter(ativo=True).order_by('periodo', 'numero'),
    }

    return render(request, "unico.html", context)


@login_required
def reserva_quantidade(request):
    if request.method != "POST":
        return redirect('unico')

    agora = timezone.localtime()
    hoje = agora.date()
    hora_atual = agora.time()

    data_reserva_str = request.POST.get('data')
    horario_inicio_str = request.POST.get('horario_inicio')
    horario_fim_str = request.POST.get('horario_fim')
    equipamento_id = request.POST.get('equipamento')
    quantidade_raw = request.POST.get('quantidade', '').strip()

    if not all([data_reserva_str, horario_inicio_str, horario_fim_str]):
        messages.error(request, "Por favor, preencha a data e selecione um horário!")
        return redirect('unico')

    try:
        data_reservae = datetime.strptime(data_reserva_str, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_str, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_str, '%H:%M').time()
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro de conversão em reserva_quantidade: {e}")
        messages.error(request, f"Formato de data ou hora inválido! Recebido: {data_reserva_str}, {horario_inicio_str}")
        return redirect('unico')

    if not quantidade_raw.isdigit() or int(quantidade_raw) <= 0:
        messages.error(request, "Quantidade inválida!")
        return redirect(f"/Logar/?data={data_reserva_str}")

    quantidade_solicitada = int(quantidade_raw)

    try:
        sala_obj = Sala.objects.get(id=request.POST.get('sala'))
    except Sala.DoesNotExist:
        messages.error(request, "Sala não encontrada!")
        return redirect('unico')

    professor_reserva = request.user
    professor_id = request.user.id

    if data_reservae < hoje:
        messages.error(
            request,
            f"⚠️ Não é possível reservar para o dia {data_reservae.strftime('%d/%m/%Y')}, "
            f"pois hoje é {hoje.strftime('%d/%m/%Y')}. Selecione uma data a partir de hoje."
        )
        return redirect('unico')

    if data_reservae == hoje and horario_fim_obj < hora_atual:
        messages.error(request, "Este horário já passou e não pode ser reservado!")
        return redirect(f"/Logar/?data={data_reserva_str}")

    if request.user.is_staff and request.POST.get('professor'):
        professor_id = request.POST.get('professor')
        try:
            professor_reserva = User.objects.get(id=professor_id)
        except User.DoesNotExist:
            messages.error(request, "Erro: Professor não encontrado!")
            return redirect('unico')

    try:
        equip_obj = Equipamento.objects.get(id=equipamento_id)
    except Equipamento.DoesNotExist:
        messages.error(request, "Equipamento não encontrado!")
        return redirect('unico')

    # Bloqueia só se o carrinho JÁ estiver reservado inteiro (reserva antiga, quantidade=None)
    carrinho_inteiro_ocupado = Reserva.objects.filter(
        equipamento=equip_obj,
        data_uso=data_reservae,
        horario_inicio=horario_inicio_obj,
        horario_fim=horario_fim_obj,
        status__in=['confirmada', 'pendente'],
        quantidade__isnull=True,
    ).exists()

    if carrinho_inteiro_ocupado:
        messages.error(request, f"O carrinho '{equip_obj.nome}' já está reservado inteiro para este horário!")
        return redirect(f"/Logar/?data={data_reserva_str}")

    total_reservado = Reserva.objects.filter(
        equipamento=equip_obj,
        data_uso=data_reservae,
        horario_inicio=horario_inicio_obj,
        horario_fim=horario_fim_obj,
        status__in=['confirmada', 'pendente'],
        quantidade__isnull=False,
    ).aggregate(total=Sum('quantidade'))['total'] or 0

    disponivel = equip_obj.quantidade - total_reservado

    if quantidade_solicitada > disponivel:
        messages.error(
            request,
            f"Só há {disponivel} unidade(s) disponível(is) de '{equip_obj.nome}' nesse horário!"
        )
        return redirect("unico")
    tem_numeracao = bool(equip_obj.numero_inicial and equip_obj.numero_final)
    numeros_escolhidos = []

    if tem_numeracao:
        numeros_raw = [n.strip() for n in request.POST.getlist('numero') if n.strip()]

        if len(numeros_raw) != quantidade_solicitada:
            messages.error(
                request,
                f"Você pediu {quantidade_solicitada} unidade(s), mas informou {len(numeros_raw)} número(s) de notebook."
            )
            return redirect('unico')

        try:
            numeros_escolhidos = [int(n) for n in numeros_raw]
        except ValueError:
            messages.error(request, "Todos os números de notebook precisam ser válidos.")
            return redirect('unico')

        if len(set(numeros_escolhidos)) != len(numeros_escolhidos):
            messages.error(request, "Você selecionou números de notebook repetidos.")
            return redirect('unico')

        faixa = equip_obj.faixa_numeros()
        fora_da_faixa = [n for n in numeros_escolhidos if n not in faixa]
        if fora_da_faixa:
            messages.error(request, f"Os números {fora_da_faixa} não pertencem ao carrinho '{equip_obj.nome}'.")
            return redirect('unico')

        inativos = set(
            Notebook.objects.filter(equipamento=equip_obj, numero__in=numeros_escolhidos, ativo=False)
            .values_list('numero', flat=True)
        )
        if inativos:
            messages.error(request, f"Os notebooks {sorted(inativos)} estão marcados como quebrados.")
            return redirect('unico')

        ja_usados = set(
            NumeroReservaQuantidade.objects.filter(
                reserva__equipamento=equip_obj,
                reserva__data_uso=data_reservae,
                reserva__horario_inicio=horario_inicio_obj,
                reserva__horario_fim=horario_fim_obj,
                reserva__status__in=['confirmada', 'pendente'],
                numero__in=numeros_escolhidos,
            ).values_list('numero', flat=True)
        )
        if ja_usados:
            messages.error(
                request,
                f"Os notebooks {sorted(ja_usados)} já foram informados em outra reserva deste horário."
            )
            return redirect('unico')

    status_reserva = 'confirmada'
    if _professor_requer_aprovacao(professor_reserva):
        status_reserva = 'pendente'

    nova_reserva = Reserva.objects.create(
        professor=professor_reserva,
        equipamento=equip_obj,
        sala=sala_obj,
        horario_inicio=horario_inicio_obj,
        horario_fim=horario_fim_obj,
        data_uso=data_reservae,
        status=status_reserva,
        quantidade=quantidade_solicitada,
    )

    if numeros_escolhidos:
        NumeroReservaQuantidade.objects.bulk_create([
            NumeroReservaQuantidade(reserva=nova_reserva, numero=n) for n in numeros_escolhidos
        ])
        nova_reserva.numeracao_preenchida = True
        nova_reserva.save(update_fields=['numeracao_preenchida'])

    if status_reserva == 'pendente':
        messages.warning(
            request,
            f"Reserva de {quantidade_solicitada} unidade(s) enviada! Aguardando aprovação de um administrador."
        )
        enviar_telegram(
            f"📥 <b>Nova reserva pendente</b>\n"
            f"Professor: {professor_reserva.get_full_name() or professor_reserva.username}\n"
            f"Data: {data_reservae.strftime('%d/%m/%Y')}\n"
            f"Horário: {horario_inicio_obj.strftime('%H:%M')} - {horario_fim_obj.strftime('%H:%M')}\n"
            f"Equipamento: {equip_obj.nome}\n"
            f"Sala: {sala_obj.nome}\n"
            f"Quantidade: {quantidade_solicitada} unidade(s)"
            + (f"\nNúmeros: {', '.join(map(str, numeros_escolhidos))}" if numeros_escolhidos else "")
        )
    else:
        messages.success(
            request,
            f"Reserva de {quantidade_solicitada} unidade(s) realizada com sucesso para {professor_reserva.username}!"
        )
        enviar_telegram(
            f"📥 <b>RESERVA UNICA</b>\n"
            f"Professor: {professor_reserva.get_full_name() or professor_reserva.username}\n"
            f"Data: {data_reservae.strftime('%d/%m/%Y')}\n"
            f"Horário: {horario_inicio_obj.strftime('%H:%M')} - {horario_fim_obj.strftime('%H:%M')}\n"
            f"Equipamento: {equip_obj.nome}\n"
            f"Sala: {sala_obj.nome}\n"
            f"Quantidade: {quantidade_solicitada} unidade(s)"
            + (f"\nNúmeros: {', '.join(map(str, numeros_escolhidos))}" if numeros_escolhidos else "")
        )

    if tem_numeracao:
        return redirect(f"/Logar/?data={data_reserva_str}")
    else:
        return redirect('preencher_numeracao_quantidade', reserva_id=nova_reserva.id)

@login_required
def preencher_numeracao_quantidade(request, reserva_id):
    # Após reservar por quantidade, professor informa quais números de notebook específicos usará
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.user != reserva.professor and not request.user.is_staff:
        messages.error(request, "Você não tem permissão para preencher esta numeração.")
        return redirect('mural')

    if reserva.quantidade is None:
        messages.error(request, "Esta reserva não é do tipo quantidade específica.")
        return redirect('mural')

    equip = reserva.equipamento

    if request.method == "POST":
        numeros_raw = [n.strip() for n in request.POST.getlist('numero') if n.strip()]

        if len(numeros_raw) != reserva.quantidade:
            messages.error(
                request,
                f"Você reservou {reserva.quantidade} unidade(s). Preencha exatamente {reserva.quantidade} número(s)."
            )
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        try:
            numeros = [int(n) for n in numeros_raw]
        except ValueError:
            messages.error(request, "Todos os números precisam ser válidos.")
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        if len(set(numeros)) != len(numeros):
            messages.error(request, "Você digitou números repetidos.")
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        faixa = equip.faixa_numeros()
        fora_da_faixa = [n for n in numeros if n not in faixa]
        if fora_da_faixa:
            messages.error(request, f"Os números {fora_da_faixa} não pertencem ao carrinho '{equip.nome}'.")
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        inativos = set(
            Notebook.objects.filter(equipamento=equip, numero__in=numeros, ativo=False)
            .values_list('numero', flat=True)
        )
        if inativos:
            messages.error(request, f"Os notebooks {sorted(inativos)} estão marcados como quebrados.")
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        ja_usados = set(
            NumeroReservaQuantidade.objects.filter(
                reserva__equipamento=equip,
                reserva__data_uso=reserva.data_uso,
                reserva__horario_inicio=reserva.horario_inicio,
                reserva__horario_fim=reserva.horario_fim,
                reserva__status__in=['confirmada', 'pendente'],
                numero__in=numeros,
            ).exclude(reserva=reserva).values_list('numero', flat=True)
        )
        if ja_usados:
            messages.error(
                request,
                f"Os notebooks {sorted(ja_usados)} já foram informados em outra reserva deste horário."
            )
            return redirect('preencher_numeracao_quantidade', reserva_id=reserva.id)

        NumeroReservaQuantidade.objects.filter(reserva=reserva).delete()
        NumeroReservaQuantidade.objects.bulk_create([
            NumeroReservaQuantidade(reserva=reserva, numero=n) for n in numeros
        ])
        reserva.numeracao_preenchida = True
        reserva.save(update_fields=['numeracao_preenchida'])

        messages.success(request, "Numeração salva com sucesso!")
        return redirect(f"/Logar/?data={reserva.data_uso.strftime('%Y-%m-%d')}")

    numeros_atuais = list(reserva.numeros_quantidade.values_list('numero', flat=True))

    return render(request, 'preencher_numeracao.html', {
        'reserva': reserva,
        'numeros_atuais': numeros_atuais,
        'range_quantidade': range(reserva.quantidade),
    })
