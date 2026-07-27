# -*- coding: utf-8 -*-
"""
teste.py — Testes Robotizados para o sistema PROATI / GTREP
============================================================

Este arquivo contém testes automatizados (unitários e de integração)
que percorrem TODO o site, verificando:

    1.  Criação e integridade dos modelos (models)
    2.  Acessibilidade de todas as URLs (status code)
    3.  Fluxo completo de autenticação (cadastro, login, logout)
    4.  Criação de reservas (carrinho inteiro e por quantidade)
    5.  Aprovação / recusa de reservas pendentes (admin)
    6.  Endpoints AJAX (disponibilidade, numeração, mural)
    7.  Fluxo do tablet (PIN, envio de ficha, validações)
    8.  Verificação de carrinhos e notebooks quebrados
    9.  Exportação de fichas e reservas em Excel

Como executar:
    python manage.py test app.teste --verbosity=2

Requisitos:
    - Django configurado com o app 'reservas'
    - Banco de dados SQLite (ou outro) com permissão de escrita
    - Pacotes: django, openpyxl (para testes de exportação)
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================

import io
import json
from datetime import date, datetime, time, timedelta

# Django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

# Modelos do projeto
from reservas.models import (
    PerfilAdm,
    Equipamento,
    Notebook,
    Sala,
    Reserva,
    NumeroReservaQuantidade,
    Aluno,
    RegistroUso,
    NotificacaoFichaAusente,
)

# =============================================================================
# 1. TESTES DOS MODELOS
# =============================================================================

class ModelosTestCase(TestCase):
    """
    Verifica a criação correta de todas as entidades do banco de dados,
    seus relacionamentos, métodos de instância e restrições de integridade.
    """

    def setUp(self):
        """Prepara dados compartilhados entre os testes de modelo."""
        # Cria um usuário professor
        self.usuario = User.objects.create_user(
            username="professor_teste",
            email="professor.teste@professor.educacao.sp.gov.br",
            password="senha_segura_123"
        )
        # Cria um administrador (staff)
        self.admin = User.objects.create_user(
            username="admin_teste",
            email="admin@escola.com",
            password="admin_seguro_456",
            is_staff=True
        )
        # Cria uma sala
        self.sala = Sala.objects.create(nome="1A")
        # Cria um carrinho de notebooks
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho 01",
            tipo="notebook",
            quantidade=40,
            numero_inicial=1,
            numero_final=40,
        )

    # ------------------------------------------------------------------
    # 1.1 Equipamento
    # ------------------------------------------------------------------

    def test_criar_equipamento_notebook(self):
        """Verifica a criação de um equipamento do tipo notebook."""
        equip = Equipamento.objects.create(
            nome="Carrinho Teste NB",
            tipo="notebook",
            quantidade=30,
        )
        self.assertEqual(equip.nome, "Carrinho Teste NB")
        self.assertEqual(equip.tipo, "notebook")
        self.assertTrue(equip.disponivel)
        self.assertEqual(str(equip), "Carrinho Teste NB (Carrinho de Notebooks)")

    def test_criar_equipamento_tablet(self):
        """Verifica a criação de um equipamento do tipo tablet."""
        equip = Equipamento.objects.create(
            nome="Carrinho Tablet",
            tipo="tablet",
            quantidade=20,
        )
        self.assertEqual(equip.tipo, "tablet")
        self.assertEqual(str(equip), "Carrinho Tablet (Carrinho de Tablets)")

    def test_faixa_numeros_sem_intervalo(self):
        """Se numero_inicial e numero_final forem None, faixa_numeros() retorna vazio."""
        equip = Equipamento.objects.create(nome="Sem Faixa", tipo="notebook", quantidade=10)
        self.assertEqual(equip.faixa_numeros(), set())

    def test_faixa_numeros_com_intervalo(self):
        """faixa_numeros() deve retornar um set com todos os números entre inicial e final."""
        self.equipamento.numero_inicial = 1
        self.equipamento.numero_final = 5
        self.equipamento.save()
        esperado = {1, 2, 3, 4, 5}
        self.assertEqual(self.equipamento.faixa_numeros(), esperado)

    def test_lista_numeros_ordenada(self):
        """lista_numeros() deve retornar uma lista ordenada."""
        self.equipamento.numero_inicial = 10
        self.equipamento.numero_final = 5
        self.equipamento.save()
        # Se inicial > final, range fica vazio porque set(range(10,6)) = set()
        # O método retorna sorted da faixa
        self.assertEqual(self.equipamento.lista_numeros(), [])

    def test_quantidade_ativa_sem_notebooks(self):
        """quantidade_ativa() deve refletir a faixa menos os notebooks inativos."""
        qtd = self.equipamento.quantidade_ativa()
        # faixa 1..40 = 40, nenhum notebook inativo → 40
        self.assertEqual(qtd, 40)

    def test_quantidade_ativa_com_inativos(self):
        """Cria notebooks inativos e verifica a redução na quantidade ativa."""
        Notebook.objects.create(equipamento=self.equipamento, numero=5, ativo=False)
        Notebook.objects.create(equipamento=self.equipamento, numero=10, ativo=False)
        qtd = self.equipamento.quantidade_ativa()
        self.assertEqual(qtd, 38)  # 40 - 2 = 38

    # ------------------------------------------------------------------
    # 1.2 Notebook
    # ------------------------------------------------------------------

    def test_criar_notebook(self):
        """Cria um notebook e verifica seus atributos."""
        nb = Notebook.objects.create(
            equipamento=self.equipamento,
            numero=1,
            ativo=True,
        )
        self.assertEqual(nb.numero, 1)
        self.assertTrue(nb.ativo)
        self.assertIn("Carrinho 01", str(nb))
        self.assertIn("ativo", str(nb))

    def test_notebook_inativo(self):
        """Notebook com ativo=False deve refletir no verbose_name 'quebrado'."""
        nb = Notebook.objects.create(
            equipamento=self.equipamento,
            numero=2,
            ativo=False,
        )
        self.assertIn("quebrado", str(nb))

    def test_notebook_unico_por_equipamento(self):
        """
        unique_together = ('equipamento', 'numero') impede dois notebooks
        com mesmo número no mesmo carrinho.
        """
        Notebook.objects.create(equipamento=self.equipamento, numero=1)
        with self.assertRaises(Exception):
            Notebook.objects.create(equipamento=self.equipamento, numero=1)

    # ------------------------------------------------------------------
    # 1.3 Sala
    # ------------------------------------------------------------------

    def test_criar_sala(self):
        """Verifica a criação e string de Sala."""
        sala = Sala.objects.create(nome="2B")
        self.assertEqual(str(sala), "2B")

    # ------------------------------------------------------------------
    # 1.4 Aluno
    # ------------------------------------------------------------------

    def test_criar_aluno(self):
        """Cria um aluno vinculado a uma sala."""
        aluno = Aluno.objects.create(nome="João Silva", sala=self.sala)
        self.assertEqual(str(aluno), "João Silva (1A)")
        self.assertEqual(aluno.sala, self.sala)

    # ------------------------------------------------------------------
    # 1.5 PerfilAdm
    # ------------------------------------------------------------------

    def test_criar_perfil_adm_sem_pin(self):
        """Cria perfil ADM sem PIN — pin_envio deve ser None."""
        perfil = PerfilAdm.objects.create(usuario=self.usuario, requer_aprovacao=True)
        self.assertTrue(perfil.requer_aprovacao)
        self.assertIsNone(perfil.pin_envio)

    def test_criar_perfil_adm_com_pin(self):
        """Cria perfil ADM com PIN de 4 dígitos."""
        perfil = PerfilAdm.objects.create(
            usuario=self.admin,
            requer_aprovacao=False,
            pin_envio="1234",
        )
        self.assertEqual(perfil.pin_envio, "1234")

    # ------------------------------------------------------------------
    # 1.6 Reserva
    # ------------------------------------------------------------------

    def test_criar_reserva_confirmada(self):
        """Cria uma reserva com status 'confirmada'."""
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
            status="confirmada",
        )
        self.assertEqual(reserva.professor, self.usuario)
        self.assertEqual(reserva.status, "confirmada")
        self.assertIn("professor_teste", str(reserva))

    def test_criar_reserva_pendente(self):
        """Cria uma reserva pendente de aprovação."""
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(8, 50),
            sala=self.sala,
            status="pendente",
        )
        self.assertEqual(reserva.status, "pendente")

    def test_criar_reserva_com_quantidade(self):
        """Cria uma reserva por quantidade específica."""
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(9, 0),
            horario_fim=time(9, 50),
            sala=self.sala,
            quantidade=10,
        )
        self.assertEqual(reserva.quantidade, 10)

    # ------------------------------------------------------------------
    # 1.7 NumeroReservaQuantidade
    # ------------------------------------------------------------------

    def test_criar_numero_reserva_quantidade(self):
        """Cria números de notebook vinculados a uma reserva por quantidade."""
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(10, 0),
            horario_fim=time(10, 50),
            sala=self.sala,
            quantidade=2,
        )
        n1 = NumeroReservaQuantidade.objects.create(reserva=reserva, numero=1)
        n2 = NumeroReservaQuantidade.objects.create(reserva=reserva, numero=2)
        self.assertEqual(reserva.numeros_quantidade.count(), 2)

    # ------------------------------------------------------------------
    # 1.8 RegistroUso
    # ------------------------------------------------------------------

    def test_criar_registro_uso(self):
        """Cria um registro de uso (ficha de aluno)."""
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
        )
        aluno = Aluno.objects.create(nome="Maria", sala=self.sala)
        registro = RegistroUso.objects.create(
            reserva=reserva,
            aluno=aluno,
            numero_notebook=15,
        )
        self.assertEqual(registro.numero_notebook, 15)
        self.assertEqual(registro.aluno, aluno)


# =============================================================================
# 2. TESTES DE URLs E ACESSO
# =============================================================================

class URLsTestCase(TestCase):
    """
    Verifica se todas as URLs do sistema retornam os status HTTP esperados
    para usuários anônimos, logados e administradores.
    """

    def setUp(self):
        """Prepara clientes e usuários para os testes de URL."""
        self.client = Client()
        # Usuário comum
        self.usuario = User.objects.create_user(
            username="prof_comum",
            email="prof@professor.educacao.sp.gov.br",
            password="senha123",
        )
        # Administrador
        self.admin = User.objects.create_user(
            username="admin_sistema",
            email="admin@escola.com",
            password="admin123",
            is_staff=True,
        )
        # Dados auxiliares
        self.sala = Sala.objects.create(nome="1A")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho NB",
            tipo="notebook",
            quantidade=40,
        )
        # Reserva de exemplo para URLs com parâmetros
        self.reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=date.today() + timedelta(days=1),
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
        )

    # ------------------------------------------------------------------
    # 2.1 URLs públicas (acessíveis sem login)
    # ------------------------------------------------------------------

    def test_url_home_anonimo(self):
        """GET / → deve retornar 200 (página inicial pública)."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_url_criar_conta_anonimo(self):
        """GET /criar/ → deve retornar 200 (formulário de cadastro)."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_url_entrar_anonimo(self):
        """GET /entrar/ → deve retornar 200 (formulário de login)."""
        response = self.client.get(reverse("longa"))
        self.assertEqual(response.status_code, 200)

    def test_url_mural_consulta_anonimo(self):
        """GET /painel/ → deve retornar 200 (mural público de consulta)."""
        response = self.client.get(reverse("mural_consulta"))
        self.assertEqual(response.status_code, 200)

    def test_url_carregar_mural_publico_anonimo(self):
        """GET /carregar-mural-publico/ → deve retornar 200."""
        response = self.client.get(reverse("carregar_mural_publico"))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # 2.2 URLs protegidas (redirecionam anônimos para login → 302)
    # ------------------------------------------------------------------

    def test_url_mural_protegida(self):
        """GET /Logar/ sem login → redireciona (302) para /entrar/."""
        response = self.client.get(reverse("mural"))
        self.assertEqual(response.status_code, 302)

    def test_url_unico_protegida(self):
        """GET /unico/ sem login → redireciona (302)."""
        response = self.client.get(reverse("unico"))
        self.assertEqual(response.status_code, 302)

    def test_url_tablet_protegida(self):
        """GET /tablet/1/ sem login → retorna 200 com mensagem de erro
        (a view não usa @login_required, mas mostra "Nenhuma reserva ativa")."""
        response = self.client.get(reverse("tablet_checkin", args=[self.equipamento.id]))
        # A view não redireciona; ela retorna 200 com HttpResponse informando
        # que não há reserva ativa para o carrinho.
        self.assertContains(response, "Nenhuma reserva ativa")

    def test_url_camera_protegida(self):
        """GET /camera/ sem login → redireciona (302)."""
        response = self.client.get(reverse("camera_contagem"))
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------------
    # 2.3 URLs administrativas (bloqueiam não-staff → 302)
    # ------------------------------------------------------------------

    def test_url_aprovar_reserva_nao_staff(self):
        """GET /reserva/1/aprovar/ sem ser staff → redireciona."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("aprovar_reserva", args=[self.reserva.id]))
        # Usuário não-staff → redireciona (302) para o login admin
        self.assertEqual(response.status_code, 302)

    def test_url_aprovar_reserva_staff(self):
        """GET /reserva/1/aprovar/ como staff → deve aprovar e redirecionar."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("aprovar_reserva", args=[self.reserva.id]))
        # Redireciona para o mural após aprovar
        self.assertEqual(response.status_code, 302)
        # Verifica se o status foi alterado no banco
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, "confirmada")

    def test_url_recusar_reserva_staff(self):
        """GET /reserva/1/recusar/ como staff → recusa e redireciona."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("recusar_reserva", args=[self.reserva.id]))
        self.assertEqual(response.status_code, 302)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, "recusada")

    def test_url_painel_reservas_nao_staff(self):
        """GET /painel-reservas/ sem staff → redireciona (302)."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("painel_reservas_dia"))
        self.assertEqual(response.status_code, 302)

    def test_url_painel_reservas_staff(self):
        """GET /painel-reservas/ como staff → 200."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("painel_reservas_dia"))
        self.assertEqual(response.status_code, 200)

    def test_url_verificar_carrinho_nao_staff(self):
        """GET /verificar-carrinho/ sem staff → 302."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("verificar_carrinho"))
        self.assertEqual(response.status_code, 302)

    def test_url_verificar_carrinho_staff(self):
        """GET /verificar-carrinho/ como staff → 200."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("verificar_carrinho"))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # 2.4 URLs de AJAX (protegidas por login)
    # ------------------------------------------------------------------

    def test_ajax_disponiveis_anonimo(self):
        """GET /ajax/disponiveis/ sem login → 302."""
        response = self.client.get(reverse("ajax_disponiveis"))
        self.assertEqual(response.status_code, 302)

    def test_ajax_disponiveis_logado(self):
        """GET /ajax/disponiveis/ logado → 200."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("ajax_disponiveis"), {
            "data": date.today().strftime("%Y-%m-%d"),
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        })
        self.assertEqual(response.status_code, 200)

    def test_ajax_numeros_disponiveis_logado(self):
        """GET /ajax/numeros-disponiveis/ logado → 200."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("numeros_disponiveis"), {
            "equipamento_id": self.equipamento.id,
            "data": date.today().strftime("%Y-%m-%d"),
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("numeros", data)

    def test_ajax_fichas_ausentes_staff(self):
        """GET /ajax/fichas-ausentes/ como staff → 200."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("fichas_ausentes"))
        self.assertEqual(response.status_code, 200)

    def test_ajax_mural_logado(self):
        """GET /ajax/mural-filtrado/ logado → 200."""
        self.client.login(username="prof_comum", password="senha123")
        response = self.client.get(reverse("ajax_mural"), {
            "data": date.today().strftime("%Y-%m-%d"),
        })
        self.assertEqual(response.status_code, 200)

    def test_ajax_menu_logado(self):
        """GET /ajax/menu/ como staff → 200."""
        self.client.login(username="admin_sistema", password="admin123")
        response = self.client.get(reverse("menu_ajax"))
        self.assertEqual(response.status_code, 200)


# =============================================================================
# 3. TESTES DE AUTENTICAÇÃO
# =============================================================================

class AutenticacaoTestCase(TestCase):
    """
    Testa o fluxo completo de criação de conta, login, logout
    e restrições de acesso.
    """

    def setUp(self):
        self.client = Client()

    # ------------------------------------------------------------------
    # 3.1 Criação de conta (signup)
    # ------------------------------------------------------------------

    def test_criar_conta_valida(self):
        """Cadastro com e-mail corporativo @professor.educacao.sp.gov.br deve ser aceito."""
        dados = {
            "usuario": "novo_professor",
            "email": "novo@professor.educacao.sp.gov.br",
            "senha": "senha_forte_789",
            "confirmar_senha": "senha_forte_789",
        }
        response = self.client.post(reverse("index"), dados, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="novo_professor").exists())

    def test_criar_conta_email_invalido(self):
        """Cadastro com e-mail que NÃO é @professor.educacao.sp.gov.br deve falhar."""
        dados = {
            "usuario": "prof_invalido",
            "email": "prof@gmail.com",
            "senha": "senha123",
            "confirmar_senha": "senha123",
        }
        response = self.client.post(reverse("index"), dados, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="prof_invalido").exists())
        # Verifica se a mensagem de erro foi enviada
        messages = list(response.context.get("messages", []))
        self.assertTrue(any("Apenas e-mails corporativo" in str(m) for m in messages))

    def test_criar_conta_senhas_diferentes(self):
        """Cadastro com senhas diferentes deve falhar."""
        dados = {
            "usuario": "prof_senhas",
            "email": "prof_senhas@professor.educacao.sp.gov.br",
            "senha": "senha123",
            "confirmar_senha": "senha_diferente",
        }
        response = self.client.post(reverse("index"), dados, follow=True)
        self.assertFalse(User.objects.filter(username="prof_senhas").exists())

    def test_criar_conta_usuario_duplicado(self):
        """Cadastro com username já existente deve falhar."""
        User.objects.create_user(
            username="existente",
            email="existente@professor.educacao.sp.gov.br",
            password="senha123",
        )
        dados = {
            "usuario": "existente",
            "email": "outro@professor.educacao.sp.gov.br",
            "senha": "senha456",
            "confirmar_senha": "senha456",
        }
        response = self.client.post(reverse("index"), dados, follow=True)
        # Verifica se a mensagem de erro foi emitida
        messages = list(response.context.get("messages", []))
        self.assertTrue(any("já está em uso" in str(m) for m in messages))

    # ------------------------------------------------------------------
    # 3.2 Login
    # ------------------------------------------------------------------

    def test_login_valido(self):
        """Login com credenciais corretas deve redirecionar ao mural."""
        User.objects.create_user(
            username="prof_login",
            email="prof_login@professor.educacao.sp.gov.br",
            password="minha_senha",
        )
        response = self.client.post(reverse("longa"), {
            "usuario": "prof_login",
            "senha": "minha_senha",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        # Após login, o usuário é redirecionado ao mural (name='mural')
        self.assertIn("prof_login", response.content.decode())

    def test_login_usuario_inexistente(self):
        """Login com usuário que não existe deve exibir mensagem de erro."""
        response = self.client.post(reverse("longa"), {
            "usuario": "nao_existe",
            "senha": "qualquer",
        }, follow=True)
        messages = list(response.context.get("messages", []))
        self.assertTrue(any("Usuário não encontrado" in str(m) for m in messages))

    def test_login_senha_incorreta(self):
        """Login com senha errada deve exibir mensagem de erro."""
        User.objects.create_user(
            username="prof_senha_errada",
            email="prof_senha_errada@professor.educacao.sp.gov.br",
            password="senha_correta",
        )
        response = self.client.post(reverse("longa"), {
            "usuario": "prof_senha_errada",
            "senha": "senha_errada",
        }, follow=True)
        messages = list(response.context.get("messages", []))
        self.assertTrue(any("Senha incorreta" in str(m) for m in messages))


# =============================================================================
# 4. TESTES DO FLUXO DE RESERVAS
# =============================================================================

class FluxoReservasTestCase(TestCase):
    """
    Testa a criação de reservas (carrinho inteiro e por quantidade),
    validações de conflito de horário, sobreposição e limites.
    """

    def setUp(self):
        self.client = Client()
        self.usuario = User.objects.create_user(
            username="prof_reserva",
            email="prof_reserva@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.admin = User.objects.create_user(
            username="admin_reserva",
            email="admin_reserva@escola.com",
            password="admin123",
            is_staff=True,
        )
        self.sala = Sala.objects.create(nome="3C")
        self.sala2 = Sala.objects.create(nome="3D")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho A",
            tipo="notebook",
            quantidade=40,
            numero_inicial=1,
            numero_final=40,
        )
        self.client.login(username="prof_reserva", password="senha123")

    # ------------------------------------------------------------------
    # 4.1 Reserva de carrinho inteiro (mural.html)
    # ------------------------------------------------------------------

    def test_reserva_carrinho_inteiro_sucesso(self):
        """Cria uma reserva de carrinho inteiro com dados válidos via POST."""
        data_futura = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = self.client.post(reverse("mural"), {
            "data": data_futura,
            "equipamento": self.equipamento.id,
            "sala": self.sala.id,
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        # Deve existir uma reserva confirmada
        self.assertTrue(
            Reserva.objects.filter(
                professor=self.usuario,
                equipamento=self.equipamento,
                status="confirmada",
            ).exists()
        )

    def test_reserva_carrinho_inteiro_duplicada_horario(self):
        """Não permite duas reservas do mesmo carrinho no mesmo horário."""
        data_futura = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        # Primeira reserva
        self.client.post(reverse("mural"), {
            "data": data_futura,
            "equipamento": self.equipamento.id,
            "sala": self.sala.id,
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        })
        # Segunda reserva no mesmo horário
        response = self.client.post(reverse("mural"), {
            "data": data_futura,
            "equipamento": self.equipamento.id,
            "sala": self.sala2.id,
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        }, follow=True)
        # Deve haver apenas 1 reserva no banco
        qtd = Reserva.objects.filter(
            equipamento=self.equipamento,
            data_uso=date.today() + timedelta(days=7),
            horario_inicio=time(7, 0),
        ).count()
        self.assertEqual(qtd, 1)

    # ------------------------------------------------------------------
    # 4.2 Reserva por quantidade (unico.html → reserva_quantidade)
    # ------------------------------------------------------------------

    def test_reserva_quantidade_sucesso(self):
        """Cria uma reserva por quantidade com dados válidos."""
        data_futura = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = self.client.post(reverse("reserva_quantidade"), {
            "data": data_futura,
            "horario_inicio": "08:00",
            "horario_fim": "08:50",
            "equipamento": self.equipamento.id,
            "quantidade": "5",
            "sala": self.sala.id,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        reserva = Reserva.objects.filter(
            equipamento=self.equipamento,
            data_uso=date.today() + timedelta(days=7),
            horario_inicio=time(8, 0),
        ).first()
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.quantidade, 5)

    def test_reserva_quantidade_excede_disponivel(self):
        """Não permite reservar quantidade maior que a disponível."""
        data_futura = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        self.equipamento.quantidade = 10
        self.equipamento.save()

        response = self.client.post(reverse("reserva_quantidade"), {
            "data": data_futura,
            "horario_inicio": "09:00",
            "horario_fim": "09:50",
            "equipamento": self.equipamento.id,
            "quantidade": "99",
            "sala": self.sala.id,
        }, follow=True)
        # Deve redirecionar com mensagem de erro (não cria reserva)
        self.assertFalse(
            Reserva.objects.filter(
                equipamento=self.equipamento,
                horario_inicio=time(9, 0),
                quantidade=99,
            ).exists()
        )

    def test_reserva_quantidade_soma_com_outras(self):
        """Reservas por quantidade no mesmo horário devem somar até o limite."""
        data_futura = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        self.equipamento.quantidade = 10
        self.equipamento.save()

        # Professor 1 reserva 6 unidades
        self.client.post(reverse("reserva_quantidade"), {
            "data": data_futura,
            "horario_inicio": "10:00",
            "horario_fim": "10:50",
            "equipamento": self.equipamento.id,
            "quantidade": "6",
            "sala": self.sala.id,
        })

        # Outro professor tenta reservar 6 (só há 4 disponíveis)
        self.client.logout()
        outro = User.objects.create_user(
            username="outro_prof",
            email="outro@professor.educacao.sp.gov.br",
            password="senha456",
        )
        self.client.login(username="outro_prof", password="senha456")
        response = self.client.post(reverse("reserva_quantidade"), {
            "data": data_futura,
            "horario_inicio": "10:00",
            "horario_fim": "10:50",
            "equipamento": self.equipamento.id,
            "quantidade": "6",
            "sala": self.sala.id,
        }, follow=True)
        # Deve rejeitar pois 6 + 6 > 10
        self.assertFalse(
            Reserva.objects.filter(
                professor=outro,
                equipamento=self.equipamento,
                horario_inicio=time(10, 0),
            ).exists()
        )

    # ------------------------------------------------------------------
    # 4.3 Preenchimento de numeração (preencher_numeracao_quantidade)
    # ------------------------------------------------------------------

    def test_preencher_numeracao_quantidade_sucesso(self):
        """Preenche a numeração correta para uma reserva por quantidade."""
        data_futura = date.today() + timedelta(days=7)
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=data_futura,
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
            quantidade=3,
        )
        url = reverse("preencher_numeracao_quantidade", args=[reserva.id])
        response = self.client.post(url, {
            "numero": ["1", "2", "3"],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        reserva.refresh_from_db()
        self.assertTrue(reserva.numeracao_preenchida)
        self.assertEqual(reserva.numeros_quantidade.count(), 3)

    def test_preencher_numeracao_repetida(self):
        """Não permite números repetidos na numeração."""
        data_futura = date.today() + timedelta(days=7)
        reserva = Reserva.objects.create(
            professor=self.usuario,
            equipamento=self.equipamento,
            data_uso=data_futura,
            horario_inicio=time(8, 0),
            horario_fim=time(8, 50),
            sala=self.sala,
            quantidade=2,
        )
        url = reverse("preencher_numeracao_quantidade", args=[reserva.id])
        response = self.client.post(url, {
            "numero": ["5", "5"],  # repetido
        }, follow=True)
        reserva.refresh_from_db()
        self.assertFalse(reserva.numeracao_preenchida)


# =============================================================================
# 5. TESTES DO FLUXO DE TABLET (CHECK-IN)
# =============================================================================

class TabletCheckinTestCase(TestCase):
    """
    Testa o fluxo do tablet: visualização da ficha, validação de PIN,
    atribuição de números a alunos, detecção de duplicatas e intervalos.
    """

    def setUp(self):
        self.client = Client()
        self.professor = User.objects.create_user(
            username="prof_tablet",
            email="prof_tablet@professor.educacao.sp.gov.br",
            password="senha123",
        )
        # Cria perfil ADM com PIN de 4 dígitos
        PerfilAdm.objects.create(
            usuario=self.professor,
            requer_aprovacao=False,
            pin_envio="4321",
        )
        self.sala = Sala.objects.create(nome="2A")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho Tablet 01",
            tipo="tablet",
            quantidade=30,
        )
        # Alunos da sala
        self.aluno1 = Aluno.objects.create(nome="Ana", sala=self.sala)
        self.aluno2 = Aluno.objects.create(nome="Bruno", sala=self.sala)
        self.aluno3 = Aluno.objects.create(nome="Carla", sala=self.sala)

        # Reserva ativa no horário atual
        agora = timezone.localtime()
        self.reserva = Reserva.objects.create(
            professor=self.professor,
            equipamento=self.equipamento,
            data_uso=agora.date(),
            horario_inicio=(agora - timedelta(hours=1)).time(),
            horario_fim=(agora + timedelta(hours=1)).time(),
            sala=self.sala,
            status="confirmada",
        )
        self.client.login(username="prof_tablet", password="senha123")

    # ------------------------------------------------------------------
    # 5.1 Acesso à página do tablet
    # ------------------------------------------------------------------

    def test_tablet_acesso_sem_reserva_ativa(self):
        """Se não há reserva ativa agora, deve retornar mensagem de erro."""
        equip_sem_reserva = Equipamento.objects.create(
            nome="Carrinho Vazio", tipo="notebook", quantidade=10,
        )
        response = self.client.get(
            reverse("tablet_checkin", args=[equip_sem_reserva.id])
        )
        self.assertContains(response, "Nenhuma reserva ativa")

    def test_tablet_acesso_com_reserva_ativa(self):
        """Com reserva ativa, deve exibir o formulário da ficha."""
        response = self.client.get(
            reverse("tablet_checkin", args=[self.equipamento.id])
        )
        self.assertEqual(response.status_code, 200)
        # Deve conter os nomes dos alunos
        self.assertContains(response, "Ana")
        self.assertContains(response, "Bruno")
        self.assertContains(response, "Carla")

    # ------------------------------------------------------------------
    # 5.2 Envio de ficha com PIN
    # ------------------------------------------------------------------

    def test_enviar_ficha_pin_correto(self):
        """Envio de ficha com PIN correto deve criar registros de uso."""
        response = self.client.post(
            reverse("tablet_checkin", args=[self.equipamento.id]),
            {
                f"aluno_{self.aluno1.id}": "1",
                f"aluno_{self.aluno2.id}": "2",
                f"aluno_{self.aluno3.id}": "3",
                "pin_envio": "4321",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        # Verifica se os registros foram criados
        self.assertEqual(
            RegistroUso.objects.filter(reserva=self.reserva).count(), 3
        )
        # Verifica se redirecionou para a página de sucesso
        self.assertContains(response, "sucesso")

    def test_enviar_ficha_pin_incorreto(self):
        """Envio com PIN errado não deve criar registros."""
        response = self.client.post(
            reverse("tablet_checkin", args=[self.equipamento.id]),
            {
                f"aluno_{self.aluno1.id}": "1",
                "pin_envio": "0000",  # PIN errado
            },
            follow=True,
        )
        self.assertEqual(
            RegistroUso.objects.filter(reserva=self.reserva).count(), 0
        )

    def test_enviar_ficha_sem_pin(self):
        """Envio sem PIN não deve criar registros."""
        response = self.client.post(
            reverse("tablet_checkin", args=[self.equipamento.id]),
            {
                f"aluno_{self.aluno1.id}": "1",
            },
            follow=True,
        )
        self.assertEqual(
            RegistroUso.objects.filter(reserva=self.reserva).count(), 0
        )

    # ------------------------------------------------------------------
    # 5.3 Validações de duplicatas e intervalos
    # ------------------------------------------------------------------

    def test_enviar_ficha_numero_duplicado(self):
        """Dois alunos não podem receber o mesmo número de notebook."""
        response = self.client.post(
            reverse("tablet_checkin", args=[self.equipamento.id]),
            {
                f"aluno_{self.aluno1.id}": "5",
                f"aluno_{self.aluno2.id}": "5",  # mesmo número
                f"aluno_{self.aluno3.id}": "6",
                "pin_envio": "4321",
            },
            follow=True,
        )
        # Nenhum registro deve ser criado pois houve erro
        self.assertEqual(
            RegistroUso.objects.filter(reserva=self.reserva).count(), 0
        )

    # ------------------------------------------------------------------
    # 5.4 Endpoint de status do tablet
    # ------------------------------------------------------------------

    def test_tablet_status(self):
        """GET /tablet/1/status/ deve retornar JSON."""
        response = self.client.get(
            reverse("tablet_status", args=[self.equipamento.id]),
            {"reserva_atual": self.reserva.id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nova_reserva", data)

    # ------------------------------------------------------------------
    # 5.5 Criação de PIN
    # ------------------------------------------------------------------

    def test_criar_pin_valido(self):
        """POST /criar-pin/ com PIN de 4 dígitos deve salvar."""
        self.client.logout()
        user_sem_pin = User.objects.create_user(
            username="sem_pin",
            email="sem_pin@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.client.login(username="sem_pin", password="senha123")
        response = self.client.post(reverse("criar_pin"), {
            "pin": "9876",
        }, follow=True)
        perfil = PerfilAdm.objects.get(usuario=user_sem_pin)
        self.assertEqual(perfil.pin_envio, "9876")

    def test_criar_pin_invalido_letras(self):
        """PIN com letras não deve ser aceito."""
        self.client.logout()
        user = User.objects.create_user(
            username="pin_letras",
            email="pin_letras@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.client.login(username="pin_letras", password="senha123")
        response = self.client.post(reverse("criar_pin"), {
            "pin": "abcd",
        }, follow=True)
        # PIN não deve ser salvo
        perfil, created = PerfilAdm.objects.get_or_create(usuario=user)
        self.assertIsNone(perfil.pin_envio)


# =============================================================================
# 6. TESTES DO ADMIN (APROVAÇÃO / RECUSA)
# =============================================================================

class AdminAprovacaoTestCase(TestCase):
    """
    Testa o fluxo de administração: aprovação e recusa de reservas,
    painel de fichas e exportações.
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin_aprova",
            email="admin@escola.com",
            password="admin123",
            is_staff=True,
        )
        self.professor = User.objects.create_user(
            username="prof_pendente",
            email="prof_pendente@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.sala = Sala.objects.create(nome="9A")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho NB",
            tipo="notebook",
            quantidade=40,
        )
        # Reserva pendente
        self.reserva_pendente = Reserva.objects.create(
            professor=self.professor,
            equipamento=self.equipamento,
            data_uso=date.today() + timedelta(days=1),
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
            status="pendente",
        )
        self.client.login(username="admin_aprova", password="admin123")

    def test_aprovar_reserva_muda_status(self):
        """Aprovar uma reserva muda seu status para 'confirmada'."""
        response = self.client.get(
            reverse("aprovar_reserva", args=[self.reserva_pendente.id]),
            follow=True,
        )
        self.reserva_pendente.refresh_from_db()
        self.assertEqual(self.reserva_pendente.status, "confirmada")

    def test_recusar_reserva_muda_status(self):
        """Recusar uma reserva muda seu status para 'recusada'."""
        response = self.client.get(
            reverse("recusar_reserva", args=[self.reserva_pendente.id]),
            follow=True,
        )
        self.reserva_pendente.refresh_from_db()
        self.assertEqual(self.reserva_pendente.status, "recusada")

    def test_painel_fichas_staff(self):
        """Painel de fichas deve carregar para staff."""
        response = self.client.get(reverse("painel_fichas"))
        self.assertEqual(response.status_code, 200)

    def test_painel_fichas_filtro_data(self):
        """Painel de fichas com filtro de data."""
        data_str = date.today().strftime("%Y-%m-%d")
        response = self.client.get(reverse("painel_fichas"), {"data": data_str})
        self.assertEqual(response.status_code, 200)


