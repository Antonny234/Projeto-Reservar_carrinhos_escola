from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import date, datetime
from django.db.models import Sum

from ..models import (
    Aluno, NumeroReservaQuantidade, RegistroUso, Reserva, Equipamento, Sala, Notebook, PerfilAdm
)
from ..forms import ReservaForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
import pandas as pd
import re

# Helper
from .helpers import _professor_requer_aprovacao


def home(request):
    return render(request, 'longa.html')


def CriarConta(request):
    if request.method == "POST":
        usuario = request.POST.get('usuario')
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        confirmar = request.POST.get('confirmar_senha')

        dominio_permitido = "@professor.educacao.sp.gov.br"

        if not email.lower().endswith(dominio_permitido):
            messages.error(request, "Erro: Apenas e-mails corporativo SEDUC!")
            return render(request, 'index.html')

        if senha != confirmar:
            messages.error(request, "As senhas não coincidem!")
            return render(request, 'index.html')

        if User.objects.filter(username=usuario).exists():
            messages.error(request, "Este nome de usuário já está em uso.")
            return render(request, 'index.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Este email esta em uso.")
            return render(request, 'index.html')

        user = User.objects.create_user(username=usuario, email=email, password=senha)
        user.save()

        messages.success(request, "Conta criada com sucesso! Faça login.")
        return render(request, 'longa.html')

    return render(request, 'index.html')


def Entrar(request):
    if request.method == "POST":
        usuario_digitado = request.POST.get('usuario')
        senha_digitada = request.POST.get('senha')

        usuario_existe = User.objects.filter(username=usuario_digitado).exists()

        if not usuario_existe:
            messages.error(request, "Usuário não encontrado!")
            return render(request, 'longa.html')

        user = authenticate(request, username=usuario_digitado, password=senha_digitada)

        if user is None:
            messages.error(request, "Senha incorreta!")
            return render(request, 'longa.html')

        login(request, user)
        return redirect('mural')

    return render(request, 'longa.html')


# Mural / Reservas


@login_required
def mural(request):
    agora = timezone.localtime(timezone.now())
    hoje = agora.date()
    hora_atual = agora.time()

    data_param = request.GET.get('data')
    data_selecionada = data_param if data_param else hoje.strftime('%Y-%m-%d')
    if request.method == "POST":
        data_reserva_str = request.POST.get('data')
        horario_inicio_str = request.POST.get('horario_inicio')
        data_reservae = datetime.strptime(data_reserva_str, '%Y-%m-%d').date()
        horario_inicio = datetime.strptime(horario_inicio_str, '%H:%M').time()
        equipamento_id = request.POST.get('equipamento')
        try:
            sala_obj = Sala.objects.get(id=request.POST.get('sala'))
        except Sala.DoesNotExist:
            messages.error(request, "Sala não encontrada!")
            return redirect('mural')
        horario_inicio = request.POST.get('horario_inicio')
        horario_fim = request.POST.get('horario_fim')
        data_reserva = request.POST.get('data')
        horario_inicio_obj = datetime.strptime(horario_inicio, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim, '%H:%M').time()

        professor_reserva = request.user
        professor_id = request.user.id

        if data_reservae == hoje and horario_fim_obj < hora_atual:
            messages.error(request, "Este horário já passou e não pode ser reservado!")
            return redirect('/Logar/?data={data_reserva}')

        if request.user.is_staff and request.POST.get('professor'):
            professor_id = request.POST.get('professor')
            try:
                professor_reserva = User.objects.get(id=professor_id)
            except User.DoesNotExist:
                messages.error(request, f"Erro: Professor não encontrado!")
                return redirect('mural')

        try:
            equip_obj = Equipamento.objects.get(id=equipamento_id)
        except Equipamento.DoesNotExist:
            messages.error(request, "Equipamento não encontrado!")
            return redirect('mural')

        dupla_reserva = Reserva.objects.filter(
            professor_id=professor_id,
            sala=sala_obj,
            data_uso=data_reservae,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
        ).exists()

        # Soma tudo que já está reservado nesse carrinho/horário:
        # - reservas com quantidade definida (reserva única) somam o valor exato
        # - reservas de carrinho inteiro (quantidade=None) consomem a capacidade toda
        reservas_existentes = Reserva.objects.filter(
            equipamento_id=equipamento_id,
            data_uso=data_reservae,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
        )

        total_reservado = 0
        for r in reservas_existentes:
            if r.quantidade is not None:
                total_reservado += r.quantidade
            else:
                total_reservado += equip_obj.quantidade

        ja_reservado = total_reservado >= equip_obj.quantidade

        if ja_reservado:
            messages.error(request, "Este carrinho já foi reservado para este horário!")
        elif dupla_reserva:
            messages.error(request, "Você ja tem uma reserva nesse horario e para essa turma!")
            return redirect("mural")
        else:
            try:
                status_reserva = 'confirmada'
                if _professor_requer_aprovacao(professor_reserva):
                    status_reserva = 'pendente'

                Reserva.objects.create(
                    professor=professor_reserva,
                    equipamento=equip_obj,
                    sala=sala_obj,
                    horario_inicio=horario_inicio_obj,
                    horario_fim=horario_fim_obj,
                    data_uso=data_reservae,
                    status=status_reserva,
                )

                if status_reserva == 'pendente':
                    messages.warning(
                        request,
                        "Reserva enviada! Aguardando aprovação de um administrador."
                    )
                else:
                    messages.success(request, f"Reserva realizada com sucesso para {professor_reserva.username}!")
            except Exception as e:
                messages.error(request, f"Erro ao salvar: {e}")

        return redirect(f"/Logar/?data={data_reserva}")

    reservas_hoje = Reserva.objects.filter(
        data_uso=hoje,
        horario_fim__gte=hora_atual,
        status__in=['confirmada', 'pendente']
    ).order_by('horario_inicio')

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
    })



