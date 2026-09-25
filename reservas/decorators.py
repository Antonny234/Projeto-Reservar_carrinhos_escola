from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def admin_escola_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # Precisa estar logado
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # Superusuário tem acesso total
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # ADM de escola
        if hasattr(request.user, 'perfil_adm') or hasattr(request.user, 'perfil_adm_escola'):
            return view_func(request, *args, **kwargs)

        # Professor normal ou professor de várias escolas
        raise PermissionDenied(
            "Você não tem permissão para acessar esta área."
        )

    return wrapper
