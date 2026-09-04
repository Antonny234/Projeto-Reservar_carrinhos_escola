from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import (Equipamento, HorarioAula, EquipamentoLiberado, BloqueioEquipamento)
from ..forms import EquipamentoForm, HorarioAulaForm, EquipamentoLiberacaoForm, BloqueioEquipamentoForm
from django.utils import timezone

@login_required
@staff_member_required
def cadastros(request):
    """Página única com as duas seções: Equipamentos e Horários de Aula."""
    equipamentos = Equipamento.objects.all().order_by('nome')
    horarios = HorarioAula.objects.all().order_by('numero')

    form_equipamento = EquipamentoForm()
    form_horario = HorarioAulaForm()

    context = {
        'equipamentos': equipamentos,
        'horarios': horarios,
        'form_equipamento': form_equipamento,
        'form_horario': form_horario,
    }
    return render(request, 'cadastros.html', context)


# ---------------- Equipamentos ----------------

@login_required
@staff_member_required
def adicionar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento cadastrado com sucesso.')
        else:
            messages.error(request, 'Corrija os erros no formulário de equipamento.')
    return redirect('cadastros')

@login_required
@staff_member_required
def editar_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)

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
@staff_member_required
def remover_liberacao(request, equipamento_id, liberacao_id):
    liberacao = get_object_or_404(EquipamentoLiberado, id=liberacao_id, equipamento_id=equipamento_id)
    if request.method == 'POST':
        nome = liberacao.professor.username
        liberacao.delete()
        messages.success(request, f'{nome} não está mais liberado(a) para este carrinho.')
    return redirect('editar_equipamento', equipamento_id=equipamento_id)


@login_required
@staff_member_required
def remover_bloqueio(request, equipamento_id, bloqueio_id):
    bloqueio = get_object_or_404(BloqueioEquipamento, id=bloqueio_id, equipamento_id=equipamento_id)
    if request.method == 'POST':
        bloqueio.delete()
        messages.success(request, 'Bloqueio removido.')
    return redirect('editar_equipamento', equipamento_id=equipamento_id)

@login_required
@staff_member_required
def excluir_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)
    if request.method == 'POST':
        nome = equipamento.nome
        equipamento.delete()
        messages.success(request, f'Equipamento "{nome}" excluído.')
    return redirect('cadastros')


# ---------------- Horários de Aula ----------------

@login_required
@staff_member_required
def adicionar_horario(request):
    if request.method == 'POST':
        form = HorarioAulaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Horário cadastrado com sucesso.')
        else:
            messages.error(request, 'Corrija os erros no formulário de horário.')
    return redirect('cadastros')


@login_required
@staff_member_required
def editar_horario(request, horario_id):
    horario = get_object_or_404(HorarioAula, id=horario_id)
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
@staff_member_required
def excluir_horario(request, horario_id):
    horario = get_object_or_404(HorarioAula, id=horario_id)
    if request.method == 'POST':
        horario.delete()
        messages.success(request, 'Horário excluído.')
    return redirect('cadastros')

