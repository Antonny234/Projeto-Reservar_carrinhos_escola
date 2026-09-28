"""Helpers para bloqueio por falhas consecutivas de autenticação."""
from django.db import transaction
from django.utils import timezone

from .models import BloqueioLogin
from .whatsapp_utils import EmailError, enviar_link_redefinicao


MAX_TENTATIVAS_LOGIN = 5


def estado_bloqueio(usuario):
    return BloqueioLogin.objects.filter(usuario=usuario).first()


def registrar_falha_login(usuario):
    """Incrementa falhas atomicamente e informa se esta falha bloqueou a conta."""
    with transaction.atomic():
        BloqueioLogin.objects.get_or_create(usuario=usuario)
        bloqueio = BloqueioLogin.objects.select_for_update().get(usuario=usuario)
        if bloqueio.bloqueada:
            return bloqueio, False
        bloqueio.tentativas_consecutivas += 1
        bloqueou_agora = bloqueio.tentativas_consecutivas >= MAX_TENTATIVAS_LOGIN
        if bloqueou_agora:
            bloqueio.bloqueada = True
        bloqueio.save(update_fields=[
            'tentativas_consecutivas', 'bloqueada', 'atualizado_em'
        ])
        return bloqueio, bloqueou_agora


def zerar_falhas_login(usuario):
    BloqueioLogin.objects.filter(usuario=usuario).update(
        tentativas_consecutivas=0,
        email_bloqueio_enviado_em=None,
    )


def enviar_email_bloqueio(request, usuario):
    if not usuario.email:
        raise EmailError('Esta conta não possui e-mail cadastrado para recuperação.')
    horario = timezone.localtime()
    enviar_link_redefinicao(
        request, usuario, conta_bloqueada=True, horario_envio=horario
    )
    BloqueioLogin.objects.filter(usuario=usuario).update(
        email_bloqueio_enviado_em=horario
    )
    return horario