@login_required
def excluir_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.user == reserva.professor or request.user.is_staff:
        reserva.delete()
        messages.success(request, "Reserva excluída com sucesso!")
        

    return redirect('mural')

@login_required
def listar_disponiveis(request):
    data_sel = request.GET.get('data')
    horario_inicio_sel = request.GET.get('horario_inicio')
    horario_fim_sel = request.GET.get('horario_fim')

    try:
        data_sel_obj = datetime.strptime(data_sel, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_sel, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_sel, '%H:%M').time()

        # Carrinhos reservados INTEIROS (bloqueiam totalmente)
        ocupados_inteiro = Reserva.objects.filter(
            data_uso=data_sel_obj,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
            numero_notebook_unico__isnull=True,
            quantidade__isnull=True,
        ).values_list('equipamento_id', flat=True)

        disponiveis = Equipamento.objects.exclude(id__in=ocupados_inteiro)

        # Soma das quantidades já reservadas via unico.html, por carrinho, nesse horário
        reservas_quantidade = Reserva.objects.filter(
            data_uso=data_sel_obj,
            horario_inicio=horario_inicio_obj,
            horario_fim=horario_fim_obj,
            status__in=['confirmada', 'pendente'],
            quantidade__isnull=False,
        ).values('equipamento_id').annotate(total=Sum('quantidade'))

        reservado_por_equip = {r['equipamento_id']: r['total'] for r in reservas_quantidade}

        data = []
        for e in disponiveis:
            reservado = reservado_por_equip.get(e.id, 0)
            qtd_disponivel = max(e.quantidade - reservado, 0)
            data.append({
                'id': e.id,
                'nome': e.nome,
                'quantidade': qtd_disponivel,
                'tem_numeracao': bool(e.numero_inicial and e.numero_final),
            })

        return JsonResponse({'equipamentos': data})

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
    
