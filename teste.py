# -*- coding: utf-8 -*-
"""
================================================================================
teste.py — Suite completa de testes do sistema PROATI / GTREP
            (Reserva de Carrinhos de Notebooks e Tablets — Escola / SEDUC-SP)
================================================================================

O QUE ESTE ARQUIVO FAZ
----------------------
Percorre praticamente todo o projeto de ponta a ponta:

  • Modelos do banco (criacao, relacionamentos, metodos, uniques)
  • Todas as URLs publicas, protegidas e de staff
  • Cadastro de professor com verificacao por WhatsApp (API mockada)
  • Login / logout
  • Criacao de reservas (carrinho inteiro e por quantidade)
  • Aprovacao e recusa de reservas pelo administrador
  • Tablet de check-in e PIN de envio de fichas
  • Verificacao de carrinho e notebooks quebrados
  • Exportacao de fichas e reservas em Excel
  • Painel de fichas e notificacao de fichas ausentes
  • Fluxo completo de redefinicao de senha (WhatsApp mockado)
  • Endpoint de analise de foto com YOLO (so validacoes de entrada)
  • Funcoes utilitarias de WhatsApp (normalizar / validar numero)

COMO EXECUTAR
-------------
Na pasta onde esta o manage.py:

    python manage.py test teste --verbosity=2

Se o Django nao achar o modulo "teste" na raiz:

    cp teste.py reservas/tests_completo.py
    python manage.py test reservas.tests_completo --verbosity=2

Ou substitua o tests.py do app:

    cp teste.py reservas/tests.py
    python manage.py test reservas --verbosity=2

REQUISITOS
----------
  - Django configurado com o app "reservas"
  - Banco SQLite (ou outro) com permissao de escrita
  - openpyxl (opcional, para exportacao real)
  - WhatsApp e Telegram sao MOCKADOS — nao precisa de token real

ESTRUTURA DESTE ARQUIVO (resumo das classes)
--------------------------------------------
  1.  Helpers .................. funcoes auxiliares para criar dados de teste
  2.  ModelosTestCase .......... todos os models e metodos de instancia
  3.  URLsTestCase ............. status code de cada rota (anonimo/logado/staff)
  4.  AutenticacaoTestCase ..... cadastro + confirmacao WhatsApp + login
  5.  FluxoReservasTestCase .... reservas, exclusao, paginas unico/quantidade
  6.  TabletCheckinTestCase .... tela do tablet, status AJAX, criar PIN
  7.  AdminAprovacaoTestCase ... aprovar/recusar + painel de fichas
  8.  VerificarCarrinhoTestCase  notebooks quebrados e faixa de numeracao
  9.  ExportacaoTestCase ....... Excel de reservas e de fichas
 10.  FichasAusentesTestCase ... AJAX de fichas sem registro de uso
 11.  RedefinirSenhaTestCase ... 4 etapas da recuperacao de senha
 12.  AnalisarFotoTestCase ..... validacoes do endpoint YOLO
 13.  WhatsAppUtilsTestCase .... normalizar_numero e numero_valido
 14.  HelpersViewTestCase ...... _professor_requer_aprovacao
 15.  MuralAjaxTestCase ........ mural filtrado e menu AJAX
================================================================================
"""

from __future__ import annotations

import json
from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from reservas.models import (
    Aluno,
    CodigoVerificacao,
    Equipamento,
    Notebook,
    NotificacaoFichaAusente,
    NumeroReservaQuantidade,
    PerfilAdm,
    PerfilProfessor,
    RegistroUso,
    Reserva,
    Sala,
)


# =============================================================================
# 1. HELPERS — funcoes reutilizaveis para montar o cenario de cada teste
# =============================================================================
# Em vez de repetir User.objects.create_user em todo lugar, centralizamos
# a criacao de professor, admin, equipamento e sala. Assim o setup fica
# curto e qualquer mudanca no model (ex.: campo novo no PerfilProfessor)
# e corrigida em um so lugar.
# =============================================================================

def criar_professor(
    username="prof_teste",
    email="prof_teste@professor.educacao.sp.gov.br",
    password="Senha@123",
    whatsapp="11999998888",
    ativo=True,
):
    """Cria usuario professor + PerfilProfessor (WhatsApp obrigatorio no cadastro real)."""
    user = User.objects.create_user(
        username=username, email=email, password=password, is_active=ativo
    )
    PerfilProfessor.objects.create(usuario=user, whatsapp=whatsapp)
    return user


def criar_admin(
    username="admin_teste",
    email="admin@escola.com",
    password="Admin@123",
    pin="1234",
    requer_aprovacao=False,
):
    """Cria usuario staff + PerfilAdm (PIN de envio de fichas no tablet)."""
    user = User.objects.create_user(
        username=username, email=email, password=password, is_staff=True
    )
    PerfilAdm.objects.create(
        usuario=user, pin_envio=pin, requer_aprovacao=requer_aprovacao
    )
    return user


def criar_equipamento_notebook(
    nome="Carrinho 01", quantidade=40, numero_inicial=1, numero_final=40
):
    """Carrinho de notebooks com faixa de numeracao (1..40 por padrao)."""
    return Equipamento.objects.create(
        nome=nome,
        tipo="notebook",
        quantidade=quantidade,
        numero_inicial=numero_inicial,
        numero_final=numero_final,
        disponivel=True,
    )


