from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..decorators import superuser_required
from django.core.exceptions import PermissionDenied
from ..models import Escola, PerfilAdm, PerfilProfessor, PerfilProfessorEscola, PerfilAdmEscola, User
from django.db import transaction
from django.db.models import Q
from ..forms import EscolaForm, ProatsExistentesForm, NovoProatFormSet,AdminEscolaForm


def promover_usuario_a_admin(usuario, escola):
    """Promove um usuário já vinculado à escola, preservando sua conta e reservas."""
    if PerfilAdm.objects.filter(usuario=usuario, escola=escola).exists() or PerfilAdmEscola.objects.filter(usuario=usuario, escolas=escola).exists():
        return False

    try:
        admin_unico = usuario.perfil_adm
    except PerfilAdm.DoesNotExist:
        admin_unico = None

    if admin_unico and admin_unico.escola_id != escola.id:
        admin_multi, _ = PerfilAdmEscola.objects.get_or_create(usuario=usuario)
        admin_multi.escolas.add(admin_unico.escola, escola)
        admin_multi.escola_ativa = escola
        admin_multi.save(update_fields=['escola_ativa'])
        admin_unico.delete()
    elif not admin_unico:
        PerfilAdm.objects.create(usuario=usuario, escola=escola)

    PerfilProfessor.objects.filter(usuario=usuario, escola=escola).delete()
    perfil_multi = PerfilProfessorEscola.objects.filter(usuario=usuario, escolas=escola).first()
    if perfil_multi:
        perfil_multi.escolas.remove(escola)
        if perfil_multi.escola_ativa_id == escola.id:
            perfil_multi.escola_ativa = perfil_multi.escolas.first()
            perfil_multi.save(update_fields=['escola_ativa'])
        if not perfil_multi.escolas.exists():
            perfil_multi.delete()
    return True

@superuser_required
def superadmin_painel(request):

    # ============================================================
    # SOMENTE SUPERADMIN
    # ============================================================

    # ============================================================
    # DADOS GERAIS DO SISTEMA
    # ============================================================

    escolas = Escola.objects.all().order_by('nome')

    total_escolas = Escola.objects.count()
    total_usuarios = User.objects.count()
    total_administradores = PerfilAdm.objects.count() + PerfilAdmEscola.objects.count()
    total_professores = PerfilProfessor.objects.count() + PerfilProfessorEscola.objects.count()


    # ============================================================
    # PAINEL
    # ============================================================

    contexto = {
        'escolas': escolas,
        'total_escolas': total_escolas,
        'total_usuarios': total_usuarios,
        'total_administradores': total_administradores,
        'total_professores': total_professores,
    }

    return render(
        request,
        'admin/superadmin.html',
        contexto
    )

@superuser_required
def cadastrar_escola(request):
    if request.method == 'POST':
        escola_form = EscolaForm(request.POST)
        admin_form = AdminEscolaForm(request.POST)

        # Verifica os dois formulários
        if escola_form.is_valid() and admin_form.is_valid():

            try:
                with transaction.atomic():

                    # Cria a escola
                    escola = escola_form.save()

                    # Cria o usuário administrador
                    usuario_admin = User.objects.create_user(
                        username=admin_form.cleaned_data['username'],
                        email=admin_form.cleaned_data['email'],
                        password=admin_form.cleaned_data['password'],
                    )

                    # Vincula o administrador à escola
                    PerfilAdm.objects.create(
                        usuario=usuario_admin,
                        escola=escola
                    )

                # SUCESSO
                messages.success(
                    request,
                    f"✓ Escola '{escola.nome}' criada com sucesso!"
                )

                return redirect('cadastrar_escola')

            except Exception as erro:

                # ERRO
                messages.error(request, "Não foi possível criar a escola. Revise os dados e tente novamente.")

    else:
        escola_form = EscolaForm()
        admin_form = AdminEscolaForm()

    contexto = {
        'escola_form': escola_form,
        'admin_form': admin_form,
    }

    return render(
        request,
        'admin/cadastro_escola.html',
        contexto
    )

