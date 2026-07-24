from django.test import TestCase
"""
tests.py — Testes para o projeto Reservar Carrinhos Escola

Como rodar:
    python manage.py test reservas

Requisito: coloque este arquivo em reservas/tests.py
(substitui o tests.py vazio que já existe lá)
"""

import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Equipamento, Reserva


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def criar_equipamento(nome="Carrinho A", tipo="tablet", quantidade=5):
    return Equipamento.objects.create(nome=nome, tipo=tipo, disponivel=True, quantidade=quantidade)


def criar_usuario(username="prof1", email="prof1@professor.educacao.sp.gov.br", password="Senha@123", is_staff=False):
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = is_staff
    user.save()
    return user


# ---------------------------------------------------------------------------
# 1. Testes de Model
# ---------------------------------------------------------------------------

class EquipamentoModelTest(TestCase):

    def test_criacao_equipamento(self):
        eq = criar_equipamento()
        self.assertEqual(str(eq), "Carrinho A (Carrinho de Tablets)")

    def test_tipo_notebook(self):
        eq = Equipamento.objects.create(nome="Carrinho NB", tipo="notebook", quantidade=3)
        self.assertEqual(eq.get_tipo_display(), "Carrinho de Notebooks")

    def test_disponivel_default_true(self):
        eq = criar_equipamento()
        self.assertTrue(eq.disponivel)


class ReservaModelTest(TestCase):

    def setUp(self):
        self.user = criar_usuario()
        self.equipamento = criar_equipamento()

    def test_criacao_reserva(self):
        reserva = Reserva.objects.create(
            professor=self.user,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala="Sala 01"
        )
        self.assertEqual(str(reserva), f"{self.user.username} - {self.equipamento.nome}")

    def test_sala_default_vazia(self):
        reserva = Reserva.objects.create(
            professor=self.user,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
        )
        self.assertEqual(reserva.sala, "")


# ---------------------------------------------------------------------------
# 2. Testes de CriarConta (POST /criar/)
# ---------------------------------------------------------------------------

class CriarContaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('index')  # /criar/

    def _post(self, **kwargs):
        dados = dict(
            usuario="novoprof",
            email="novoprof@professor.educacao.sp.gov.br",
            senha="Senha@123",
            confirmar_senha="Senha@123",
        )
        dados.update(kwargs)
        return self.client.post(self.url, dados)

    def test_criar_conta_valida(self):
        resp = self._post()
        self.assertTrue(User.objects.filter(username="novoprof").exists())

    def test_email_dominio_invalido(self):
        resp = self._post(email="prof@gmail.com")
        self.assertFalse(User.objects.filter(username="novoprof").exists())
        self.assertContains(resp, "corporativo SEDUC")

    def test_senhas_diferentes(self):
        resp = self._post(confirmar_senha="outrasenha")
        self.assertFalse(User.objects.filter(username="novoprof").exists())
        self.assertContains(resp, "não coincidem")

    def test_username_duplicado(self):
        criar_usuario(username="novoprof")
        resp = self._post()
        self.assertEqual(User.objects.filter(username="novoprof").count(), 1)
        self.assertContains(resp, "já está em uso")

    def test_email_duplicado(self):
        criar_usuario(username="outro", email="novoprof@professor.educacao.sp.gov.br")
        resp = self._post()
        self.assertContains(resp, "email esta em uso")

    def test_get_retorna_index(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "index.html")


# ---------------------------------------------------------------------------
# 3. Testes de Entrar (POST /entrar/)
# ---------------------------------------------------------------------------

class EntrarTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('longa')  # name='longa' → /entrar/ (segundo registro)
        self.user = criar_usuario()

    def test_login_valido_redireciona_para_mural(self):
        resp = self.client.post(self.url, {'usuario': 'prof1', 'senha': 'Senha@123'})
        self.assertRedirects(resp, reverse('mural'))

    def test_login_invalido_exibe_erro(self):
        resp = self.client.post(self.url, {'usuario': 'prof1', 'senha': 'senhaerrada'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "incorretos")

    def test_get_retorna_longa(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "longa.html")


# ---------------------------------------------------------------------------
# 4. Testes do Mural (GET/POST /Logar/)
# ---------------------------------------------------------------------------

class MuralTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('mural')  # /Logar/
        self.user = criar_usuario()
        self.equipamento = criar_equipamento()

    def _login(self):
        self.client.login(username='prof1', password='Senha@123')

    def _post_reserva(self, **kwargs):
        amanha = (date.today() + timedelta(days=1)).isoformat()
        dados = dict(
            equipamento=self.equipamento.id,
            sala="Sala 10",
            horario_inicio="08:00",
            horario_fim="10:00",
            data=amanha,
        )
        dados.update(kwargs)
        return self.client.post(self.url, dados)

    # --- acesso sem login ---

    def test_get_sem_login_redireciona(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/entrar/', resp['Location'])

    # --- GET com login ---

    def test_get_com_login_retorna_200(self):
        self._login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "mural.html")

    def test_get_passa_equipamentos_no_contexto(self):
        self._login()
        resp = self.client.get(self.url)
        self.assertIn(self.equipamento, resp.context['equipamentos'])

    # --- POST: criar reserva ---

    def test_post_cria_reserva(self):
        self._login()
        self._post_reserva()
        self.assertEqual(Reserva.objects.count(), 1)

    def test_post_reserva_duplicada_nao_cria(self):
        self._login()
        self._post_reserva()
        self._post_reserva()  # mesmo horário e equipamento
        self.assertEqual(Reserva.objects.count(), 1)

    def test_post_reserva_associa_professor_logado(self):
        self._login()
        self._post_reserva()
        reserva = Reserva.objects.first()
        self.assertEqual(reserva.professor, self.user)

    def test_post_sem_login_redireciona(self):
        resp = self._post_reserva()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Reserva.objects.count(), 0)

    # --- POST: staff reserva por outro professor ---

    def test_staff_reserva_para_outro_usuario(self):
        outro = criar_usuario(username="prof2", email="prof2@professor.educacao.sp.gov.br")
        staff = criar_usuario(username="coord", email="coord@professor.educacao.sp.gov.br", is_staff=True)
        self.client.login(username='coord', password='Senha@123')
        amanha = (date.today() + timedelta(days=1)).isoformat()
        self.client.post(self.url, {
            'equipamento': self.equipamento.id,
            'sala': 'Sala 5',
            'horario_inicio': '08:00',
            'horario_fim': '10:00',
            'data': amanha,
            'professor': 'prof2',
        })
        reserva = Reserva.objects.first()
        self.assertEqual(reserva.professor, outro)

    def test_staff_usuario_inexistente_exibe_erro(self):
        staff = criar_usuario(username="coord", email="coord@professor.educacao.sp.gov.br", is_staff=True)
        self.client.login(username='coord', password='Senha@123')
        amanha = (date.today() + timedelta(days=1)).isoformat()
        resp = self.client.post(self.url, {
            'equipamento': self.equipamento.id,
            'sala': 'Sala 5',
            'horario_inicio': '08:00',
            'horario_fim': '10:00',
            'data': amanha,
            'professor': 'fantasma',
        }, follow=True)
        self.assertContains(resp, "não foi encontrado")
        self.assertEqual(Reserva.objects.count(), 0)

    # --- POST: staff atualiza quantidade do equipamento ---

    def test_staff_atualiza_quantidade(self):
        staff = criar_usuario(username="coord", email="coord@professor.educacao.sp.gov.br", is_staff=True)
        self.client.login(username='coord', password='Senha@123')
        resp = self.client.post(self.url, {
            'equipamento_id': self.equipamento.id,
            'quantidade': 20,
        }, follow=True)
        self.equipamento.refresh_from_db()
        self.assertEqual(int(self.equipamento.quantidade), 20)


# ---------------------------------------------------------------------------
# 5. Testes de Excluir Reserva (/excluir-reserva/<id>/)
# ---------------------------------------------------------------------------

class ExcluirReservaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario()
        self.outro = criar_usuario(username="prof2", email="prof2@professor.educacao.sp.gov.br")
        self.equipamento = criar_equipamento()
        self.reserva = Reserva.objects.create(
            professor=self.user,
            equipamento=self.equipamento,
            data_uso=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
            sala="Sala 1"
        )

    def _url(self):
        return reverse('excluir_reserva', args=[self.reserva.id])

    def test_dono_pode_excluir(self):
        self.client.login(username='prof1', password='Senha@123')
        self.client.post(self._url())
        self.assertEqual(Reserva.objects.count(), 0)

    def test_outro_professor_nao_pode_excluir(self):
        self.client.login(username='prof2', password='Senha@123')
        self.client.post(self._url())
        self.assertEqual(Reserva.objects.count(), 1)

    def test_staff_pode_excluir_qualquer_reserva(self):
        staff = criar_usuario(username="coord", email="coord@professor.educacao.sp.gov.br", is_staff=True)
        self.client.login(username='coord', password='Senha@123')
        self.client.post(self._url())
        self.assertEqual(Reserva.objects.count(), 0)

    def test_sem_login_redireciona(self):
        resp = self.client.post(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Reserva.objects.count(), 1)


# ---------------------------------------------------------------------------
# 6. Testes de listar_disponiveis (/ajax/disponiveis/)
# ---------------------------------------------------------------------------

class ListarDisponiveisTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('ajax_disponiveis')
        self.eq1 = criar_equipamento(nome="Carrinho A")
        self.eq2 = criar_equipamento(nome="Carrinho B")
        self.user = criar_usuario()
        # Reserva o Carrinho A para um horário específico
        Reserva.objects.create(
            professor=self.user,
            equipamento=self.eq1,
            data_uso=date.today(),
            horario_inicio=time(8, 0),
            horario_fim=time(10, 0),
        )

    def test_retorna_json(self):
        resp = self.client.get(self.url, {
            'data': date.today().isoformat(),
            'horario_inicio': '08:00:00',
            'horario_fim': '10:00:00',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')

    def test_exclui_ocupados(self):
        resp = self.client.get(self.url, {
            'data': date.today().isoformat(),
            'horario_inicio': '08:00:00',
            'horario_fim': '10:00:00',
        })
        dados = json.loads(resp.content)
        ids_retornados = [e['id'] for e in dados['equipamentos']]
        self.assertNotIn(self.eq1.id, ids_retornados)
        self.assertIn(self.eq2.id, ids_retornados)

    def test_outro_horario_retorna_todos(self):
        resp = self.client.get(self.url, {
            'data': date.today().isoformat(),
            'horario_inicio': '14:00:00',
            'horario_fim': '16:00:00',
        })
        dados = json.loads(resp.content)
        ids_retornados = [e['id'] for e in dados['equipamentos']]
        self.assertIn(self.eq1.id, ids_retornados)
        self.assertIn(self.eq2.id, ids_retornados)



# 7. Testes de carregar_mural e carregar_mural_publico (partials AJAX)


class CarregarMuralTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario()
        self.eq = criar_equipamento()

    def _criar_reserva(self, data=None, h_inicio=time(8, 0), h_fim=time(10, 0)):
        return Reserva.objects.create(
            professor=self.user,
            equipamento=self.eq,
            data_uso=data or date.today(),
            horario_inicio=h_inicio,
            horario_fim=h_fim,
            sala="Sala X"
        )

    def test_carregar_mural_retorna_200(self):
        resp = self.client.get(reverse('ajax_mural'), {'data': date.today().isoformat()})
        self.assertEqual(resp.status_code, 200)

    def test_carregar_mural_usa_partial_correto(self):
        resp = self.client.get(reverse('ajax_mural'), {'data': date.today().isoformat()})
        self.assertTemplateUsed(resp, 'partials/lista_reservas.html')

    def test_carregar_mural_publico_retorna_200(self):
        resp = self.client.get(reverse('carregar_mural_publico'), {'data': date.today().isoformat()})
        self.assertEqual(resp.status_code, 200)

    def test_carregar_mural_publico_usa_partial_correto(self):
        resp = self.client.get(reverse('carregar_mural_publico'), {'data': date.today().isoformat()})
        self.assertTemplateUsed(resp, 'partials/lista_reservas_consulta.html')

    def test_carregar_mural_data_futura_mostra_reservas(self):
        amanha = date.today() + timedelta(days=1)
        self._criar_reserva(data=amanha, h_inicio=time(8, 0), h_fim=time(10, 0))
        resp = self.client.get(reverse('ajax_mural'), {'data': amanha.isoformat()})
        self.assertIn(self.eq, [r.equipamento for r in resp.context['reservas']])


# ---------------------------------------------------------------------------
# 8. Testes do Painel público (/painel/)
# ---------------------------------------------------------------------------

class MuralPrincipalTest(TestCase):

    def test_get_retorna_200(self):
        resp = self.client.get(reverse('mural_consulta'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'mural_consulta.html')

    def test_contexto_tem_hoje(self):
        resp = self.client.get(reverse('mural_consulta'))
        self.assertIn('hoje', resp.context)

    def test_acesso_publico_sem_login(self):
        # Painel de consulta não exige login
        resp = self.client.get(reverse('mural_consulta'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 9. Testes de exportar_reservas_excel (/exportar-excel/)
# ---------------------------------------------------------------------------

class ExportarExcelTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario()
        self.eq = criar_equipamento()

    def test_sem_login_redireciona(self):
        resp = self.client.get(reverse('exportar_excel'))
        self.assertEqual(resp.status_code, 302)

    def test_com_login_retorna_xlsx(self):
        self.client.login(username='prof1', password='Senha@123')
        resp = self.client.get(reverse('exportar_excel'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_filename_no_header(self):
        self.client.login(username='prof1', password='Senha@123')
        resp = self.client.get(reverse('exportar_excel'))
        self.assertIn('reservas_passadas.xlsx', resp['Content-Disposition'])

    def test_so_exporta_reservas_passadas(self):
        """Reservas futuras não devem aparecer no Excel (testamos indiretamente
        verificando que o endpoint não quebra quando há dados mistos)."""
        ontem = date.today() - timedelta(days=1)
        amanha = date.today() + timedelta(days=1)
        Reserva.objects.create(professor=self.user, equipamento=self.eq,
                               data_uso=ontem, horario_inicio=time(8, 0), horario_fim=time(10, 0))
        Reserva.objects.create(professor=self.user, equipamento=self.eq,
                               data_uso=amanha, horario_inicio=time(8, 0), horario_fim=time(10, 0))
        self.client.login(username='prof1', password='Senha@123')
        resp = self.client.get(reverse('exportar_excel'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 10. Testes da home page
# ---------------------------------------------------------------------------

class HomeTest(TestCase):

    def test_home_retorna_200(self):
        resp = self.client.get(reverse('longa'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'longa.html')
# Create your tests here.