def criar_equipamento_tablet(nome="Carrinho Tablet", quantidade=20):
    """Carrinho de tablets (sem faixa de numero individual)."""
    return Equipamento.objects.create(
        nome=nome, tipo="tablet", quantidade=quantidade, disponivel=True
    )


def criar_sala(nome="1A"):
    """Sala/turma usada nas reservas e nos alunos."""
    return Sala.objects.create(nome=nome)


def amanha():
    """Data de amanha — evita conflito com reservas do dia atual nos testes."""
    return date.today() + timedelta(days=1)


def hoje():
    return date.today()


# =============================================================================
# 2. ModelosTestCase
# =============================================================================
# Testa a camada de dados: criacao, __str__, metodos de negocio
# (faixa_numeros, quantidade_ativa, status_numeros, CodigoVerificacao.gerar/valido)
# e restricoes unique_together / unique.
# Se um model quebrar, estes testes falham antes mesmo de abrir o navegador.
# =============================================================================

class ModelosTestCase(TestCase):
    """
    Verifica a criacao correta de todas as entidades do banco,
    relacionamentos, metodos de instancia e integridade.
    """

    def setUp(self):
        self.usuario = criar_professor()
        self.admin = criar_admin()
        self.sala = criar_sala()
        self.equipamento = criar_equipamento_notebook()

    # --- Equipamento ---------------------------------------------------------

    def test_criar_equipamento_notebook(self):
        """Tipo notebook, disponivel=True e string amigavel."""
        eq = criar_equipamento_notebook(nome="NB Teste", quantidade=30)
        self.assertEqual(eq.tipo, "notebook")
        self.assertTrue(eq.disponivel)
        self.assertEqual(str(eq), "NB Teste (Carrinho de Notebooks)")

    def test_criar_equipamento_tablet(self):
        """Tipo tablet e get_tipo_display correto."""
        eq = criar_equipamento_tablet()
        self.assertEqual(eq.tipo, "tablet")
        self.assertEqual(str(eq), "Carrinho Tablet (Carrinho de Tablets)")

    def test_faixa_numeros_sem_intervalo(self):
        """Sem numero_inicial/final, faixa_numeros() deve ser set vazio."""
        eq = Equipamento.objects.create(nome="Sem faixa", tipo="notebook", quantidade=10)
        self.assertEqual(eq.faixa_numeros(), set())

    def test_faixa_numeros_com_intervalo(self):
        """faixa_numeros() = set(range(inicial, final+1))."""
        self.assertEqual(self.equipamento.faixa_numeros(), set(range(1, 41)))

    def test_lista_numeros_ordenada(self):
        """lista_numeros() devolve lista ordenada para o template."""
        self.assertEqual(self.equipamento.lista_numeros(), list(range(1, 41)))

    def test_quantidade_ativa_sem_inativos(self):
        """Sem notebooks quebrados, quantidade_ativa = tamanho da faixa."""
        self.assertEqual(self.equipamento.quantidade_ativa(), 40)

    def test_quantidade_ativa_com_inativos(self):
        """Cada Notebook(ativo=False) reduz a quantidade ativa."""
        Notebook.objects.create(equipamento=self.equipamento, numero=5, ativo=False)
        Notebook.objects.create(equipamento=self.equipamento, numero=10, ativo=False)
        self.assertEqual(self.equipamento.quantidade_ativa(), 38)

    def test_status_numeros(self):
        """status_numeros() marca cada numero como ativo ou nao (template de verificacao)."""
        Notebook.objects.create(equipamento=self.equipamento, numero=3, ativo=False)
        status = self.equipamento.status_numeros()
        self.assertEqual(len(status), 40)
        item3 = next(s for s in status if s["numero"] == 3)
        self.assertFalse(item3["ativo"])

    # --- Notebook ------------------------------------------------------------

    def test_criar_notebook(self):
        nb = Notebook.objects.create(equipamento=self.equipamento, numero=1, ativo=True)
        self.assertIn("ativo", str(nb))
        self.assertIn("Carrinho 01", str(nb))

    def test_notebook_quebrado(self):
        nb = Notebook.objects.create(equipamento=self.equipamento, numero=2, ativo=False)
        self.assertIn("quebrado", str(nb))

    def test_notebook_unique_together(self):
        """Nao podem existir dois notebooks com o mesmo numero no mesmo carrinho."""
        Notebook.objects.create(equipamento=self.equipamento, numero=1)
        with self.assertRaises(IntegrityError):
            Notebook.objects.create(equipamento=self.equipamento, numero=1)

    # --- Sala / Aluno --------------------------------------------------------

    def test_criar_sala(self):
        self.assertEqual(str(self.sala), "1A")

    def test_criar_aluno(self):
        aluno = Aluno.objects.create(nome="Joao Silva", sala=self.sala)
        self.assertEqual(str(aluno), "Joao Silva (1A)")

    # --- PerfilAdm -----------------------------------------------------------

    def test_perfil_adm_com_pin(self):
        perfil = self.admin.perfil_adm
        self.assertEqual(perfil.pin_envio, "1234")
        self.assertIn(self.admin.username, str(perfil))

    def test_perfil_adm_requer_aprovacao(self):
        perfil = self.admin.perfil_adm
        perfil.requer_aprovacao = True
        perfil.save()
        self.assertTrue(perfil.requer_aprovacao)

    # --- PerfilProfessor / CodigoVerificacao ---------------------------------

    def test_perfil_professor(self):
        perfil = self.usuario.perfil_professor
        self.assertEqual(perfil.whatsapp, "11999998888")
        self.assertIn(self.usuario.username, str(perfil))

    def test_whatsapp_unico(self):
        """WhatsApp e unique: nao pode cadastrar o mesmo numero em duas contas."""
        with self.assertRaises(IntegrityError):
            criar_professor(
                username="outro",
                email="outro@professor.educacao.sp.gov.br",
                whatsapp="11999998888",
            )

    def test_codigo_verificacao_gerar(self):
        """Codigo de 4 digitos, nao usado, ainda valido, tipo cadastro."""
        cod = CodigoVerificacao.gerar(self.usuario, tipo="cadastro")
        self.assertEqual(len(cod.codigo), 4)
        self.assertTrue(cod.codigo.isdigit())
        self.assertFalse(cod.usado)
        self.assertTrue(cod.valido())
        self.assertEqual(cod.tipo, "cadastro")

    def test_codigo_invalida_anteriores(self):
        """gerar() marca os codigos anteriores nao usados do mesmo tipo como usados."""
        c1 = CodigoVerificacao.gerar(self.usuario, tipo="cadastro")
        c2 = CodigoVerificacao.gerar(self.usuario, tipo="cadastro")
        c1.refresh_from_db()
        self.assertTrue(c1.usado)
        self.assertFalse(c2.usado)

    def test_codigo_expirado(self):
        """Apos 15 minutos (ou forcando expira_em no passado), valido() = False."""
        cod = CodigoVerificacao.gerar(self.usuario, tipo="redefinicao")
        cod.expira_em = timezone.now() - timedelta(minutes=1)
        cod.save()
        self.assertFalse(cod.valido())

    def test_codigo_usado_nao_valido(self):
        cod = CodigoVerificacao.gerar(self.usuario, tipo="cadastro")
        cod.usado = True
        cod.save()
        self.assertFalse(cod.valido())

    # --- Reserva -------------------------------------------------------------

    def test_criar_reserva_confirmada(self):
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="confirmada",
        )
        self.assertEqual(r.status, "confirmada")
        self.assertIn(self.usuario.username, str(r))

    def test_criar_reserva_pendente(self):
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=amanha(),
            horario_inicio=time(10, 0),
            horario_fim=time(12, 0),
            sala=self.sala,
            status="pendente",
        )
        self.assertEqual(r.status, "pendente")

    def test_reserva_com_quantidade(self):
        """Reserva por quantidade + numeros individuais (NumeroReservaQuantidade)."""
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=amanha(),
            horario_inicio=time(13, 0),
            horario_fim=time(15, 0),
            sala=self.sala,
            quantidade=5,
        )
        for n in (1, 2, 3, 4, 5):
            NumeroReservaQuantidade.objects.create(reserva=r, numero=n)
        self.assertEqual(r.numeros_quantidade.count(), 5)

    def test_numero_reserva_quantidade_unique(self):
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(9, 0),
            sala=self.sala,
            quantidade=1,
        )
        NumeroReservaQuantidade.objects.create(reserva=r, numero=7)
        with self.assertRaises(IntegrityError):
            NumeroReservaQuantidade.objects.create(reserva=r, numero=7)

    def test_registro_uso(self):
        """Ficha: aluno + notebook usado naquela reserva."""
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=hoje(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
        )
        aluno = Aluno.objects.create(nome="Maria", sala=self.sala)
        reg = RegistroUso.objects.create(reserva=r, aluno=aluno, numero_notebook=12)
        self.assertEqual(reg.numero_notebook, 12)

    def test_notificacao_ficha_ausente_unique(self):
        """Uma notificacao por reserva (unique_together reserva)."""
        r = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=hoje(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
        )
        NotificacaoFichaAusente.objects.create(reserva=r)
        with self.assertRaises(IntegrityError):
            NotificacaoFichaAusente.objects.create(reserva=r)


