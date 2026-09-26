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
    """Permite que o professor troque a escola ativa quando tem 2+ escolas."""
    escola = get_object_or_404(Escola, id=escola_id)
    
    # Verificar se o usuário tem acesso a esta escola
    if not hasattr(request.user, 'perfil_escola') and not hasattr(request.user, 'perfil_adm_escola'):
        messages.error(request, "Você não tem acesso a múltiplas escolas!")
        return redirect('mural')
    
    perfil = request.user.perfil_adm_escola if hasattr(request.user, 'perfil_adm_escola') else request.user.perfil_escola
    if not perfil.escolas.filter(id=escola_id).exists():
        messages.error(request, "Você não tem acesso a esta escola!")
        return redirect('mural')
    
    # Atualizar a escola ativa
    perfil.escola_ativa = escola
    perfil.save(update_fields=['escola_ativa'])
    
    messages.success(request, f"✓ Escola alterada para {escola.nome}")
    proxima_url = request.GET.get('next', '')
    if url_has_allowed_host_and_scheme(proxima_url, {request.get_host()}):
        return redirect(proxima_url)
    return redirect('mural')
