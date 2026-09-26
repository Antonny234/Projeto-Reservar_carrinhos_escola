import csv
import logging
import os
from io import BytesIO, StringIO

import resend
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..decorators import admin_escola_required
from ..models import Escola, EquipamentoInventario, GrupoEquipamento, TransferenciaEscola, ItemTransferenciaEscola
from ..utils import obter_escola_ativa

logger = logging.getLogger(__name__)


def _notificar_escola_origem(transferencia_id):
    """Aviso por e-mail aos administradores da origem, quando Resend está configurado."""
    transferencia = TransferenciaEscola.objects.select_related('origem', 'destino').get(pk=transferencia_id)
    destinatarios = list(transferencia.origem.administradores.select_related('usuario').values_list('usuario__email', flat=True))
    destinatarios += list(transferencia.origem.administradores_multiplos.select_related('usuario').values_list('usuario__email', flat=True))
    destinatarios = sorted({email for email in destinatarios if email})
    chave = os.environ.get('RESEND_API_KEY')
    if not chave or not settings.DEFAULT_FROM_EMAIL or not destinatarios:
        logger.info('Aviso de recebimento da transferência %s disponível no painel; e-mail sem configuração ou destinatário.', transferencia_id)
        return
    try:
        resend.api_key = chave
        resend.Emails.send({
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': destinatarios,
            'subject': f'Transferência {transferencia_id} recebida por {transferencia.destino.nome}',
            'text': f'A transferência {transferencia_id} foi conferida e recebida por {transferencia.recebida_por_nome}. O inventário foi atualizado.',
        })
    except Exception:
        logger.exception('Falha ao enviar confirmação da transferência %s', transferencia_id)


@login_required
@admin_escola_required
def iniciar_transferencia_escola(request):
    escola = obter_escola_ativa(request)
    if request.method == 'POST':
        destino = get_object_or_404(Escola, pk=request.POST.get('destino'))
        tipo = request.POST.get('identificador_tipo', '')
        campo = {'id': 'identificador', 'serie': 'numero_serie', 'patrimonio': 'numero_patrimonio'}.get(tipo)
        valores = [v.strip() for v in request.POST.get('identificadores', '').splitlines() if v.strip()]
        if destino.pk == escola.pk or not campo or not valores:
            messages.error(request, 'Informe destino, identificação e ao menos um item válido.')
            return redirect('iniciar_transferencia_escola')
        with transaction.atomic():
            filtro = Q(**{f'{campo}__in': valores})
            if tipo == 'id':
                ids = [int(v) for v in valores if v.isdigit()]
                filtro |= Q(pk__in=ids)
            itens = list(EquipamentoInventario.objects.select_for_update().filter(filtro, grupo__escola=escola))
            index = {}
            for valor in valores:
                encontrados = [item for item in itens if str(item.pk) == valor or str(getattr(item, campo) or '') == valor]
                if len(encontrados) == 1:
                    index[valor] = encontrados[0]
            if len(index) != len(valores) or len({item.pk for item in index.values()}) != len(valores):
                messages.error(request, 'Um ou mais itens não foram encontrados na escola de origem.')
                return redirect('iniciar_transferencia_escola')
            if ItemTransferenciaEscola.objects.filter(equipamento__in=index.values(), transferencia__status='pendente').exists():
                messages.error(request, 'Um ou mais equipamentos já aguardam conferência em outra transferência.')
                return redirect('iniciar_transferencia_escola')
            transferencia = TransferenciaEscola.objects.create(origem=escola, destino=destino, criada_por=request.user)
            ItemTransferenciaEscola.objects.bulk_create([
                ItemTransferenciaEscola(transferencia=transferencia, equipamento=index[v], identificador_tipo=tipo, identificador_valor=v)
                for v in valores
            ])
        return redirect('comprovante_transferencia_escola', pk=transferencia.pk)
    return render(request, 'transferencia_escola_form.html', {
        'escolas': Escola.objects.exclude(pk=escola.pk).order_by('nome'),
        'equipamentos': EquipamentoInventario.objects.filter(grupo__escola=escola).select_related('grupo'),
    })


