from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError

from ..models import (Aluno, Equipamento, HorarioAula, EquipamentoLiberado, BloqueioEquipamento, Sala)
from ..forms import EquipamentoForm, HorarioAulaForm, EquipamentoLiberacaoForm, BloqueioEquipamentoForm
from ..decorators import admin_escola_required
from django.utils import timezone
from ..utils import obter_escola_ativa
import os
import re
import unicodedata
import pandas as pd


def _normalizar_coluna(valor):
    valor = unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', valor).strip().casefold()


def _dados_cadastros(escola, **extras):
    dados = {
        'equipamentos': Equipamento.objects.filter(escola=escola).order_by('nome'),
        'horarios': HorarioAula.objects.filter(escola=escola).order_by('numero'),
        'salas': Sala.objects.filter(escola=escola).order_by('nome'),
        'total_alunos': Aluno.objects.filter(sala__escola=escola).count(),
        'form_equipamento': EquipamentoForm(),
        'form_horario': HorarioAulaForm(),
    }
    dados.update(extras)
    return dados


def _linhas_do_arquivo(arquivo):
    extensao = os.path.splitext(arquivo.name)[1].casefold()
    if extensao in {'.xlsx', '.xls', '.csv'}:
        if extensao == '.csv':
            tabela = pd.read_csv(arquivo)
        else:
            tabela = pd.read_excel(arquivo)
        return tabela.fillna('').values.tolist(), tabela.columns.tolist()
    if extensao == '.pdf':
        import pdfplumber
        linhas = []
        with pdfplumber.open(arquivo) as pdf:
            for pagina in pdf.pages:
                for tabela in pagina.extract_tables() or []:
                    linhas.extend(tabela)
        if not linhas:
            raise ValidationError('Não foi encontrada uma tabela no PDF. Use um PDF com texto/tabela selecionável ou importe Excel.')
        return linhas[1:], linhas[0]
    raise ValidationError('Formato inválido. Envie um arquivo Excel (.xlsx, .xls, .csv) ou PDF.')


def _validar_planilha_alunos(arquivo, escola):
    linhas, cabecalhos = _linhas_do_arquivo(arquivo)
    mapa = {_normalizar_coluna(coluna): indice for indice, coluna in enumerate(cabecalhos)}
    indice_nome = next((indice for chave, indice in mapa.items() if chave in {'aluno', 'nome', 'nome do aluno'}), None)
    indice_sala = next((indice for chave, indice in mapa.items() if chave in {'sala', 'turma', 'classe'}), None)
    if indice_nome is None or indice_sala is None:
        raise ValidationError('O documento precisa ter as colunas “Aluno” (ou “Nome”) e “Sala” (ou “Turma”).')

    salas = {_normalizar_coluna(sala.nome): sala.nome for sala in Sala.objects.filter(escola=escola)}
    validos, erros, vistos = [], [], set()
    for numero_linha, linha in enumerate(linhas, start=2):
        nome = str(linha[indice_nome]).strip() if len(linha) > indice_nome else ''
        sala = str(linha[indice_sala]).strip() if len(linha) > indice_sala else ''
        if not nome and not sala:
            continue
        if not nome or not sala:
            erros.append(f'Linha {numero_linha}: informe aluno e sala.')
            continue
        chave_sala = _normalizar_coluna(sala)
        if chave_sala not in salas:
            erros.append(f'Linha {numero_linha}: a sala “{sala}” do aluno {nome} não está cadastrada nesta escola.')
            continue
        chave = (_normalizar_coluna(nome), chave_sala)
        if chave in vistos:
            erros.append(f'Linha {numero_linha}: {nome} aparece mais de uma vez na sala {salas[chave_sala]}.')
            continue
        vistos.add(chave)
        validos.append({'nome': nome, 'sala': salas[chave_sala]})
    return validos, erros

@login_required
@admin_escola_required
def cadastros(request):
    """Página única com as duas seções: Equipamentos e Horários de Aula."""
    escola = obter_escola_ativa(request)
    return render(request, 'cadastros.html', _dados_cadastros(escola))


