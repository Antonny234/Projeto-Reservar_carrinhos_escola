from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q,Count
from django.shortcuts import render, redirect, get_object_or_404

from ..models import GrupoEquipamento, EquipamentoInventario, Transferencia
from ..forms import GrupoEquipamentoForm, EquipamentoInventarioForm, TransferenciaForm


def is_staff(user):
    return user.is_authenticated and user.is_staff


def inventario_lista(request):
    """
    Sem busca: mostra os grupos em cards, com a quantidade de equipamentos de cada um.
    Com busca (?q=...): mostra os equipamentos encontrados em todos os grupos.
    """
    termo = request.GET.get('q', '').strip()

    if termo:
        equipamentos = EquipamentoInventario.objects.select_related('grupo').filter(
            Q(numero_serie__icontains=termo) |
            Q(numero_patrimonio__icontains=termo) |
            Q(tipo__icontains=termo) |
            Q(localizacao_atual__icontains=termo) |
            Q(identificador__icontains=termo)
        )
        return render(request, 'inventario_lista.html', {
            'modo': 'busca',
            'termo': termo,
            'equipamentos': equipamentos,
        })

    grupos = GrupoEquipamento.objects.annotate(total=Count('equipamentos')).order_by('nome')
    return render(request, 'inventario_lista.html', {
        'modo': 'grupos',
        'grupos': grupos,
    })


def grupo_equipamentos(request, grupo_id):
    """Lista os equipamentos de um grupo específico, com busca local opcional."""
    grupo = get_object_or_404(GrupoEquipamento, pk=grupo_id)
    equipamentos = grupo.equipamentos.all()

    termo = request.GET.get('q', '').strip()
    if termo:
        equipamentos = equipamentos.filter(
            Q(numero_serie__icontains=termo) |
            Q(numero_patrimonio__icontains=termo) |
            Q(tipo__icontains=termo) |
            Q(localizacao_atual__icontains=termo) |
            Q(identificador__icontains=termo)
        )

    return render(request, 'grupo_equipamentos.html', {
        'grupo': grupo,
        'equipamentos': equipamentos,
        'termo': termo,
    })


@login_required
def inventario_detalhe(request, pk):
    """Detalhe do equipamento + histórico de transferências."""
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk)
    historico = equipamento.transferencias.select_related('usuario').all()

    return render(request, 'inventario_detalhe.html', {
        'equipamento': equipamento,
        'historico': historico,
    })


@user_passes_test(is_staff)
def equipamento_novo(request):
    if request.method == 'POST':
        form = EquipamentoInventarioForm(request.POST)
        if form.is_valid():
            equipamento = form.save()
            messages.success(request, 'Equipamento cadastrado com sucesso.')
            return redirect('inventario_detalhe', pk=equipamento.pk)
    else:
        form = EquipamentoInventarioForm()

    return render(request, 'equipamento_form.html', {'form': form})


@user_passes_test(is_staff)
def grupo_novo(request):
    if request.method == 'POST':
        form = GrupoEquipamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grupo criado com sucesso.')
            return redirect('inventario_lista')
    else:
        form = GrupoEquipamentoForm()

    return render(request, 'grupo_form.html', {'form': form})


@user_passes_test(is_staff)
def transferir_equipamento(request, pk):
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk)

    if request.method == 'POST':
        form = TransferenciaForm(request.POST)
        if form.is_valid():
            novo_local = form.cleaned_data['local_destino']
            observacao = form.cleaned_data['observacao']

            Transferencia.objects.create(
                equipamento=equipamento,
                local_origem=equipamento.localizacao_atual,
                local_destino=novo_local,
                usuario=request.user,
                observacao=observacao,
            )

            equipamento.localizacao_atual = novo_local
            equipamento.save()

            messages.success(request, f'Equipamento transferido para "{novo_local}".')
            return redirect('inventario_detalhe', pk=equipamento.pk)
    else:
        form = TransferenciaForm(initial={'local_destino': equipamento.localizacao_atual})

    return render(request, 'transferencia_form.html', {
        'form': form,
        'equipamento': equipamento,
    })

@user_passes_test(is_staff)
def equipamento_editar(request, pk):
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk)

    if request.method == 'POST':
        form = EquipamentoInventarioForm(request.POST, instance=equipamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento atualizado com sucesso.')
            return redirect('inventario_detalhe', pk=equipamento.pk)
    else:
        form = EquipamentoInventarioForm(instance=equipamento)

    return render(request, 'equipamento_form.html', {
        'form': form,
        'editando': True,
        'equipamento': equipamento,
    })

@user_passes_test(is_staff)
def equipamento_excluir(request, pk):
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk)

    if request.method == 'POST':
        nome = str(equipamento)
        equipamento.delete()
        messages.success(request, f'Equipamento "{nome}" excluído com sucesso.')
        return redirect('inventario_lista')

    return render(request, 'equipamento_confirmar_exclusao.html', {
        'equipamento': equipamento,
    })
@user_passes_test(is_staff)
def grupo_excluir(request, pk):
    grupo = get_object_or_404(GrupoEquipamento, id=pk)

    if request.method != 'POST':
        return redirect('inventario_lista')

    nome = str(grupo)
    total_equipamentos, _ = grupo.equipamentos.all().delete()  
    grupo.delete() 

    if total_equipamentos > 0:
        messages.success(request, f'Grupo "{nome}" e {total_equipamentos} equipamento(s) excluídos com sucesso.')
    else:
        messages.success(request, f'Grupo "{nome}" excluído com sucesso.')

    return redirect('inventario_lista')