@login_required
def numeros_disponiveis(request):
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
            status__in=['confirmada', 'pendente']
        ).order_by('horario_inicio')
    else:
        reservas = Reserva.objects.filter(
            data_uso=data_sel_obj,
            status__in=['confirmada', 'pendente']
        ).order_by('horario_inicio')

    reservas = list(reservas)
    for r in reservas:
        r.mostrar_botao_numeracao = bool(
            r.quantidade and not r.numeracao_preenchida and hora_atual >= r.horario_inicio
        )

    return render(request, 'partials/lista_reservas.html', {
        'reservas': reservas,
        'user': request.user,
    })


def carregar_mural_publico(request):
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

    return render(request, 'partials/lista_reservas_consulta.html', {'reservas': reservas,})


def carrinho_principal(request):
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
    df = pd.read_excel(caminho_arquivo)
    for index, row in df.iterrows():
        Sala, _ = Sala.objects.get_or_create(nome=row['sala'])
        Aluno.objects.get_or_create(nome=row['nome'], sala = Sala)


# PIN de envio para tablet


@login_required
def criar_pin(request):
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


def view_tablet(request, equipamento_id):
    agora = timezone.localtime()

    reserva = Reserva.objects.filter(
        equipamento_id=equipamento_id,
        status='confirmada',
        data_uso=agora.date(),
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time(),
        quantidade__isnull=True,
    ).first()

    if not reserva:
        return HttpResponse("Nenhuma reserva ativa para este carrinho agora.")

    sala = reserva.sala
    alunos = Aluno.objects.filter(sala=sala)

    if request.method == "POST":
        # Validar PIN de envio
        pin_digitado = request.POST.get('pin_envio', '').strip()
        professor = reserva.professor

        try:
            pin_correto = professor.perfil_adm.pin_envio
        except PerfilAdm.DoesNotExist:
            pin_correto = None

        if not pin_correto:
            messages.error(request, "Professor não possui PIN cadastrado. Crie um PIN no mural primeiro.")
            return render(request, 'tablet_checkin.html', {'reserva': reserva, 'alunos': alunos, 'dados_anteriores': request.POST})

        if not pin_digitado or pin_digitado != pin_correto:
            messages.error(request, "PIN inválido! Digite o PIN de 4 dígitos correto.")
            return render(request, 'tablet_checkin.html', {'reserva': reserva, 'alunos': alunos, 'dados_anteriores': request.POST})

        numeros_usados = {}
        erros = False
        carrinho_id = reserva.equipamento.id  

        for aluno in alunos:
            numero_str = request.POST.get(f'aluno_{aluno.id}')
            if numero_str:
                num = int(numero_str)

                #regra de validação para mandar as fichas
                if carrinho_id == 1 and num > 40:
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} , mais so tem notebooks de 1 a 40.")
                    erros = True
                elif carrinho_id == 10 and (num < 41 or num >80 ):
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} mais so tem notebooks de 41 a 80.")
                    erros = True
                elif carrinho_id == 11 and (num < 81 or num > 120):
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} mais so tem notebooks de 81 a 120.")
                    erros = True
                elif carrinho_id == 12 and (num < 121 or num > 160):
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} mais so tem notebooks de 121 a 160.")
                    erros = True
                elif carrinho_id == 13 and (num < 161 or num > 200):
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} mais so tem notebooks de 161 a 200.")
                    erros = True
                elif carrinho_id == 14 and (num < 201 or num > 240):
                    messages.error(request, f"Erro: {aluno.nome} colocou {num} mais so tem notebooks de 201 a 240.")
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
            return render(request, 'tablet_checkin.html', {'reserva': reserva, 'alunos': alunos, 'dados_anteriores': request.POST})

      
        for aluno in alunos:
            numero = request.POST.get(f'aluno_{aluno.id}')
            if numero:
                RegistroUso.objects.update_or_create(
                    reserva=reserva, aluno=aluno,
                    defaults={'numero_notebook': numero}
                )

        return render(request, 'enviado.html', {
            'id': equipamento_id,
            'reserva_id': reserva.id,
            'professor_id': reserva.professor_id,
            'carrinho_id': carrinho_id,
            'sala': sala.id,
        })

    return render(request, 'tablet_checkin.html', {'reserva': reserva, 'alunos': alunos})

