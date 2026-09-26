import json
import logging
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from ..decorators import admin_escola_required
from ..models import TelegramBotEscola, TelegramDestino, Escola
from ..telegram import (
    configurar_webhook,
    cifrar_token,
    decifrar_token,
    gerar_pareamento,
    validar_bot_token,
    validar_webhook_secret,
    enviar_telegram,
)
from ..utils import obter_escola_ativa

logger = logging.getLogger(__name__)


@login_required
@admin_escola_required
def telegram_painel(request):
    escola_id = request.POST.get('escola_id') or request.GET.get('escola_id')
    if request.user.is_superuser and escola_id:
        escola = get_object_or_404(Escola, pk=escola_id)
    else:
        escola = obter_escola_ativa(request)
    bot = TelegramBotEscola.objects.filter(escola=escola).first()
    destinos = bot.destinos.filter(ativo=True) if bot else []
    pareamento = None

    if request.method == 'POST':
        acao = request.POST.get('acao', '').strip()

        try:
            if acao == 'configurar':
                token = request.POST.get('bot_token', '').strip()
                if not bot and not token:
                    messages.error(request, 'Informe o token do bot criado no @BotFather.')
                else:
                    token_real = token if token else decifrar_token(bot)
                    dados_bot = validar_bot_token(token_real)
                    token_cifrado_novo = cifrar_token(token_real) if token else None
                    token_mudou = False
                    token_anterior = ''
                    if bot and token:
                        token_anterior = decifrar_token(bot) if bot.bot_token_cifrado else ''
                        token_mudou = token_real != token_anterior
                        if token_mudou:
                            try:
                                from ..telegram import _api_request
                                _api_request(token_anterior, 'deleteWebhook', {'drop_pending_updates': True})
                            except Exception:
                                logger.warning('Não foi possível remover o webhook antigo do bot da escola %s.', escola.pk)
                                logger.debug('Detalhes do webhook antigo', exc_info=True)
                    if not bot:
                        bot = TelegramBotEscola.objects.create(
                            escola=escola,
                            webhook_slug=secrets.token_urlsafe(24).replace('-', '').replace('_', '')[:80],
                        )
                    if token_mudou:
                        bot.destinos.all().delete()
                        bot.pareamentos.filter(usado_em__isnull=True).update(usado_em=timezone.now())
                        bot.webhook_slug = secrets.token_urlsafe(24).replace('-', '').replace('_', '')[:80]
                        bot.webhook_configurado = False
                    bot.bot_username = dados_bot.get('username', '')
                    bot.bot_nome = dados_bot.get('first_name', '')
                    if token_cifrado_novo:
                        bot.bot_token_cifrado = token_cifrado_novo
                    bot.ativo = True
                    bot.ultimo_erro = ''
                    bot.save()
                    configurar_webhook(bot, request)
                    messages.success(request, f'Bot @{bot.bot_username} conectado e webhook ativado com sucesso.')

            elif acao == 'parear':
                if not bot or not bot.ativo:
                    messages.error(request, 'Configure e ative o bot antes de gerar um link de conexão.')
                else:
                    codigo, link = gerar_pareamento(bot, request.user)
                    request.session['telegram_pairing'] = {'codigo': codigo, 'link': link}
                    messages.success(request, 'Link de conexão gerado. Ele expira em 10 minutos e só pode ser usado uma vez.')

            elif acao == 'testar':
                if not bot or not bot.ativo:
                    messages.error(request, 'Nenhum bot ativo configurado para esta escola.')
                else:
                    quantidade = enviar_telegram(
                        f'🧪 <b>Teste do GTREP</b>\\nEscola: {escola.nome}\\nHorário: {timezone.localtime():%d/%m/%Y %H:%M}',
                        escola=escola,
                    )
                    if quantidade:
                        messages.success(request, f'Teste enviado para {quantidade} destino(s).')
                    else:
                        messages.warning(request, 'Não há destinos ativos para receber o teste.')

            elif acao == 'adicionar_destino':
                if not bot:
                    messages.error(request, 'Configure o bot primeiro.')
                else:
                    chat_id = request.POST.get('chat_id', '').strip()
                    nome = request.POST.get('nome', '').strip()[:200]
                    if not chat_id or not chat_id.lstrip('-').isdigit():
                        messages.error(request, 'Informe um chat_id numérico válido.')
                    else:
                        TelegramDestino.objects.update_or_create(
                            bot=bot,
                            chat_id=chat_id,
                            defaults={'nome': nome or chat_id, 'ativo': True},
                        )
                        messages.success(request, 'Destino Telegram adicionado.')

            elif acao == 'remover_destino':
                destino = get_object_or_404(
                    TelegramDestino,
                    pk=request.POST.get('destino_id'),
                    bot=bot,
                )
                destino.delete()
                messages.success(request, 'Destino removido.')

            elif acao == 'desativar':
                if bot:
                    try:
                        from ..telegram import remover_webhook
                        remover_webhook(bot)
                    except Exception:
                        logger.exception('Falha ao remover webhook durante desativação do bot.')
                    bot.ativo = False
                    bot.webhook_configurado = False
                    bot.save(update_fields=['ativo', 'webhook_configurado', 'atualizado_em'])
                    messages.success(request, 'Bot desativado. O token foi mantido de forma cifrada para uma futura reativação.')

            elif acao == 'reativar':
                if not bot:
                    messages.error(request, 'Nenhum bot configurado.')
                else:
                    bot.ativo = True
                    bot.save(update_fields=['ativo', 'atualizado_em'])
                    configurar_webhook(bot, request)
                    messages.success(request, f'Bot @{bot.bot_username} reativado.')

        except Exception as exc:
            logger.exception('Falha na administração do Telegram da escola %s', escola.pk)
            if bot:
                bot.ultimo_erro = str(exc)[:2000]
                bot.save(update_fields=['ultimo_erro', 'atualizado_em'])
            messages.error(request, f'Não foi possível concluir a operação: {exc}')

        return redirect('telegram_painel')

    pareamento = request.session.pop('telegram_pairing', None)

    return render(request, 'telegram_painel.html', {
        'escola': escola,
        'bot': bot,
        'destinos': destinos,
        'pareamento': pareamento,
    })


@csrf_exempt
@require_POST
def telegram_webhook(request, webhook_slug):
    bot = TelegramBotEscola.objects.select_related('escola').filter(
        webhook_slug=webhook_slug,
        ativo=True,
    ).first()
    if not bot:
        return HttpResponse(status=404)

    received_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if not validar_webhook_secret(bot, received_secret):
        logger.warning('Webhook Telegram rejeitado para bot da escola %s', bot.escola_id)
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'detail': 'JSON inválido.'}, status=400)

    try:
        from ..telegram import processar_webhook
        processar_webhook(bot, payload)
    except Exception:
        logger.exception('Erro processando webhook Telegram da escola %s', bot.escola_id)
        # Telegram pode reenviar se receber erro; como o segredo já validou a origem,
        # mantemos 200 para não criar tempestade de reentregas por falha interna.

    return JsonResponse({'ok': True})