@login_required
@admin_escola_required
def adicionar_sala(request):
    if request.method == 'POST':
        escola = obter_escola_ativa(request)
        nome = request.POST.get('nome_sala', '').strip()
        if not nome:
            messages.error(request, 'Informe o nome da sala.')
        elif Sala.objects.filter(escola=escola, nome__iexact=nome).exists():
            messages.error(request, f'A sala “{nome}” já está cadastrada.')
        else:
            Sala.objects.create(escola=escola, nome=nome)
            messages.success(request, f'Sala “{nome}” cadastrada com sucesso.')
    return redirect('cadastros')


@login_required
@admin_escola_required
def adicionar_aluno(request):
    """Cadastra um aluno individualmente na turma selecionada."""
    if request.method != 'POST':
        return redirect('cadastros')

    escola = obter_escola_ativa(request)
    nome = request.POST.get('nome_aluno', '').strip()
    sala_id = request.POST.get('sala_aluno', '')
    sala = Sala.objects.filter(pk=sala_id, escola=escola).first()

    if not nome:
        messages.error(request, 'Informe o nome do aluno.')
    elif not sala:
        messages.error(request, 'Selecione uma sala válida.')
    elif Aluno.objects.filter(nome__iexact=nome, sala=sala).exists():
        messages.warning(request, f'O aluno “{nome}” já está cadastrado na sala {sala.nome}.')
    else:
        Aluno.objects.create(nome=nome, sala=sala)
        messages.success(request, f'Aluno “{nome}” cadastrado na sala {sala.nome}.')
    return redirect('cadastros')


@login_required
@admin_escola_required
def importar_alunos(request):
    escola = obter_escola_ativa(request)
    if request.method != 'POST' or not request.FILES.get('arquivo_alunos'):
        messages.error(request, 'Selecione um arquivo para importar.')
        return redirect('cadastros')
    arquivo = request.FILES['arquivo_alunos']
    if arquivo.size > 10 * 1024 * 1024:
        messages.error(request, 'O arquivo deve ter no máximo 10 MB.')
        return redirect('cadastros')
    try:
        alunos_validos, erros = _validar_planilha_alunos(arquivo, escola)
    except (ValidationError, ValueError, KeyError, ImportError) as erro:
        messages.error(request, f'Não foi possível ler o documento: {erro}')
        return redirect('cadastros')
    request.session['importacao_alunos'] = alunos_validos
    return render(request, 'cadastros.html', _dados_cadastros(
        escola, alunos_importacao=alunos_validos, erros_importacao=erros
    ))


@login_required
@admin_escola_required
def confirmar_importacao_alunos(request):
    escola = obter_escola_ativa(request)
    alunos = request.session.pop('importacao_alunos', [])
    if request.method != 'POST' or not alunos:
        messages.error(request, 'Não há uma importação válida para confirmar.')
        return redirect('cadastros')
    salas = {_normalizar_coluna(sala.nome): sala for sala in Sala.objects.filter(escola=escola)}
    criados, ignorados = 0, 0
    with transaction.atomic():
        for item in alunos:
            sala = salas.get(_normalizar_coluna(item['sala']))
            if not sala:
                continue
            if Aluno.objects.filter(nome__iexact=item['nome'], sala=sala).exists():
                ignorados += 1
            else:
                Aluno.objects.create(nome=item['nome'], sala=sala)
                criados += 1
    messages.success(request, f'Importação concluída: {criados} aluno(s) cadastrado(s); {ignorados} já existiam.')
    return redirect('cadastros')


# ---------------- Equipamentos ----------------

@login_required
@admin_escola_required
def adicionar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentoForm(request.POST)
        if form.is_valid():
            equipamento = form.save(commit=False)
            equipamento.escola = obter_escola_ativa(request)
            equipamento.save()
            messages.success(request, 'Equipamento cadastrado com sucesso.')
        else:
            messages.error(request, 'Corrija os erros no formulário de equipamento.')
    return redirect('cadastros')