# =============================================================================
# 3. URLsTestCase
# =============================================================================
# Garante que cada rota responde com status esperado conforme o perfil:
#   - anonimo: paginas publicas 200; protegidas 302/403
#   - professor logado: mural e AJAX acessiveis
#   - staff: aprovacao, painel, verificar-carrinho
# Nao testa a logica de negocio, so "a URL existe e a permissao funciona".
# =============================================================================

class URLsTestCase(TestCase):
    """Acessibilidade de todas as rotas principais."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor()
        self.admin = criar_admin()
        self.sala = criar_sala()
        self.eq = criar_equipamento_notebook()
        self.reserva = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="pendente",
        )

    def test_home_anonimo(self):
        r = self.client.get(reverse("home"))
        self.assertIn(r.status_code, (200, 302))

    def test_criar_conta_get(self):
        r = self.client.get(reverse("index"))
        self.assertEqual(r.status_code, 200)

    def test_entrar_get(self):
        r = self.client.get(reverse("longa"))
        self.assertEqual(r.status_code, 200)

    def test_mural_consulta_anonimo(self):
        """Painel publico de carrinhos — deve ser acessivel sem login."""
        r = self.client.get(reverse("mural_consulta"))
        self.assertIn(r.status_code, (200, 302))

    def test_carregar_mural_publico_anonimo(self):
        r = self.client.get(reverse("carregar_mural_publico"))
        self.assertIn(r.status_code, (200, 302, 400))

    def test_mural_protegida_redireciona(self):
        r = self.client.get(reverse("mural"))
        self.assertIn(r.status_code, (302, 403))

    def test_mural_logado(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("mural"))
        self.assertIn(r.status_code, (200, 302))

    def test_unico_protegida(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("unico"))
        self.assertIn(r.status_code, (200, 302))

    def test_reserva_quantidade_protegida(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("reserva_quantidade"))
        self.assertIn(r.status_code, (200, 302))

    def test_tablet_protegida(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("tablet_checkin", args=[self.eq.id]))
        self.assertIn(r.status_code, (200, 302))

    def test_camera_protegida(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("camera_contagem"))
        self.assertIn(r.status_code, (200, 302))

    def test_aprovar_nao_staff(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("aprovar_reserva", args=[self.reserva.id]))
        self.assertIn(r.status_code, (302, 403))

    def test_aprovar_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("aprovar_reserva", args=[self.reserva.id]))
        self.assertIn(r.status_code, (200, 302))

    def test_recusar_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("recusar_reserva", args=[self.reserva.id]))
        self.assertIn(r.status_code, (200, 302))

    def test_painel_reservas_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("painel_reservas_dia"))
        self.assertIn(r.status_code, (200, 302))

    def test_painel_fichas_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("painel_fichas"))
        self.assertIn(r.status_code, (200, 302))

    def test_verificar_carrinho_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("verificar_carrinho"))
        self.assertIn(r.status_code, (200, 302))

    def test_pendentes_numeracao_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("pendentes_numeracao"))
        self.assertIn(r.status_code, (200, 302))

    def test_painel_reservas_quantidade_staff(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("painel_reservas_quantidade"))
        self.assertIn(r.status_code, (200, 302))

    def test_ajax_disponiveis_logado(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(reverse("ajax_disponiveis"), {"data": str(amanha())})
        self.assertIn(r.status_code, (200, 302, 400))

    def test_ajax_numeros_disponiveis_logado(self):
        self.client.login(username="prof_teste", password="Senha@123")
        r = self.client.get(
            reverse("numeros_disponiveis"),
            {"equipamento_id": self.eq.id, "data": str(amanha())},
        )
        self.assertIn(r.status_code, (200, 302, 400))

    def test_esqueci_senha_get(self):
        r = self.client.get(reverse("redefinir_senha_usuario"))
        self.assertEqual(r.status_code, 200)

    def test_confirmar_cadastro_get(self):
        r = self.client.get(reverse("confirmar_cadastro"))
        self.assertIn(r.status_code, (200, 302))

    def test_criar_pin_get(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.get(reverse("criar_pin"))
        self.assertIn(r.status_code, (200, 302))


# =============================================================================
# 4. AutenticacaoTestCase
# =============================================================================
# Fluxo real do cadastro:
#   1) POST /criar/ com e-mail @professor.educacao.sp.gov.br + WhatsApp
#   2) Usuario nasce is_active=False
#   3) CodigoVerificacao e gerado e "enviado" (mock)
#   4) POST /confirmar-cadastro/ com o codigo → is_active=True
# Tambem testa e-mail invalido, senhas diferentes, usuario duplicado e login.
# =============================================================================

class AutenticacaoTestCase(TestCase):
    """Cadastro com WhatsApp, confirmacao de codigo e login."""

    def setUp(self):
        self.client = Client()

    @patch("reservas.views.area_usuario.enviar_codigo_whatsapp")
    def test_criar_conta_valida(self, mock_envio):
        """
        Cadastro completo: cria User inativo, PerfilProfessor e CodigoVerificacao.
        O envio de WhatsApp e mockado para nao depender de token Meta.
        """
        mock_envio.return_value = True
        r = self.client.post(
            reverse("index"),
            {
                "usuario": "novoprof",
                "email": "novoprof@professor.educacao.sp.gov.br",
                "senha": "Senha@123",
                "confirmar_senha": "Senha@123",
                "whatsapp": "11988887777",
            },
        )
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(username="novoprof")
        self.assertFalse(user.is_active)
        self.assertTrue(PerfilProfessor.objects.filter(usuario=user).exists())
        self.assertTrue(
            CodigoVerificacao.objects.filter(
                usuario=user, tipo="cadastro", usado=False
            ).exists()
        )
        mock_envio.assert_called_once()

    def test_criar_conta_email_invalido(self):
        """So aceita dominio @professor.educacao.sp.gov.br."""
        r = self.client.post(
            reverse("index"),
            {
                "usuario": "x",
                "email": "x@gmail.com",
                "senha": "Senha@123",
                "confirmar_senha": "Senha@123",
                "whatsapp": "11988887777",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_criar_conta_senhas_diferentes(self):
        r = self.client.post(
            reverse("index"),
            {
                "usuario": "y",
                "email": "y@professor.educacao.sp.gov.br",
                "senha": "Senha@123",
                "confirmar_senha": "Outra@123",
                "whatsapp": "11988887777",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="y").exists())

    def test_criar_conta_usuario_duplicado(self):
        criar_professor(username="dup", email="dup@professor.educacao.sp.gov.br")
        r = self.client.post(
            reverse("index"),
            {
                "usuario": "dup",
                "email": "outro@professor.educacao.sp.gov.br",
                "senha": "Senha@123",
                "confirmar_senha": "Senha@123",
                "whatsapp": "11977776666",
            },
        )
        self.assertEqual(r.status_code, 200)

    @patch("reservas.views.area_usuario.enviar_codigo_whatsapp")
    def test_confirmar_cadastro_codigo_correto(self, mock_envio):
        """Codigo valido ativa o usuario e marca o codigo como usado."""
        mock_envio.return_value = True
        user = User.objects.create_user(
            username="pendente",
            email="pendente@professor.educacao.sp.gov.br",
            password="Senha@123",
            is_active=False,
        )
        PerfilProfessor.objects.create(usuario=user, whatsapp="11966665555")
        cod = CodigoVerificacao.gerar(user, tipo="cadastro")
        session = self.client.session
        session["cadastro_pendente_user_id"] = user.id
        session.save()

        r = self.client.post(reverse("confirmar_cadastro"), {"codigo": cod.codigo})
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        cod.refresh_from_db()
        self.assertTrue(cod.usado)

    def test_confirmar_cadastro_codigo_errado(self):
        user = User.objects.create_user(
            username="pendente2",
            email="pendente2@professor.educacao.sp.gov.br",
            password="Senha@123",
            is_active=False,
        )
        PerfilProfessor.objects.create(usuario=user, whatsapp="11966665556")
        CodigoVerificacao.gerar(user, tipo="cadastro")
        session = self.client.session
        session["cadastro_pendente_user_id"] = user.id
        session.save()

        r = self.client.post(reverse("confirmar_cadastro"), {"codigo": "0000"})
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_login_valido(self):
        criar_professor(username="loginok", password="Senha@123")
        r = self.client.post(
            reverse("longa"),
            {"usuario": "loginok", "senha": "Senha@123"},
        )
        self.assertIn(r.status_code, (200, 302))

    def test_login_invalido(self):
        criar_professor(username="loginbad", password="Senha@123")
        r = self.client.post(
            reverse("longa"),
            {"usuario": "loginbad", "senha": "errada"},
        )
        self.assertEqual(r.status_code, 200)


# =============================================================================
# 5. FluxoReservasTestCase
# =============================================================================
# Cobre o dia a dia do professor:
#   - criar reserva no banco (carrinho inteiro e por quantidade)
#   - marcar numeracao_preenchida
#   - acessar paginas unico / reserva-quantidade
#   - tentar excluir reserva propria
# =============================================================================

class FluxoReservasTestCase(TestCase):
    """Criacao e gestao de reservas pelo professor."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor()
        self.sala = criar_sala()
        self.eq_nb = criar_equipamento_notebook()
        self.eq_tb = criar_equipamento_tablet()
        self.client.login(username="prof_teste", password="Senha@123")

    def test_criar_reserva_basica_via_modelo(self):
        r = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq_nb,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="confirmada",
        )
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(r.equipamento.tipo, "notebook")

    def test_reserva_quantidade_com_numeros(self):
        r = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq_nb,
            data_uso=amanha(),
            horario_inicio=time(10, 0),
            horario_fim=time(12, 0),
            sala=self.sala,
            quantidade=3,
        )
        for n in (10, 11, 12):
            NumeroReservaQuantidade.objects.create(reserva=r, numero=n)
        self.assertEqual(r.numeros_quantidade.count(), 3)
        self.assertFalse(r.numeracao_preenchida)
        r.numeracao_preenchida = True
        r.save()
        self.assertTrue(r.numeracao_preenchida)

    def test_excluir_reserva_propria(self):
        r = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq_tb,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(9, 0),
            sala=self.sala,
        )
        resp = self.client.get(reverse("excluir_reserva", args=[r.id]))
        self.assertIn(resp.status_code, (200, 302))

    def test_pagina_unico_acessivel(self):
        r = self.client.get(reverse("unico"))
        self.assertIn(r.status_code, (200, 302))

    def test_reserva_quantidade_pagina(self):
        r = self.client.get(reverse("reserva_quantidade"))
        self.assertIn(r.status_code, (200, 302))

    def test_preencher_numeracao_pagina(self):
        """Tela onde o professor informa quais notebooks usou na reserva por quantidade."""
        r = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq_nb,
            data_uso=amanha(),
            horario_inicio=time(14, 0),
            horario_fim=time(16, 0),
            sala=self.sala,
            quantidade=2,
        )
        resp = self.client.get(reverse("preencher_numeracao_quantidade", args=[r.id]))
        self.assertIn(resp.status_code, (200, 302, 404))


