"""Integração multi-escola com Telegram Bot API.

Cada escola possui um bot próprio. O token é armazenado cifrado com Fernet e
os chats são vinculados por um código temporário enviado ao próprio bot.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta
from urllib.parse import quote

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import TelegramBotEscola, TelegramDestino, TelegramPareamento

logger = logging.getLogger(__name__)

PAIRING_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
PAIRING_MINUTES = 10


def _fernet() -> Fernet:
    key = getattr(settings, 'TELEGRAM_ENCRYPTION_KEY', '')
    if not key:
        raise RuntimeError('TELEGRAM_ENCRYPTION_KEY não configurada.')
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise RuntimeError('TELEGRAM_ENCRYPTION_KEY inválida. Gere uma chave Fernet válida.') from exc


def cifrar_token(token: str) -> str:
    return _fernet().encrypt(token.encode('utf-8')).decode('utf-8')


def decifrar_token(bot: TelegramBotEscola) -> str:
    if not bot.bot_token_cifrado:
        raise RuntimeError('Bot sem token configurado.')
    try:
        return _fernet().decrypt(bot.bot_token_cifrado.encode('utf-8')).decode('utf-8')
    except InvalidToken as exc:
        raise RuntimeError('Não foi possível decifrar o token do bot. Verifique TELEGRAM_ENCRYPTION_KEY.') from exc


def gerar_webhook_secret(bot: TelegramBotEscola) -> str:
    payload = f'telegram-webhook:{bot.pk}:{bot.webhook_slug}'
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def _api_request(token: str, method: str, payload: dict | None = None, timeout: float = 8.0) -> dict:
    url = f'https://api.telegram.org/bot{token}/{method}'
    response = requests.post(url, json=payload or {}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not data.get('ok'):
        raise RuntimeError(data.get('description') or 'Telegram recusou a solicitação.')
    return data


def validar_bot_token(token: str) -> dict:
    data = _api_request(token.strip(), 'getMe')
    result = data.get('result') or {}
    if not result.get('is_bot') or not result.get('username'):
        raise RuntimeError('O token informado não corresponde a um bot Telegram válido.')
    return result


def configurar_webhook(bot: TelegramBotEscola, request) -> None:
    token = decifrar_token(bot)
    webhook_url = request.build_absolute_uri(
        reverse('telegram_webhook', kwargs={'webhook_slug': bot.webhook_slug})
    )
    if not webhook_url.startswith('https://'):
        raise RuntimeError('O webhook do Telegram exige HTTPS. Configure o domínio HTTPS antes de ativar o bot.')

    _api_request(
        token,
        'setWebhook',
        {
            'url': webhook_url,
            'secret_token': gerar_webhook_secret(bot),
            'allowed_updates': ['message'],
            'drop_pending_updates': True,
        },
    )
    bot.webhook_configurado = True
    bot.ultimo_erro = ''
    bot.ultima_verificacao = timezone.now()
    _api_request(
        token,
        'setMyCommands',
        {'commands': [
            {'command': 'status', 'description': 'Verifica a conexão com a escola'},
            {'command': 'ajuda', 'description': 'Mostra os comandos disponíveis'},
        ]},
    )
    bot.save(update_fields=['webhook_configurado', 'ultimo_erro', 'ultima_verificacao', 'atualizado_em'])


def remover_webhook(bot: TelegramBotEscola) -> None:
    token = decifrar_token(bot)
    _api_request(token, 'deleteWebhook', {'drop_pending_updates': True})
    bot.webhook_configurado = False
    bot.save(update_fields=['webhook_configurado', 'atualizado_em'])


def enviar_telegram(mensagem: str, escola=None) -> int:
    """Envia mensagem para todos os destinos ativos da escola.

    Retorna o número de chats que receberam o envio com sucesso. Falhas não
    sobem para a requisição principal, pois alerta não pode impedir reserva.
    """
    if escola is None:
        logger.warning('Notificação Telegram descartada: escola não informada.')
        return 0

    bot = TelegramBotEscola.objects.filter(escola=escola, ativo=True).first()
    if not bot or not bot.bot_token_cifrado:
        return 0

    destinos = list(bot.destinos.filter(ativo=True))
    if not destinos:
        return 0

    try:
        token = decifrar_token(bot)
    except RuntimeError:
        logger.exception('Falha ao decifrar token Telegram da escola %s', escola.pk)
        return 0

    enviados = 0
    for destino in destinos:
        try:
            _api_request(
                token,
                'sendMessage',
                {
                    'chat_id': destino.chat_id,
                    'text': mensagem[:4096],
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True,
                },
            )
            destino.ultimo_envio = timezone.now()
            destino.save(update_fields=['ultimo_envio'])
            enviados += 1
        except requests.RequestException:
            logger.exception('Falha HTTP ao enviar Telegram para chat %s', destino.chat_id)
        except Exception:
            logger.exception('Falha Telegram para escola %s / chat %s', escola.pk, destino.chat_id)
    return enviados


def gerar_pareamento(bot: TelegramBotEscola, usuario) -> tuple[str, str]:
    codigo = ''.join(secrets.choice(PAIRING_ALPHABET) for _ in range(10))
    codigo_hash = hashlib.sha256(codigo.encode('utf-8')).hexdigest()
    TelegramPareamento.objects.filter(bot=bot, usado_em__isnull=True).update(usado_em=timezone.now())
    TelegramPareamento.objects.create(
        bot=bot,
        codigo_hash=codigo_hash,
        expira_em=timezone.now() + timedelta(minutes=PAIRING_MINUTES),
        criado_por=usuario,
    )
    link = f'https://t.me/{quote(bot.bot_username)}?start={codigo}'
    return codigo, link


def _nome_chat(chat: dict, remetente: dict) -> str:
    if chat.get('title'):
        return chat['title']
    nome = ' '.join(
        part for part in [remetente.get('first_name'), remetente.get('last_name')] if part
    ).strip()
    return nome or remetente.get('username') or str(chat.get('id'))


def processar_webhook(bot: TelegramBotEscola, payload: dict) -> None:
    message = payload.get('message') or {}
    chat = message.get('chat') or {}
    remetente = message.get('from') or {}
    chat_id = chat.get('id')
    texto = (message.get('text') or '').strip()
    if chat_id is None:
        return

    # /start CODIGO -> conclui o pareamento.
    if texto.startswith('/start'):
        partes = texto.split(maxsplit=1)
        codigo = partes[1].strip() if len(partes) == 2 else ''
        pareamento = None
        if codigo:
            codigo_hash = hashlib.sha256(codigo.upper().encode('utf-8')).hexdigest()
            pareamento = TelegramPareamento.objects.filter(
                bot=bot,
                codigo_hash=codigo_hash,
                usado_em__isnull=True,
                expira_em__gte=timezone.now(),
            ).order_by('-criado_em').first()

        if pareamento:
            nome = _nome_chat(chat, remetente)
            TelegramDestino.objects.update_or_create(
                bot=bot,
                chat_id=str(chat_id),
                defaults={'nome': nome, 'ativo': True},
            )
            pareamento.usado_em = timezone.now()
            pareamento.save(update_fields=['usado_em'])
            _api_request(
                decifrar_token(bot),
                'sendMessage',
                {
                    'chat_id': chat_id,
                    'text': (
                        '✅ <b>Telegram conectado</b>\n'
                        f'Escola: {bot.escola.nome}\n'
                        'Este chat passará a receber as notificações do sistema.'
                    ),
                    'parse_mode': 'HTML',
                },
            )
            return

        destino_existe = bot.destinos.filter(chat_id=str(chat_id), ativo=True).exists()
        if destino_existe:
            _api_request(
                decifrar_token(bot),
                'sendMessage',
                {
                    'chat_id': chat_id,
                    'text': '✅ Este chat já está conectado às notificações desta escola.\nUse /ajuda para ver os comandos.',
                },
            )
        else:
            _api_request(
                decifrar_token(bot),
                'sendMessage',
                {
                    'chat_id': chat_id,
                    'text': 'Para conectar este chat, peça ao administrador da escola um link de conexão válido.',
                },
            )
        return

    destino = bot.destinos.filter(chat_id=str(chat_id), ativo=True).first()
    if texto.startswith('/ajuda'):
        mensagem = (
            'ℹ️ <b>GTREP — comandos</b>\n'
            '/status — verifica a conexão\n'
            '/ajuda — mostra esta mensagem'
        )
    elif texto.startswith('/status'):
        mensagem = f'🟢 <b>Conexão ativa</b>\nEscola: {bot.escola.nome}' if destino else '🔒 Este chat ainda não está conectado a uma escola.'
    else:
        if destino:
            return
        return

    _api_request(decifrar_token(bot), 'sendMessage', {'chat_id': chat_id, 'text': mensagem})


def validar_webhook_secret(bot: TelegramBotEscola, received: str | None) -> bool:
    expected = gerar_webhook_secret(bot)
    return bool(received) and hmac.compare_digest(expected, received)
