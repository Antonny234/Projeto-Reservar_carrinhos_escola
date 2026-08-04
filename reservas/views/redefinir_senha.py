# -*- coding: utf-8 -*-
"""Fluxo de redefinição de senha por e-mail (link)."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from ..email_utils import enviar_link_redefinicao, EmailError


def redefinir_senha_usuario(request):
    """Etapa 1 — digita o usuário e envia o link por e-mail."""
    if request.method == "POST":
        usuario = request.POST.get('usuario', '').strip()

        if not usuario:
            messages.error(request, "Informe o seu usuário.")
            return render(request, 'redefinir_senha_usuario.html')

        user = User.objects.filter(username=usuario).first()
        if not user:
            # Mensagem genérica por segurança (não revela se o usuário existe)
            messages.success(request, "Se o usuário existir, enviamos um link para o e-mail cadastrado.")
            return redirect('longa')

        if not user.email:
            messages.error(request, "Esta conta não possui e-mail cadastrado.")
            return render(request, 'redefinir_senha_usuario.html')

        try:
            enviar_link_redefinicao(request, user)
            messages.success(
                request,
                "Enviamos um link de redefinição para o e-mail cadastrado. Verifique sua caixa de entrada."
            )
        except EmailError as e:
            messages.error(request, str(e))
            return render(request, 'redefinir_senha_usuario.html')

        return redirect('longa')

    return render(request, 'redefinir_senha_usuario.html')


def redefinir_senha_confirmar(request, uidb64, token):
    """Etapa 2 — o usuário clica no link e define a nova senha."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Link inválido ou expirado. Solicite uma nova redefinição.")
        return redirect('redefinir_senha_usuario')

    if request.method == "POST":
        senha = request.POST.get('senha', '')
        confirmar = request.POST.get('confirmar_senha', '')

        if not senha or not confirmar:
            messages.error(request, "Preencha todos os campos.")
            return render(request, 'redefinir_senha_nova.html', {'uidb64': uidb64, 'token': token})

        if senha != confirmar:
            messages.error(request, "As senhas não coincidem!")
            return render(request, 'redefinir_senha_nova.html', {'uidb64': uidb64, 'token': token})

        if len(senha) < 8:
            messages.error(request, "A senha deve ter pelo menos 8 caracteres.")
            return render(request, 'redefinir_senha_nova.html', {'uidb64': uidb64, 'token': token})

        user.set_password(senha)
        user.save()

        messages.success(request, "Senha redefinida com sucesso! Faça login.")
        return redirect('longa')

    return render(request, 'redefinir_senha_nova.html', {'uidb64': uidb64, 'token': token})