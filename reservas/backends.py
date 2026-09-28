"""Backend Django com bloqueio após cinco erros consecutivos de senha."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .login_security import (
    estado_bloqueio,
    registrar_falha_login,
    zerar_falhas_login,
    enviar_email_bloqueio,
)
from .whatsapp_utils import EmailError


class BloqueioBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if username is None or password is None:
            return None

        UserModel = get_user_model()
        try:
            usuario = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Mantém custo de hash semelhante para nomes inexistentes.
            UserModel().set_password(password)
            return None

        bloqueio = estado_bloqueio(usuario)
        if bloqueio and bloqueio.bloqueada:
            if request is not None:
                request.login_account_locked = True
            return None

        if usuario.check_password(password):
            if self.user_can_authenticate(usuario):
                zerar_falhas_login(usuario)
                return usuario
            return None

        bloqueio, bloqueou_agora = registrar_falha_login(usuario)
        if bloqueou_agora and request is not None:
            request.login_account_locked = True
            try:
                request.login_lock_email_sent_at = enviar_email_bloqueio(request, usuario)
            except EmailError:
                request.login_lock_email_failed = True
        return None
