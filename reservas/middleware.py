# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.utils.deprecation import MiddlewareMixin


class EscolaMiddleware(MiddlewareMixin):
    """Resolve a escola ativa sem escolher uma escola implicitamente."""

    def process_request(self, request):
        request.escola_ativa = None
        request.perfil = None

        if not request.user.is_authenticated:
            return

        user = request.user
        if request.path.startswith('/trocar-escola/') or request.path == '/superadmin/':
            return

        if user.is_superuser:
            escola_id = request.session.get('escola_ativa_id')
            if escola_id:
                from .models import Escola
                request.escola_ativa = Escola.objects.filter(pk=escola_id).first()
            return

        perfil_adm = getattr(user, 'perfil_adm', None)
        if perfil_adm is not None:
            request.perfil = perfil_adm
            request.escola_ativa = perfil_adm.escola
            return

        perfil_adm_escola = getattr(user, 'perfil_adm_escola', None)
        if perfil_adm_escola is not None:
            request.perfil = perfil_adm_escola
            escola = perfil_adm_escola.escolas.filter(
                pk=perfil_adm_escola.escola_ativa_id
            ).first() if perfil_adm_escola.escola_ativa_id else None
            if escola is None:
                raise PermissionDenied('Selecione uma escola vinculada Ã  sua conta.')
            request.escola_ativa = escola
            return

        perfil_escola = getattr(user, 'perfil_escola', None)
        if perfil_escola is not None:
            request.perfil = perfil_escola
            escola = perfil_escola.escolas.filter(
                pk=perfil_escola.escola_ativa_id
            ).first() if perfil_escola.escola_ativa_id else None
            if escola is None:
                raise PermissionDenied('Selecione uma escola vinculada Ã  sua conta.')
            request.escola_ativa = escola
            return

        perfil_professor = getattr(user, 'perfil_professor', None)
        if perfil_professor is not None:
            request.perfil = perfil_professor
            request.escola_ativa = perfil_professor.escola
            return

        raise PermissionDenied('Sua conta nÃ£o estÃ¡ vinculada a uma escola.')


