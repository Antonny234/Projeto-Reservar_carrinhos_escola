from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q,Count
from django.shortcuts import render, redirect, get_object_or_404

from ..models import GrupoEquipamento, EquipamentoInventario, Transferencia
from ..forms import CadastroLoteEquipamentosForm, GrupoEquipamentoForm, EquipamentoInventarioForm, TransferenciaForm, campo_nativo_do_inventario, dados_para_campos_nativos, normalizar_campos_inventario
from ..decorators import admin_escola_required
from ..utils import obter_escola_ativa


@login_required
@admin_escola_required
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
            Q(identificador__icontains=termo),
            grupo__escola=obter_escola_ativa(request),
        )
        return render(request, 'inventario_lista.html', {
            'modo': 'busca',
            'termo': termo,
            'equipamentos': equipamentos,
        })

    grupos = GrupoEquipamento.objects.filter(escola=obter_escola_ativa(request)).annotate(total=Count('equipamentos')).order_by('nome')
    return render(request, 'inventario_lista.html', {
        'modo': 'grupos',
        'grupos': grupos,
    })


@login_required
@admin_escola_required
def configurar_campos_inventario(request):
    escola = obter_escola_ativa(request)
    if request.method == 'POST':
        nomes = request.POST.getlist('nome_campo')
        tipos = request.POST.getlist('tipo_campo')
        campos, vistos, erro = [], set(), None
        for nome, tipo in zip(nomes, tipos):
            nome = nome.strip()
            if not nome:
                continue
            if len(nome) > 80 or tipo not in {'numero', 'texto', 'ambos'}:
                erro = 'Há um campo inválido na configuração.'
                break
            if nome.casefold() in vistos:
                erro = f'O campo "{nome}" foi informado mais de uma vez.'
                break
            vistos.add(nome.casefold())
            campos.append({'nome': nome, 'tipo': tipo})
        if erro:
            messages.error(request, erro)
        else:
            escola.campos_inventario = normalizar_campos_inventario(campos)
            escola.save(update_fields=['campos_inventario'])
            messages.success(request, 'Campos do inventário atualizados.')
            return redirect('inventario_lista')
    return render(request, 'configurar_campos_inventario.html', {
        'campos': normalizar_campos_inventario(escola.campos_inventario),
        'escola': escola,
    })


@login_required
@admin_escola_required
def grupo_equipamentos(request, grupo_id):
    """Lista os equipamentos de um grupo específico, com busca local opcional."""
    grupo = get_object_or_404(GrupoEquipamento, pk=grupo_id, escola=obter_escola_ativa(request))
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
        'campos': normalizar_campos_inventario(grupo.escola.campos_inventario),
    })


@login_required
@admin_escola_required
def inventario_detalhe(request, pk):
    """Detalhe do equipamento + histórico de transferências."""
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk, grupo__escola=obter_escola_ativa(request))
    historico = equipamento.transferencias.select_related('usuario').all()
    valores_principais = dados_para_campos_nativos(equipamento.dados_personalizados, {
        'identificador': equipamento.identificador or '',
        'numero_patrimonio': equipamento.numero_patrimonio,
        'numero_serie': equipamento.numero_serie,
        'localizacao_atual': equipamento.localizacao_atual,
    })
    dados_extras = [
        (nome, valor) for nome, valor in equipamento.dados_personalizados.items()
        if not campo_nativo_do_inventario(nome)
    ]

    return render(request, 'inventario_detalhe.html', {
        'equipamento': equipamento,
        'historico': historico,
        'valores_principais': valores_principais,
        'dados_extras': dados_extras,
    })


@admin_escola_required
def equipamento_novo(request):
    escola = obter_escola_ativa(request)
    campos = normalizar_campos_inventario(escola.campos_inventario)
    if request.method == 'POST':
        if 'cadastro_lote' in request.POST:
            form = EquipamentoInventarioForm(escola=escola)
            form.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)
            lote_form = CadastroLoteEquipamentosForm(request.POST, escola=escola)
            if lote_form.is_valid():
                equipamentos = lote_form.save()
                messages.success(request, f'{len(equipamentos)} equipamento(s) cadastrado(s) com sucesso.')
                return redirect('grupo_equipamentos', grupo_id=lote_form.cleaned_data['grupo'].pk)
        else:
            lote_form = CadastroLoteEquipamentosForm(escola=escola)
            form = EquipamentoInventarioForm(request.POST, escola=escola)
            form.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)
            if form.is_valid():
                equipamento = form.save()
                messages.success(request, 'Equipamento cadastrado com sucesso.')
                return redirect('inventario_detalhe', pk=equipamento.pk)
    else:
        grupo_inicial = GrupoEquipamento.objects.filter(
            pk=request.GET.get('grupo'), escola=escola
        ).first()
        form = EquipamentoInventarioForm(
            escola=escola,
            initial={'grupo': grupo_inicial} if grupo_inicial else None,
        )
        form.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)
        lote_form = CadastroLoteEquipamentosForm(
            escola=escola,
            initial={'grupo': grupo_inicial} if grupo_inicial else None,
        )

    return render(request, 'equipamento_form.html', {
        'form': form,
        'lote_form': lote_form,
        'campos': campos,
        'modo_lote': request.method == 'POST' and 'cadastro_lote' in request.POST,
    })


@admin_escola_required
def grupo_novo(request):
    if request.method == 'POST':
        form = GrupoEquipamentoForm(request.POST)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.escola = obter_escola_ativa(request)
            grupo.save()
            messages.success(request, 'Grupo criado com sucesso.')
            return redirect('inventario_lista')
    else:
        form = GrupoEquipamentoForm()

    return render(request, 'grupo_form.html', {'form': form})


@admin_escola_required
def transferir_equipamento(request, pk):
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk, grupo__escola=obter_escola_ativa(request))

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

@admin_escola_required
def equipamento_editar(request, pk):
    escola = obter_escola_ativa(request)
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk, grupo__escola=escola)

    if request.method == 'POST':
        form = EquipamentoInventarioForm(request.POST, instance=equipamento, escola=escola)
        form.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento atualizado com sucesso.')
            return redirect('inventario_detalhe', pk=equipamento.pk)
    else:
        form = EquipamentoInventarioForm(instance=equipamento, escola=escola)
        form.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)

    return render(request, 'equipamento_form.html', {
        'form': form,
        'editando': True,
        'equipamento': equipamento,
    })

@admin_escola_required
def equipamento_excluir(request, pk):
    equipamento = get_object_or_404(EquipamentoInventario, pk=pk, grupo__escola=obter_escola_ativa(request))

    if request.method == 'POST':
        nome = str(equipamento)
        equipamento.delete()
        messages.success(request, f'Equipamento "{nome}" excluído com sucesso.')
        return redirect('inventario_lista')

    return render(request, 'equipamento_confirmar_exclusao.html', {
        'equipamento': equipamento,
    })
@admin_escola_required
def grupo_excluir(request, pk):
    grupo = get_object_or_404(GrupoEquipamento, id=pk, escola=obter_escola_ativa(request))

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
