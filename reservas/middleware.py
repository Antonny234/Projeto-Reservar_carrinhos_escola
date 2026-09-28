# -*- coding: utf-8 -*-

from django.utils.deprecation import MiddlewareMixin
from .models import Escola


class EscolaMiddleware(MiddlewareMixin):

    def process_request(self, request):

        request.escola_ativa = None
        request.perfil = None

        # Usuário não está logado
        if not request.user.is_authenticated:
            return

        if request.user.is_superuser:
            request.escola_ativa = Escola.objects.first()
            return

        # ==========================================================
        # 1. ADMINISTRADOR DE UMA ESCOLA ESPECÍFICA
        # ==========================================================
        if hasattr(request.user, 'perfil_adm'):

            perfil = request.user.perfil_adm
            request.perfil = perfil

            # A escola do ADM é a escola ativa
            request.escola_ativa = perfil.escola

            return

        # ==========================================================
        # 2. PROFESSOR COM MÚLTIPLAS ESCOLAS
        # ==========================================================
        if hasattr(request.user, 'perfil_adm_escola'):
            perfil = request.user.perfil_adm_escola
            escola_ativa = perfil.escolas.filter(pk=perfil.escola_ativa_id).first() if perfil.escola_ativa_id else None
            escola_ativa = escola_ativa or perfil.escolas.first()
            if escola_ativa:
                request.perfil = perfil
                if perfil.escola_ativa_id != escola_ativa.id:
                    perfil.escola_ativa = escola_ativa
                    perfil.save(update_fields=['escola_ativa'])
                request.escola_ativa = escola_ativa
                return

        if hasattr(request.user, 'perfil_escola'):

            perfil = request.user.perfil_escola
            request.perfil = perfil

            # Já existe uma escola ativa
            if perfil.escola_ativa_id and perfil.escolas.filter(pk=perfil.escola_ativa_id).exists():

                request.escola_ativa = perfil.escola_ativa

            # Ainda não existe escola ativa
            else:

                escola = perfil.escolas.first()

                if escola:
                    perfil.escola_ativa = escola
                    perfil.save(update_fields=['escola_ativa'])
                    request.escola_ativa = escola

            return

        # ==========================================================
        # 3. PROFESSOR DE UMA ÚNICA ESCOLA
        # ==========================================================
        if hasattr(request.user, 'perfil_professor'):

            perfil = request.user.perfil_professor
            request.perfil = perfil

            request.escola_ativa = perfil.escola

            return

        # ==========================================================
        # 4. SUPERUSUÁRIO
        # ==========================================================
        if request.user.is_superuser:

            # Superusuário pode começar pela primeira escola
            request.escola_ativa = Escola.objects.first()

            return