@superuser_required
def gerenciar_escola(request, escola_id):
    escola = get_object_or_404(Escola, id=escola_id)

    # Formulário de edição dos dados básicos da escola
    if request.method == 'POST' and request.POST.get('acao') == 'editar_escola':
        escola_form = EscolaForm(request.POST, instance=escola)
        if escola_form.is_valid():
            escola_form.save()
            messages.success(request, "✓ Dados da escola atualizados com sucesso!")
            return redirect('gerenciar_escola', escola_id=escola.id)
    else:
        escola_form = EscolaForm(instance=escola)

    # Remover administrador
    if request.method == 'POST' and request.POST.get('acao') == 'remover_admin':
        adm_id = request.POST.get('adm_id')
        adm = get_object_or_404(PerfilAdm, id=adm_id, escola=escola)
        nome = adm.usuario.username
        adm.delete()
        messages.success(request, f"✓ Administrador '{nome}' removido desta escola.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    if request.method == 'POST' and request.POST.get('acao') == 'remover_admin_multiplo':
        perfil = get_object_or_404(PerfilAdmEscola, id=request.POST.get('perfil_id'), escolas=escola)
        perfil.escolas.remove(escola)
        if perfil.escola_ativa_id == escola.id:
            perfil.escola_ativa = perfil.escolas.first()
            perfil.save(update_fields=['escola_ativa'])
        if not perfil.escolas.exists():
            perfil.delete()
        messages.success(request, "Administrador removido desta escola.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    if request.method == 'POST' and request.POST.get('acao') == 'atualizar_cargo':
        tipo = request.POST.get('tipo_perfil')
        perfil_id = request.POST.get('perfil_id')
        cargo = request.POST.get('cargo')
        cargo = cargo.strip() if cargo else ''
        if not cargo:
            messages.error(request, "Informe a função do usuário.")
        elif len(cargo) > 100:
            messages.error(request, "A função deve ter no máximo 100 caracteres.")
        elif tipo == 'unico':
            perfil = get_object_or_404(PerfilProfessor, id=perfil_id, escola=escola)
            perfil.cargo = cargo
            perfil.save(update_fields=['cargo'])
            messages.success(request, f"Função de '{perfil.usuario.username}' atualizada.")
        elif tipo == 'multiplo':
            perfil = get_object_or_404(PerfilProfessorEscola, id=perfil_id, escolas=escola)
            perfil.cargo = cargo
            perfil.save(update_fields=['cargo'])
            messages.success(request, f"Função de '{perfil.usuario.username}' atualizada.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    if request.method == 'POST' and request.POST.get('acao') == 'promover_admin':
        usuario = get_object_or_404(User, id=request.POST.get('usuario_id'))
        vinculado = (
            PerfilProfessor.objects.filter(usuario=usuario, escola=escola).exists()
            or PerfilProfessorEscola.objects.filter(usuario=usuario, escolas=escola).exists()
        )
        if not vinculado:
            messages.error(request, "Este usuário não está vinculado como professor a esta escola.")
        elif promover_usuario_a_admin(usuario, escola):
            messages.success(request, f"'{usuario.username}' agora é administrador desta escola.")
        else:
            messages.info(request, f"'{usuario.username}' já é administrador desta escola.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    # Remover professor (escola única)
    if request.method == 'POST' and request.POST.get('acao') == 'remover_professor':
        prof_id = request.POST.get('prof_id')
        prof = get_object_or_404(PerfilProfessor, id=prof_id, escola=escola)
        nome = prof.usuario.username
        prof.delete()
        messages.success(request, f"✓ Professor '{nome}' removido desta escola.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    # Remover professor de múltiplas escolas (apenas desvincula desta escola)
    if request.method == 'POST' and request.POST.get('acao') == 'remover_professor_multiplo':
        perfil_id = request.POST.get('perfil_id')
        perfil = get_object_or_404(PerfilProfessorEscola, id=perfil_id)
        perfil.escolas.remove(escola)
        if perfil.escola_ativa_id == escola.id:
            perfil.escola_ativa = perfil.escolas.first()
            perfil.save(update_fields=['escola_ativa'])
        messages.success(request, f"✓ '{perfil.usuario.username}' desvinculado desta escola.")
        return redirect('gerenciar_escola', escola_id=escola.id)

    administradores = escola.administradores.select_related('usuario').all()
    administradores_multiplos = PerfilAdmEscola.objects.filter(escolas=escola).select_related('usuario').prefetch_related('escolas')
    professores = escola.professores.select_related('usuario').all()
    professores_multiplos = escola.professores_multiplos.select_related(
        'usuario__perfil_escola'
    ).all() if hasattr(escola, 'professores_multiplos') else []

    # PerfilProfessorEscola vinculados a esta escola (via M2M)
    perfis_multiplos = PerfilProfessorEscola.objects.filter(escolas=escola).select_related('usuario')

    contexto = {
        'escola': escola,
        'escola_form': escola_form,
        'administradores': administradores,
        'professores': professores,
        'perfis_multiplos': perfis_multiplos,
        'cargos_sugeridos': ['Professor', 'Coordenador(a)', 'Coordenador pedagógico', 'Diretor(a)', 'Vice-diretor(a)', 'PROAT'],
        'administradores_multiplos': administradores_multiplos,
        'total_vinculados': administradores.count() + administradores_multiplos.count() + professores.count() + perfis_multiplos.count(),
    }
    return render(request, 'admin/gerenciar_escola.html', contexto)

@superuser_required
def adicionar_administrador(request, escola_id):
    escola = get_object_or_404(Escola, id=escola_id)

    if request.method == 'POST':
        admin_form = AdminEscolaForm(request.POST)
        if admin_form.is_valid():
            usuario = User.objects.create_user(
                username=admin_form.cleaned_data['username'],
                email=admin_form.cleaned_data['email'],
                password=admin_form.cleaned_data['password'],
            )
            PerfilAdm.objects.create(usuario=usuario, escola=escola)
            messages.success(request, f"✓ Administrador '{usuario.username}' cadastrado com sucesso!")
            return redirect('gerenciar_escola', escola_id=escola.id)
    else:
        admin_form = AdminEscolaForm()

    contexto = {
        'escola': escola,
        'admin_form': admin_form,
    }
    return render(request, 'admin/adicionar_administrador.html', contexto)

@superuser_required
def listar_escolas(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas o Superadmin pode acessar este painel.")

    escolas = Escola.objects.all().order_by('nome')

    return render(request, 'admin/listar_escolas.html', {'escolas': escolas})


@superuser_required
def listar_usuarios(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas o Superadmin pode acessar este painel.")

    escolas = Escola.objects.all().order_by('nome')
    escola_id = request.GET.get('escola')
    escola_selecionada = None

    usuarios = User.objects.all().select_related(
        'perfil_adm__escola',
        'perfil_professor__escola',
    ).prefetch_related(
        'perfil_escola__escolas',
        'perfil_adm_escola__escolas',
    ).order_by('username')

    if escola_id:
        escola_selecionada = get_object_or_404(Escola, id=escola_id)
        usuarios = usuarios.filter(
            Q(perfil_adm__escola_id=escola_id) |
            Q(perfil_adm_escola__escolas__id=escola_id) |
            Q(perfil_professor__escola_id=escola_id) |
            Q(perfil_escola__escolas__id=escola_id)
        ).distinct()

    return render(request, 'admin/listar_usuarios.html', {'usuarios': usuarios, 'escolas': escolas,
        'escola_selecionada': escola_selecionada,})


@superuser_required
def listar_administradores(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas o Superadmin pode acessar este painel.")
    escolas = Escola.objects.all().order_by('nome')
    escola_id = request.GET.get('escola')
    escola_selecionada = None

    administradores_unicos = PerfilAdm.objects.select_related('usuario', 'escola').order_by('usuario__username')
    administradores_multiplos = PerfilAdmEscola.objects.select_related('usuario').prefetch_related('escolas').order_by('usuario__username')

    if escola_id:
        escola_selecionada = get_object_or_404(Escola, id=escola_id)
        administradores_unicos = administradores_unicos.filter(escola_id=escola_id)
        administradores_multiplos = administradores_multiplos.filter(escolas__id=escola_id).distinct()

    return render(request, 'admin/listar_administradores.html', {
        'administradores_unicos': administradores_unicos,
        'administradores_multiplos': administradores_multiplos,
        'escolas': escolas,
        'escola_selecionada': escola_selecionada,})


@superuser_required
def listar_professores(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas o Superadmin pode acessar este painel.")

    escolas = Escola.objects.all().order_by('nome')
    escola_id = request.GET.get('escola')
    escola_selecionada = None

    professores_unicos = PerfilProfessor.objects.select_related('usuario', 'escola').order_by('usuario__username')
    professores_multiplos = PerfilProfessorEscola.objects.select_related('usuario').prefetch_related('escolas').order_by('usuario__username')

    if escola_id:
        escola_selecionada = get_object_or_404(Escola, id=escola_id)
        professores_unicos = professores_unicos.filter(escola_id=escola_id)
        professores_multiplos = professores_multiplos.filter(escolas__id=escola_id).distinct()


    return render(request, 'admin/listar_professores.html', {
        'professores_unicos': professores_unicos,
        'professores_multiplos': professores_multiplos,
        'escolas': escolas,
        'escola_selecionada': escola_selecionada,
    })