@login_required
@admin_escola_required
def editar_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id, escola=obter_escola_ativa(request))

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'salvar_equipamento':
            form = EquipamentoForm(request.POST, instance=equipamento)
            if form.is_valid():
                form.save()
                messages.success(request, 'Equipamento atualizado com sucesso.')
            else:
                messages.error(request, 'Corrija os erros no formulário de equipamento.')

        elif acao == 'liberar_professor':
            form_liberacao = EquipamentoLiberacaoForm(request.POST)
            if form_liberacao.is_valid():
                professor = form_liberacao.cleaned_data['professor']
                _, criado = EquipamentoLiberado.objects.get_or_create(equipamento=equipamento, professor=professor)
                if criado:
                    messages.success(request, f'{professor.username} liberado(a) para reservar "{equipamento.nome}" sem aprovação.')
                else:
                    messages.warning(request, f'{professor.username} já estava liberado(a) para este carrinho.')
            else:
                messages.error(request, 'Selecione um professor válido.')

        elif acao == 'adicionar_bloqueio':
            form_bloqueio = BloqueioEquipamentoForm(request.POST)
            if form_bloqueio.is_valid():
                bloqueio = form_bloqueio.save(commit=False)
                bloqueio.equipamento = equipamento
                bloqueio.criado_por = request.user
                bloqueio.save()
                messages.success(request, 'Horário bloqueado com sucesso.')
            else:
                messages.error(request, 'Corrija os erros no formulário de bloqueio.')

        else:
            messages.error(request, 'Ação inválida.')

        return redirect('editar_equipamento', equipamento_id=equipamento.id)

    form = EquipamentoForm(instance=equipamento)
    form_liberacao = EquipamentoLiberacaoForm()
    form_bloqueio = BloqueioEquipamentoForm()

    liberados = equipamento.professores_liberados.select_related('professor').order_by('professor__username')

    hoje = timezone.localtime(timezone.now()).date()
    bloqueios = equipamento.bloqueios.filter(data__gte=hoje).order_by('data', 'horario_inicio')

    return render(request, 'editar_equipamento.html', {
        'equipamento': equipamento,
        'form': form,
        'form_liberacao': form_liberacao,
        'form_bloqueio': form_bloqueio,
        'liberados': liberados,
        'bloqueios': bloqueios,
    })


@login_required
@admin_escola_required
def remover_liberacao(request, equipamento_id, liberacao_id):
    liberacao = get_object_or_404(EquipamentoLiberado, id=liberacao_id, equipamento_id=equipamento_id, equipamento__escola=obter_escola_ativa(request))
    if request.method == 'POST':
        nome = liberacao.professor.username
        liberacao.delete()
        messages.success(request, f'{nome} não está mais liberado(a) para este carrinho.')
    return redirect('editar_equipamento', equipamento_id=equipamento_id)


@login_required
@admin_escola_required
def remover_bloqueio(request, equipamento_id, bloqueio_id):
    bloqueio = get_object_or_404(BloqueioEquipamento, id=bloqueio_id, equipamento_id=equipamento_id, equipamento__escola=obter_escola_ativa(request))
    if request.method == 'POST':
        bloqueio.delete()
        messages.success(request, 'Bloqueio removido.')
    return redirect('editar_equipamento', equipamento_id=equipamento_id)

@login_required
@admin_escola_required
def excluir_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id, escola=obter_escola_ativa(request))
    if request.method == 'POST':
        nome = equipamento.nome
        equipamento.delete()
        messages.success(request, f'Equipamento "{nome}" excluído.')
    return redirect('cadastros')


# ---------------- Horários de Aula ----------------

@login_required
@admin_escola_required
def adicionar_horario(request):
    if request.method == 'POST':
        form = HorarioAulaForm(request.POST)
        if form.is_valid():
            horario = form.save(commit=False)
            horario.escola = obter_escola_ativa(request)
            horario.save()
            messages.success(request, 'Horário cadastrado com sucesso.')
        else:
            messages.error(request, 'Corrija os erros no formulário de horário.')
    return redirect('cadastros')


@login_required
@admin_escola_required
def editar_horario(request, horario_id):
    horario = get_object_or_404(HorarioAula, id=horario_id, escola=obter_escola_ativa(request))
    if request.method == 'POST':
        form = HorarioAulaForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Horário atualizado com sucesso.')
            return redirect('cadastros')
    else:
        form = HorarioAulaForm(instance=horario)

    return render(request, 'editar_horario.html', {
        'form': form,
        'horario': horario,
    })


@login_required
@admin_escola_required
def excluir_horario(request, horario_id):
    horario = get_object_or_404(HorarioAula, id=horario_id, escola=obter_escola_ativa(request))
    if request.method == 'POST':
        horario.delete()
        messages.success(request, 'Horário excluído.')
    return redirect('cadastros')