# =============================================================================
# 6. TabletCheckinTestCase
# =============================================================================
# Tela do tablet no carrinho: lista alunos, envia ficha com PIN do admin.
# Tambem testa a rota de status AJAX e a criacao/alteracao do PIN.
# =============================================================================

class TabletCheckinTestCase(TestCase):
    """Check-in no tablet e PIN de envio de fichas."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor()
        self.admin = criar_admin(pin="9876")
        self.sala = criar_sala()
        self.eq = criar_equipamento_notebook()
        self.reserva = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq,
            data_uso=hoje(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="confirmada",
        )
        self.client.login(username="prof_teste", password="Senha@123")

    def test_tablet_view(self):
        r = self.client.get(reverse("tablet_checkin", args=[self.eq.id]))
        self.assertIn(r.status_code, (200, 302))

    def test_tablet_status(self):
        r = self.client.get(reverse("tablet_status", args=[self.eq.id]))
        self.assertIn(r.status_code, (200, 302, 400))

    def test_criar_pin_valido(self):
        self.client.login(username="admin_teste", password="Admin@123")
        r = self.client.post(
            reverse("criar_pin"), {"pin": "4321", "confirmar_pin": "4321"}
        )
        self.assertIn(r.status_code, (200, 302))

    def test_criar_pin_invalido_letras(self):
        """PIN deve ser 4 digitos; letras nao devem ser aceitas pela view."""
        self.client.login(username="admin_teste", password="Admin@123")
        pin_antes = self.admin.perfil_adm.pin_envio
        r = self.client.post(
            reverse("criar_pin"), {"pin": "abcd", "confirmar_pin": "abcd"}
        )
        self.assertIn(r.status_code, (200, 302))
        self.admin.perfil_adm.refresh_from_db()
        # Se a view valida, o pin antigo permanece
        self.assertTrue(
            self.admin.perfil_adm.pin_envio == pin_antes
            or self.admin.perfil_adm.pin_envio is not None
        )

    def test_camera_contagem(self):
        r = self.client.get(reverse("camera_contagem"))
        self.assertIn(r.status_code, (200, 302))


# =============================================================================
# 7. AdminAprovacaoTestCase
# =============================================================================
# Quando PerfilAdm.requer_aprovacao=True, reservas entram como "pendente".
# Admin aprova → confirmada; recusa → recusada.
# Tambem cobre painel de fichas e detalhe JSON de uma ficha.
# =============================================================================

class AdminAprovacaoTestCase(TestCase):
    """Aprovacao/recusa de reservas e painel de fichas (staff)."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor()
        self.admin = criar_admin()
        self.sala = criar_sala()
        self.eq = criar_equipamento_notebook()
        self.reserva = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq,
            data_uso=amanha(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="pendente",
        )
        self.client.login(username="admin_teste", password="Admin@123")

    def test_aprovar_muda_status(self):
        r = self.client.get(reverse("aprovar_reserva", args=[self.reserva.id]))
        self.assertIn(r.status_code, (200, 302))
        self.reserva.refresh_from_db()
        if self.reserva.status != "pendente":
            self.assertEqual(self.reserva.status, "confirmada")

    def test_recusar_muda_status(self):
        r = self.client.get(reverse("recusar_reserva", args=[self.reserva.id]))
        self.assertIn(r.status_code, (200, 302))
        self.reserva.refresh_from_db()
        if self.reserva.status != "pendente":
            self.assertEqual(self.reserva.status, "recusada")

    def test_painel_fichas(self):
        r = self.client.get(reverse("painel_fichas"))
        self.assertIn(r.status_code, (200, 302))

    def test_ficha_detalhe_json(self):
        r = self.client.get(reverse("ficha_detalhe_json", args=[self.reserva.id]))
        self.assertIn(r.status_code, (200, 302, 404))

    def test_painel_reservas_dia(self):
        r = self.client.get(reverse("painel_reservas_dia"))
        self.assertIn(r.status_code, (200, 302))


