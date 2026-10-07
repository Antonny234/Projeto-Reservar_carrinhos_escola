from django.shortcuts import render


def erro_aplicacao(request, titulo, mensagem, status, botao_texto='Voltar ao início', botao_url='/'):
    return render(request, 'erro_aplicacao.html', {
        'titulo': titulo,
        'mensagem': mensagem,
        'botao_texto': botao_texto,
        'botao_url': botao_url,
    }, status=status)


def handler403(request, exception=None):
    if not request.user.is_authenticated:
        return erro_aplicacao(
            request,
            'Ação proibida',
            'Você precisa fazer login antes de acessar esta página.',
            403,
            'Fazer login',
            '/entrar/',
        )
    return erro_aplicacao(
        request,
        'Acesso não permitido',
        'Sua conta não tem permissão para acessar esta página.',
        403,
    )


def handler404(request, exception=None):
    return erro_aplicacao(
        request,
        'Página não encontrada',
        'O endereço pode estar incorreto ou a página não existe mais.',
        404,
    )


def handler500(request):
    return erro_aplicacao(
        request,
        'Algo deu errado',
        'Ocorreu um erro inesperado. Tente novamente em instantes.',
        500,
    )


def csrf_failure(request, reason=''):
    return erro_aplicacao(
        request,
        'Sua sessão precisa ser atualizada',
        'Atualize esta página. Depois, volte ao login e tente novamente para renovar sua sessão.',
        403,
        'Ir para o login',
        '/entrar/',
    )
