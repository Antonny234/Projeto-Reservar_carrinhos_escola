from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def admin_escola_required(view_func):
    """Exige que o usuário seja administrador da escola atualmente ativa."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        escola = getattr(request, "escola_ativa", None)
        if escola is None:
            raise PermissionDenied("Você não tem uma escola ativa selecionada.")

        perfil_adm = getattr(request.user, "perfil_adm", None)
        if perfil_adm is not None and perfil_adm.escola_id == escola.id:
            return view_func(request, *args, **kwargs)

        perfil_multi = getattr(request.user, "perfil_adm_escola", None)
        if perfil_multi is not None and perfil_multi.escolas.filter(pk=escola.pk).exists():
            return view_func(request, *args, **kwargs)

        raise PermissionDenied("Você não tem permissão administrativa nesta escola.")

    return wrapper


def superuser_required(view_func):
    """Garante que somente superusuários acessem a administração global."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_superuser:
            raise PermissionDenied("Apenas o Superadmin pode acessar esta área.")
        return view_func(request, *args, **kwargs)

    return wrapper