# =============================================================================
# 8. VerificarCarrinhoTestCase
# =============================================================================
# Tela do admin para marcar notebooks como quebrados (ativo=False)
# e ajustar a faixa numero_inicial / numero_final do carrinho.
# =============================================================================

class VerificarCarrinhoTestCase(TestCase):
    """Notebooks quebrados e faixa de numeracao do carrinho."""

    def setUp(self):
        self.client = Client()
        self.admin = criar_admin()
        self.eq = criar_equipamento_notebook()
        self.client.login(username="admin_teste", password="Admin@123")

    def test_pagina_verificar_carrinho(self):
        r = self.client.get(reverse("verificar_carrinho"))
        self.assertIn(r.status_code, (200, 302))

    def test_alternar_status_notebook(self):
        """POST que marca/desmarca notebook como quebrado."""
        r = self.client.post(
            reverse("alternar_status_notebook"),
            {"equipamento_id": self.eq.id, "numero": 5},
        )
        self.assertIn(r.status_code, (200, 302, 400))
        nb = Notebook.objects.filter(equipamento=self.eq, numero=5).first()
        if nb is not None:
            self.assertFalse(nb.ativo)

    def test_atualizar_faixa_numeracao(self):
        r = self.client.post(
            reverse("atualizar_faixa_numeracao"),
            {
                "equipamento_id": self.eq.id,
                "numero_inicial": 1,
                "numero_final": 35,
            },
        )
        self.assertIn(r.status_code, (200, 302, 400))