@login_required
@admin_escola_required
def transferencias_pendentes(request):
    escola = obter_escola_ativa(request)
    recebidas = TransferenciaEscola.objects.filter(destino=escola, status='pendente').select_related('origem').prefetch_related('itens__equipamento')
    enviadas = TransferenciaEscola.objects.filter(origem=escola).select_related('destino').prefetch_related('itens__equipamento')
    return render(request, 'transferencias_escola.html', {'recebidas': recebidas, 'enviadas': enviadas})


@login_required
@admin_escola_required
@require_POST
def receber_transferencia_escola(request, pk):
    escola = obter_escola_ativa(request)
    nome = request.POST.get('nome_completo', '').strip()
    if len(nome.split()) < 2 or len(nome) > 200:
        messages.error(request, 'Informe seu nome e sobrenome para assinar a conferência.')
        return redirect('transferencias_pendentes')
    with transaction.atomic():
        transferencia = get_object_or_404(TransferenciaEscola.objects.select_for_update(), pk=pk, destino=escola, status='pendente')
        for item in transferencia.itens.select_related('equipamento__grupo'):
            grupo_destino, _ = GrupoEquipamento.objects.get_or_create(escola=escola, nome=item.equipamento.grupo.nome)
            item.equipamento.grupo = grupo_destino
            item.equipamento.save(update_fields=['grupo'])
        transferencia.status = 'recebida'
        transferencia.recebida_por = request.user
        transferencia.recebida_por_nome = nome
        transferencia.recebida_em = timezone.now()
        transferencia.save(update_fields=['status', 'recebida_por', 'recebida_por_nome', 'recebida_em'])
        transaction.on_commit(lambda: _notificar_escola_origem(transferencia.pk))
    messages.success(request, 'Recebimento confirmado; o inventário foi atualizado e a escola de origem pode consultar a confirmação.')
    return redirect('transferencias_pendentes')


@login_required
@admin_escola_required
def checklist_transferencia_escola(request, pk):
    escola = obter_escola_ativa(request)
    transferencia = get_object_or_404(TransferenciaEscola.objects.prefetch_related('itens__equipamento'), pk=pk, destino=escola)
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['Tipo', 'Identificador conferido', 'Patrimônio', 'Número de série', 'Tipo de equipamento', 'Conferido'])
    for item in transferencia.itens.all():
        equip = item.equipamento
        writer.writerow([item.identificador_tipo, item.identificador_valor, equip.numero_patrimonio, equip.numero_serie, equip.tipo, '[ ]'])
    response = HttpResponse('\ufeff' + out.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="checklist-transferencia-{pk}.csv"'
    return response


@login_required
@admin_escola_required
def comprovante_transferencia_escola(request, pk):
    escola = obter_escola_ativa(request)
    transferencia = get_object_or_404(TransferenciaEscola.objects.select_related('origem', 'destino').prefetch_related('itens__equipamento'), pk=pk, origem=escola)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError('Instale reportlab para gerar comprovantes PDF.') from exc
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f'Comprovante de transferência {pk}')
    y = 800
    pdf.setFont('Helvetica-Bold', 16); pdf.drawString(48, y, f'Transferência entre escolas #{pk}'); y -= 30
    pdf.setFont('Helvetica', 10)
    for linha in [f'Origem: {transferencia.origem.nome}', f'Destino: {transferencia.destino.nome}', f'Data: {transferencia.criada_em:%d/%m/%Y %H:%M}', f'Status: {transferencia.get_status_display()}', 'Itens:']:
        pdf.drawString(48, y, linha); y -= 18
    for item in transferencia.itens.all():
        eq = item.equipamento
        linha = f'{item.identificador_tipo}: {item.identificador_valor} | Patrimônio: {eq.numero_patrimonio} | Série: {eq.numero_serie} | {eq.tipo}'
        if y < 60:
            pdf.showPage(); y = 800; pdf.setFont('Helvetica', 9)
        pdf.drawString(48, y, linha[:115]); y -= 16
    pdf.save()
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprovante-transferencia-{pk}.pdf"'
    return response