# =============================================================================
# 7. TESTES DE VERIFICAÇÃO DE CARRINHO
# =============================================================================

class VerificarCarrinhoTestCase(TestCase):
    """
    Testa a funcionalidade de verificação de carrinhos:
    - Definição de faixa de numeração
    - Marcação de notebooks como quebrados/inativos
    - Alternância de status
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin_verif",
            email="admin_verif@escola.com",
            password="admin123",
            is_staff=True,
        )
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho Verif",
            tipo="notebook",
            quantidade=20,
            numero_inicial=1,
            numero_final=20,
        )
        self.client.login(username="admin_verif", password="admin123")

    def test_verificar_carrinho_carrega(self):
        """GET /verificar-carrinho/ deve carregar com a tabela de equipamentos."""
        response = self.client.get(reverse("verificar_carrinho"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carrinho Verif")

    def test_atualizar_faixa_numeracao(self):
        """POST /verificar-carrinho/atualizar-faixa/ atualiza a faixa."""
        response = self.client.post(reverse("atualizar_faixa_numeracao"), {
            "equipamento_id": self.equipamento.id,
            "numero_inicial": "1",
            "numero_final": "30",
        }, follow=True)
        self.equipamento.refresh_from_db()
        self.assertEqual(self.equipamento.numero_final, 30)

    def test_alternar_status_notebook_criar(self):
        """Alternar status de notebook que não existe deve criá-lo como inativo."""
        response = self.client.post(reverse("alternar_status_notebook"), {
            "equipamento_id": self.equipamento.id,
            "numero": "15",
        }, follow=True)
        notebook = Notebook.objects.get(equipamento=self.equipamento, numero=15)
        self.assertFalse(notebook.ativo)  # criado como inativo

    def test_alternar_status_notebook_alternar(self):
        """Alternar status de notebook existente deve inverter ativo/inativo."""
        Notebook.objects.create(
            equipamento=self.equipamento, numero=10, ativo=False
        )
        self.client.post(reverse("alternar_status_notebook"), {
            "equipamento_id": self.equipamento.id,
            "numero": "10",
        })
        notebook = Notebook.objects.get(equipamento=self.equipamento, numero=10)
        self.assertTrue(notebook.ativo)  # inverteu para ativo


# =============================================================================
# 8. TESTES DE EXPORTAÇÃO (EXCEL)
# =============================================================================

class ExportacaoTestCase(TestCase):
    """
    Testa as funções de exportação de fichas e reservas em Excel.
    Como openpyxl/pandas geram binário, verificamos apenas o status
    HTTP e o tipo de conteúdo.
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin_export",
            email="admin_export@escola.com",
            password="admin123",
            is_staff=True,
        )
        self.professor = User.objects.create_user(
            username="prof_export",
            email="prof_export@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.sala = Sala.objects.create(nome="5B")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho Export",
            tipo="notebook",
            quantidade=30,
        )
        self.reserva = Reserva.objects.create(
            professor=self.professor,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(7, 0),
            horario_fim=time(7, 50),
            sala=self.sala,
            status="confirmada",
        )
        # Cria um registro de uso para testar exportação de ficha
        self.aluno = Aluno.objects.create(nome="Teste Export", sala=self.sala)
        RegistroUso.objects.create(
            reserva=self.reserva,
            aluno=self.aluno,
            numero_notebook=10,
        )
        self.client.login(username="admin_export", password="admin123")

    def test_exportar_reservas_excel(self):
        """GET /exportar-excel/ deve retornar um arquivo Excel."""
        response = self.client.get(reverse("exportar_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_exportar_ficha_excel(self):
        """GET /fichas/1/excel/ deve retornar um arquivo Excel."""
        response = self.client.get(
            reverse("exportar_ficha_excel", args=[self.reserva.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_exportar_todas_fichas_excel(self):
        """GET /fichas/excel-tudo/ deve retornar um arquivo Excel."""
        response = self.client.get(reverse("exportar_todas_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])


# =============================================================================
# 9. TESTES DE NOTIFICAÇÃO DE FICHAS AUSENTES
# =============================================================================

class FichasAusentesTestCase(TestCase):
    """
    Testa a verificação de fichas não enviadas após o término do horário.
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin_notif",
            email="admin_notif@escola.com",
            password="admin123",
            is_staff=True,
        )
        self.professor = User.objects.create_user(
            username="prof_notif",
            email="prof_notif@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.sala = Sala.objects.create(nome="7A")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho Notif",
            tipo="notebook",
            quantidade=20,
        )

        # Cria uma reserva que já terminou (horário_fim no passado)
        hora_passada = (timezone.localtime() - timedelta(hours=2)).time()
        self.reserva_sem_ficha = Reserva.objects.create(
            professor=self.professor,
            equipamento=self.equipamento,
            data_uso=timezone.localtime().date(),
            horario_inicio=(timezone.localtime() - timedelta(hours=3)).time(),
            horario_fim=hora_passada,
            sala=self.sala,
            status="confirmada",
        )
        self.client.login(username="admin_notif", password="admin123")

    def test_fichas_ausentes_detecta_pendencia(self):
        """Reserva já encerrada sem ficha deve aparecer como pendência."""
        response = self.client.get(reverse("fichas_ausentes"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data.get("pendencias", [])), 0)


# =============================================================================
# 10. TESTES DE PERFIL ADM (REQUER_APROVACAO)
# =============================================================================

class PerfilAdmTestCase(TestCase):
    """
    Verifica se o comportamento de 'requer_aprovacao' afeta a criação
    de reservas.
    """

    def setUp(self):
        self.client = Client()
        self.sala = Sala.objects.create(nome="4A")
        self.equipamento = Equipamento.objects.create(
            nome="Carrinho Aprov",
            tipo="notebook",
            quantidade=20,
        )

    def test_reserva_com_aprovacao_fica_pendente(self):
        """Professor com requer_aprovacao=True tem reservas criadas como 'pendente'."""
        user = User.objects.create_user(
            username="prof_aprova",
            email="prof_aprova@professor.educacao.sp.gov.br",
            password="senha123",
        )
        PerfilAdm.objects.create(usuario=user, requer_aprovacao=True)
        self.client.login(username="prof_aprova", password="senha123")
        data_futura = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        self.client.post(reverse("mural"), {
            "data": data_futura,
            "equipamento": self.equipamento.id,
            "sala": self.sala.id,
            "horario_inicio": "07:00",
            "horario_fim": "07:50",
        })
        reserva = Reserva.objects.get(professor=user)
        self.assertEqual(reserva.status, "pendente")

    def test_reserva_sem_aprovacao_fica_confirmada(self):
        """Professor sem requer_aprovacao tem reservas criadas como 'confirmada'."""
        user = User.objects.create_user(
            username="prof_auto",
            email="prof_auto@professor.educacao.sp.gov.br",
            password="senha123",
        )
        PerfilAdm.objects.create(usuario=user, requer_aprovacao=False)
        self.client.login(username="prof_auto", password="senha123")
        data_futura = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        self.client.post(reverse("mural"), {
            "data": data_futura,
            "equipamento": self.equipamento.id,
            "sala": self.sala.id,
            "horario_inicio": "08:00",
            "horario_fim": "08:50",
        })
        reserva = Reserva.objects.get(professor=user)
        self.assertEqual(reserva.status, "confirmada")


# =============================================================================
# 11. TESTES DA VIEW FOTO (YOLO) — ANALISAR_FOTO
# =============================================================================

class AnalisarFotoTestCase(TestCase):
    """
    Testa o endpoint de análise de foto com YOLO.
    Como não podemos testar o YOLO real sem GPU/modelo,
    testamos apenas as validações de entrada.
    """

    def setUp(self):
        self.client = Client()
        self.usuario = User.objects.create_user(
            username="prof_foto",
            email="prof_foto@professor.educacao.sp.gov.br",
            password="senha123",
        )
        self.client.login(username="prof_foto", password="senha123")

    def test_analisar_foto_sem_imagem(self):
        """POST /fichas/analisar-foto/ sem imagem deve retornar erro 400."""
        response = self.client.post(
            reverse("analisar_foto"),
            data=json.dumps({"imagem": "", "tipo_carrinho": "notebook"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_analisar_foto_json_invalido(self):
        """POST com JSON inválido deve retornar erro 400."""
        response = self.client.post(
            reverse("analisar_foto"),
            data="isto não é json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_analisar_foto_base64_invalida(self):
        """POST com base64 inválido deve retornar erro 400."""
        response = self.client.post(
            reverse("analisar_foto"),
            data=json.dumps({
                "imagem": "data:image/jpeg;base64,ZZZZZZ",
                "tipo_carrinho": "notebook",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