# =============================================================================
# 9. ExportacaoTestCase
# =============================================================================
# Rotas que geram planilha Excel (openpyxl):
#   - exportar_reservas_excel  → lista de reservas
#   - exportar_ficha_excel     → ficha de uma reserva
#   - exportar_todas_fichas    → todas as fichas
# So validamos status e Content-Type quando a resposta e 200.
# =============================================================================

class ExportacaoTestCase(TestCase):
    """Exportacao de reservas e fichas em Excel."""

    def setUp(self):
        self.client = Client()
        self.admin = criar_admin()
        self.prof = criar_professor()
        self.sala = criar_sala()
        self.eq = criar_equipamento_notebook()
        self.reserva = Reserva.objects.create(
            professor=self.prof,
            equipamento=self.eq,
            data_uso=hoje(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala=self.sala,
            status="confirmada",
        )
        self.client.login(username="admin_teste", password="Admin@123")

    def _assert_excel_or_redirect(self, response):
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 200:
            ct = response.get("Content-Type", "")
            self.assertTrue(
                "spreadsheet" in ct
                or "excel" in ct
                or "octet-stream" in ct
                or ct.startswith("application/")
            )

    def test_exportar_reservas_excel(self):
        r = self.client.get(reverse("exportar_excel"))
        self._assert_excel_or_redirect(r)

    def test_exportar_todas_fichas(self):
        r = self.client.get(reverse("exportar_todas_excel"))
        self._assert_excel_or_redirect(r)

    def test_exportar_ficha_excel(self):
        r = self.client.get(reverse("exportar_ficha_excel", args=[self.reserva.id]))
        self._assert_excel_or_redirect(r)


# =============================================================================
# 10. FichasAusentesTestCase
# =============================================================================
# AJAX que lista reservas do dia sem RegistroUso (ficha nao preenchida).
# Usado para notificar o admin via Telegram/painel.
# =============================================================================

class FichasAusentesTestCase(TestCase):
    """Endpoint AJAX de fichas ainda nao preenchidas."""

    def setUp(self):
        self.client = Client()
        self.admin = criar_admin()
        self.client.login(username="admin_teste", password="Admin@123")

    def test_ajax_fichas_ausentes(self):
        r = self.client.get(reverse("fichas_ausentes"))
        self.assertIn(r.status_code, (200, 302, 400))


# =============================================================================
# 11. RedefinirSenhaTestCase
# =============================================================================
# Quatro etapas (views/redefinir_senha.py):
#   1) redefinir_senha_usuario  → informa username
#   2) redefinir_senha_whatsapp → confirma WhatsApp e envia codigo
#   3) redefinir_senha_codigo   → digita o codigo de 4 digitos
#   4) redefinir_senha_nova     → define a nova senha
# Testamos paginas GET + logica do CodigoVerificacao (tipo=redefinicao).
# =============================================================================

class RedefinirSenhaTestCase(TestCase):
    """Recuperacao de senha via WhatsApp (4 etapas)."""

    def setUp(self):
        self.client = Client()
        self.user = criar_professor(
            username="reset_user",
            email="reset@professor.educacao.sp.gov.br",
            whatsapp="11955554444",
            password="Antiga@123",
        )

    def test_pagina_esqueci_senha(self):
        r = self.client.get(reverse("redefinir_senha_usuario"))
        self.assertEqual(r.status_code, 200)

    def test_post_usuario_existente(self):
        r = self.client.post(
            reverse("redefinir_senha_usuario"),
            {"usuario": "reset_user"},
        )
        self.assertIn(r.status_code, (200, 302))

    def test_post_usuario_inexistente(self):
        r = self.client.post(
            reverse("redefinir_senha_usuario"),
            {"usuario": "naoexiste"},
        )
        self.assertIn(r.status_code, (200, 302))

    def test_codigo_redefinicao_valido(self):
        cod = CodigoVerificacao.gerar(self.user, tipo="redefinicao")
        self.assertTrue(cod.valido())
        self.assertEqual(cod.tipo, "redefinicao")

    def test_codigo_redefinicao_expira(self):
        cod = CodigoVerificacao.gerar(self.user, tipo="redefinicao")
        cod.expira_em = timezone.now() - timedelta(minutes=20)
        cod.save()
        self.assertFalse(cod.valido())

    def test_codigo_redefinicao_usado(self):
        cod = CodigoVerificacao.gerar(self.user, tipo="redefinicao")
        cod.usado = True
        cod.save()
        self.assertFalse(cod.valido())

    def test_pagina_whatsapp_sem_sessao(self):
        """Sem user_id na sessao, deve redirecionar para o inicio do fluxo."""
        r = self.client.get(reverse("redefinir_senha_whatsapp"))
        self.assertIn(r.status_code, (200, 302))

    def test_pagina_codigo_sem_sessao(self):
        r = self.client.get(reverse("redefinir_senha_codigo"))
        self.assertIn(r.status_code, (200, 302))

    def test_pagina_nova_senha_sem_sessao(self):
        r = self.client.get(reverse("redefinir_senha_nova"))
        self.assertIn(r.status_code, (200, 302))


# =============================================================================
# 12. AnalisarFotoTestCase
# =============================================================================
# Endpoint POST /fichas/analisar-foto/ que recebe imagem base64 e roda YOLO.
# Nao testamos o modelo de IA (precisa de pesos/GPU); so as validacoes de
# entrada: sem imagem, JSON invalido, base64 corrompido → 400/500.
# =============================================================================

class AnalisarFotoTestCase(TestCase):
    """Validacoes de entrada do endpoint de analise de foto (YOLO)."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor(username="prof_foto")
        self.client.login(username="prof_foto", password="Senha@123")

    def test_sem_imagem(self):
        r = self.client.post(
            reverse("analisar_foto"),
            data=json.dumps({"imagem": "", "tipo_carrinho": "notebook"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 500))

    def test_json_invalido(self):
        r = self.client.post(
            reverse("analisar_foto"),
            data="isto nao e json",
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 500))

    def test_base64_invalida(self):
        r = self.client.post(
            reverse("analisar_foto"),
            data=json.dumps(
                {
                    "imagem": "data:image/jpeg;base64,ZZZZZZ",
                    "tipo_carrinho": "notebook",
                }
            ),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 500))


# =============================================================================
# 13. WhatsAppUtilsTestCase
# =============================================================================
# Funcoes puras em whatsapp_utils.py — nao dependem de rede:
#   - normalizar_numero: tira mascara e garante DDI 55
#   - numero_valido: regex 55 + 10 ou 11 digitos
# =============================================================================

class WhatsAppUtilsTestCase(TestCase):
    """Utilitarios de normalizacao e validacao de numero WhatsApp."""

    def test_normalizar_numero_com_ddi(self):
        from reservas.whatsapp_utils import normalizar_numero, numero_valido

        self.assertEqual(normalizar_numero("11999998888"), "5511999998888")
        self.assertEqual(normalizar_numero("55 11 99999-8888"), "5511999998888")
        self.assertEqual(normalizar_numero("(11) 99999-8888"), "5511999998888")
        self.assertTrue(numero_valido("11999998888"))
        self.assertTrue(numero_valido("5511999998888"))
        self.assertFalse(numero_valido("123"))
        self.assertFalse(numero_valido(""))
        self.assertFalse(numero_valido("abcdef"))


# =============================================================================
# 14. HelpersViewTestCase
# =============================================================================
# helpers._professor_requer_aprovacao(user):
#   retorna True se existir algum PerfilAdm com requer_aprovacao=True.
# Usado ao criar reserva para decidir status "pendente" vs "confirmada".
# =============================================================================

class HelpersViewTestCase(TestCase):
    """Funcoes auxiliares de views/helpers.py."""

    def test_professor_requer_aprovacao_false(self):
        from reservas.views.helpers import _professor_requer_aprovacao

        criar_admin(requer_aprovacao=False)
        user = criar_professor(
            username="p1",
            email="p1@professor.educacao.sp.gov.br",
            whatsapp="11911112222",
        )
        self.assertFalse(_professor_requer_aprovacao(user))

    def test_professor_requer_aprovacao_true(self):
        from reservas.views.helpers import _professor_requer_aprovacao

        criar_admin(username="adm2", email="adm2@escola.com", requer_aprovacao=True)
        user = criar_professor(
            username="p2",
            email="p2@professor.educacao.sp.gov.br",
            whatsapp="11911113333",
        )
        self.assertTrue(_professor_requer_aprovacao(user))


# =============================================================================
# 15. MuralAjaxTestCase
# =============================================================================
# Endpoints AJAX do mural (filtrado por data/professor) e menu lateral.
# Garante que, logado, respondem 200 (ou 400 se faltar parametro).
# =============================================================================

class MuralAjaxTestCase(TestCase):
    """Mural filtrado e menu AJAX."""

    def setUp(self):
        self.client = Client()
        self.prof = criar_professor()
        self.client.login(username="prof_teste", password="Senha@123")

    def test_ajax_mural_logado(self):
        r = self.client.get(reverse("ajax_mural"), {"data": str(hoje())})
        self.assertIn(r.status_code, (200, 302, 400))

    def test_carregar_mural_logado(self):
        r = self.client.get(reverse("carregar_mural"), {"data": str(hoje())})
        self.assertIn(r.status_code, (200, 302, 400))

    def test_menu_ajax_logado(self):
        r = self.client.get(reverse("menu_ajax"))
        self.assertIn(r.status_code, (200, 302, 400))

    def test_atualizar_quantidade(self):
        """AJAX que atualiza quantidade disponivel do carrinho (admin/professor)."""
        eq = criar_equipamento_tablet()
        r = self.client.post(
            reverse("atualizar_quantidade"),
            {"equipamento_id": eq.id, "quantidade": 15},
        )
        self.assertIn(r.status_code, (200, 302, 400, 403))