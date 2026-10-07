# -*- coding: utf-8 -*-
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from ..models import Escola


@login_required
@require_POST
def trocar_escola_ativa(request, escola_id):
    """Define explicitamente a escola ativa do usuário."""
    escola = get_object_or_404(Escola, pk=escola_id)

    if request.user.is_superuser:
        request.session['escola_ativa_id'] = escola.pk
    else:
        perfil = getattr(request.user, 'perfil_adm_escola', None)
        if perfil is None:
            perfil = getattr(request.user, 'perfil_escola', None)
        if perfil is None or not perfil.escolas.filter(pk=escola.pk).exists():
            messages.error(request, 'Você não tem acesso a esta escola!')
            return redirect('mural')
        perfil.escola_ativa = escola
        perfil.save(update_fields=['escola_ativa'])

    messages.success(request, f'Escola alterada para {escola.nome}')
    proxima_url = request.GET.get('next', '')
    if url_has_allowed_host_and_scheme(proxima_url, {request.get_host()}):
        return redirect(proxima_url)
    return redirect('mural')