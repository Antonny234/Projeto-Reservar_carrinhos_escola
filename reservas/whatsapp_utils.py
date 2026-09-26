# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging
import os
import resend

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Erro ao tentar enviar e-mail."""


def enviar_codigo_email(email: str, codigo: str) -> bool:
    """Envia o código de verificação de 4 dígitos por e-mail via Resend."""
    resend.api_key = os.environ.get("RESEND_API_KEY")
    if not resend.api_key or not settings.DEFAULT_FROM_EMAIL:
        logger.warning("RESEND_API_KEY ou DEFAULT_FROM_EMAIL não configurados.")
        raise EmailError("Envio de e-mail não está configurado no servidor.")

    assunto = "Código de verificação - Cadastro"
    mensagem = (
        f"Olá!\n\n"
        f"Seu código de verificação é: {codigo}\n\n"
        f"Este código é válido por 15 minutos.\n\n"
        f"Se você não solicitou este código, ignore este e-mail."
    )

    try:
        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email],
            "subject": assunto,
            "text": mensagem,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.exception("Falha ao enviar e-mail de código")
        raise EmailError("Não foi possível enviar o e-mail agora. Tente novamente.") from e


def enviar_link_redefinicao(request, user) -> bool:
    """Gera e envia o link de redefinição de senha por e-mail via Resend."""
    resend.api_key = os.environ.get("RESEND_API_KEY")
    if not resend.api_key or not settings.DEFAULT_FROM_EMAIL:
        raise EmailError("Envio de e-mail não está configurado no servidor.")

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Monta o link absoluto
    caminho = reverse('redefinir_senha_confirmar', kwargs={'uidb64': uid, 'token': token})
    link = request.build_absolute_uri(caminho)

    assunto = "Redefinição de senha"
    mensagem = (
        f"Olá {user.username},\n\n"
        f"Você solicitou a redefinição de senha.\n\n"
        f"Clique no link abaixo para criar uma nova senha:\n"
        f"{link}\n\n"
        f"Este link é válido por algumas horas.\n"
        f"Se você não solicitou isso, ignore este e-mail."
    )

    try:
        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [user.email],
            "subject": assunto,
            "text": mensagem,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.exception("Falha ao enviar e-mail de redefinição")
        raise EmailError("Não foi possível enviar o e-mail agora. Tente novamente.") from e