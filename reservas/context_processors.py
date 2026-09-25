def escola_context(request):
    """Adiciona informações da escola ao contexto de todos os templates.
    Verifica se o usuário tem múltiplas escolas e passa a variável mostra_seletor_escola."""
    
    context = {
        'escola_ativa': None,
        'escolas_usuario': [],
        'mostra_seletor_escola': False,
        'usuario_eh_admin': False,
    }

    if request.user.is_authenticated:
        # Administrador de escola não precisa ser staff do Django Admin.
        context['usuario_eh_admin'] = request.user.is_superuser or hasattr(request.user, 'perfil_adm') or hasattr(request.user, 'perfil_adm_escola')
        if hasattr(request.user, 'perfil_adm_escola'):
            perfil = request.user.perfil_adm_escola
            escolas = list(perfil.escolas.values('id', 'nome'))
            context['escolas_usuario'] = escolas
            context['escola_ativa'] = perfil.escola_ativa
            context['mostra_seletor_escola'] = len(escolas) > 1
        elif hasattr(request.user, 'perfil_adm'):
            context['escola_ativa'] = request.user.perfil_adm.escola
        # 🔑 VERIFICAR SE TEM PERFIL MULTI-ESCOLA
        elif hasattr(request.user, 'perfil_escola'):
            perfil = request.user.perfil_escola
            escolas = list(perfil.escolas.values('id', 'nome'))
            context['escolas_usuario'] = escolas
            context['escola_ativa'] = perfil.escola_ativa
            
            # 🎯 MOSTRAR SELETOR APENAS SE TEM 2+ ESCOLAS
            context['mostra_seletor_escola'] = len(escolas) > 1
        
        # Se tem perfil simples (1 escola), mostrar apenas a escola
        elif hasattr(request.user, 'perfil_professor'):
            context['escola_ativa'] = request.user.perfil_professor.escola

    return context