@login_required
def status_tablet(request, equipamento_id):
    agora = timezone.localtime()

    nova_reserva = Reserva.objects.filter(
        equipamento_id=equipamento_id,
        status__in=['confirmada','pendente'],
        data_uso=agora.date(),
        horario_inicio__lte=agora.time(),
        horario_fim__gte=agora.time(),
        quantidade__isnull=True,
    ).exclude(id=request.GET.get('reserva_atual')).exists()

    return JsonResponse({'nova_reserva': nova_reserva})


@login_required
def camera_contagem(request):
    return render(request, 'camera.html')

@login_required
def pagina_unico(request):
    # Pega todos os equipamentos para listar no select do formulário
    equipamentos = Equipamento.objects.all()
    
    # Cria uma instância do formulário vazio
    form = ReservaForm()  # Isso vai carregar todas as salas automaticamente
    
    context = {
        'hoje': timezone.now().date().strftime('%Y-%m-%d'),
        'equipamentos': equipamentos,
        'form': form,  # Adicione o formulário ao contexto
    }
    
    return render(request, "unico.html", context)


@login_required
def reserva_quantidade(request):
    """Segunda forma de reserva: reservar apenas X unidades de um carrinho.
    Não bloqueia o carrinho inteiro — só soma com outras reservas por quantidade
    até atingir o total do equipamento."""
    agora = timezone.localtime()
    hoje = agora.date()
    hora_atual = agora.time()
    data_reserva_str = request.POST.get('data')
    horario_inicio_str = request.POST.get('horario_inicio')
    horario_fim_str = request.POST.get('horario_fim')

    # Validação rápida: se algum estiver vazio, nem tente converter
    if not all([data_reserva_str, horario_inicio_str, horario_fim_str]):
        messages.error(request, "Por favor, preencha a data e selecione um horário!")
        return redirect('unico')

    try:
        data_reservae = datetime.strptime(data_reserva_str, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_str, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_str, '%H:%M').time()
    except ValueError as e:
        # Se cair aqui, o formato está errado
        print(f"Erro de conversão: {e}") 
        messages.error(request, f"Formato de data ou hora inválido! Recebido: {data_reserva_str}, {horario_inicio_str}")
        return redirect('unico')

    if request.method != "POST":
        return redirect('unico')

    data_reserva_str = request.POST.get('data')
    horario_inicio_str = request.POST.get('horario_inicio')
    horario_fim_str = request.POST.get('horario_fim')
    equipamento_id = request.POST.get('equipamento')
    quantidade_raw = request.POST.get('quantidade', '').strip()

    try:
        data_reservae = datetime.strptime(data_reserva_str, '%Y-%m-%d').date()
        horario_inicio_obj = datetime.strptime(horario_inicio_str, '%H:%M').time()
        horario_fim_obj = datetime.strptime(horario_fim_str, '%H:%M').time()
    except (ValueError, TypeError):
        messages.error(request, "Data ou horário inválido!")
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

    if data_reservae == hoje and horario_fim_obj < hora_atual:
        messages.error(request, "Este horário já passou e não pode ser reservado!")
        return redirect(f"/Logar/?data={data_reserva_str}")

    if request.user.is_staff and request.POST.get('professor'):
        professor_id = request.POST.get('professor')
        try:
            professor_reserva = User.objects.get(id=professor_id)
        except User.DoesNotExist:
            messages.error(request, "Erro: Professor não encontrado!")
            return redirect('mural')

    equip_obj = Equipamento.objects.get(id=equipamento_id)

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

    if status_reserva == 'pendente':
        messages.warning(
            request,
            f"Reserva de {quantidade_solicitada} unidade(s) enviada! Aguardando aprovação de um administrador."
        )
    else:
        messages.success(
            request,
            f"Reserva de {quantidade_solicitada} unidade(s) realizada com sucesso para {professor_reserva.username}!"
        )

    return redirect('preencher_numeracao_quantidade', reserva_id=nova_reserva.id)
@login_required
def preencher_numeracao_quantidade(request, reserva_id):
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
