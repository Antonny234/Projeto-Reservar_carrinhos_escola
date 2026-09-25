"""Testes automatizados do app reservas.

Execucao:
    cd app
    python manage.py test reservas
"""
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import (
    CadastroLoteEquipamentosForm,
    EquipamentoInventarioForm,
    campo_nativo_do_inventario,
    dados_para_campos_nativos,
    normalizar_campos_inventario,
)

from reservas.models import Escola
from .models import (
    CodigoVerificacao,
    Equipamento,
    EquipamentoInventario,
    Escola,
    GrupoEquipamento,
    Notebook,
    PerfilAdm,
    PerfilProfessor,
    Reserva,
    Sala,
    Transferencia,
)
from .utils import filtrar_equipamentos, filtrar_reservas, filtrar_salas


CAMPOS_INVENTARIO = [
    {'nome': 'Local', 'tipo': 'ambos'},
    {'nome': 'Id', 'tipo': 'ambos'},
    {'nome': 'N-Serial', 'tipo': 'ambos'},
    {'nome': 'N Patrimonio', 'tipo': 'ambos'},
]

  # certifique-se de que o modelo Escola está importado

def obter_ou_criar_escola_teste():
    escola, _ = Escola.objects.get_or_create(
        nome="Escola Modelo de Teste"
    )
    return escola

def criar_professor(user=None, whatsapp="11999999999", escola=None):
    if escola is None:
        escola = obter_ou_criar_escola_teste()
    if user is None:
        # mantenha a criação do seu user padrão aqui...
        user = ... 
    
    return PerfilProfessor.objects.create(
        usuario=user,
        whatsapp=whatsapp,
        escola=escola  # <-- campo adicionado
    )

def criar_admin(user=None, pin="1234", requer_aprovacao=False, escola=None):
    if escola is None:
        escola = obter_ou_criar_escola_teste()
    if user is None:
        # mantenha a criação do seu user admin padrão aqui...
        user = ...

    return PerfilAdm.objects.create(
        usuario=user,
        pin_envio=pin,
        requer_aprovacao=requer_aprovacao,
        escola=escola  # <-- campo adicionado
    )
class BaseEscolaTestCase(TestCase):
    """Base com duas escolas para validar isolamento de dados."""

    def setUp(self):
        self.escola = Escola.objects.create(
            nome='Escola Teste', cidade='Sao Paulo', campos_inventario=CAMPOS_INVENTARIO
        )
        self.outra_escola = Escola.objects.create(
            nome='Outra Escola', cidade='Campinas', campos_inventario=CAMPOS_INVENTARIO
        )
        self.admin = User.objects.create_user('admin', password='Senha@123')
        PerfilAdm.objects.create(usuario=self.admin, escola=self.escola)
        self.professor = User.objects.create_user('professor', password='Senha@123')
        PerfilProfessor.objects.create(usuario=self.professor, escola=self.escola)
        self.grupo = GrupoEquipamento.objects.create(escola=self.escola, nome='Tablets')
        self.outro_grupo = GrupoEquipamento.objects.create(escola=self.outra_escola, nome='Tablets')

    def login_admin(self):
        self.client.force_login(self.admin)

    def dados_unitarios(self, grupo=None, **alteracoes):
        dados = {
            'grupo': str((grupo or self.grupo).pk),
            'dado_0': 'Carrinho 2',
            'dado_1': '32',
            'dado_2': '0562334623',
            'dado_3': '0154535623',
        }
        dados.update(alteracoes)
        return dados

    def criar_inventario(self, grupo=None, **alteracoes):
        valores = self.dados_unitarios(grupo, **alteracoes)
        dados = {
            'Local': valores['dado_0'],
            'Id': valores['dado_1'],
            'N-Serial': valores['dado_2'],
            'N Patrimonio': valores['dado_3'],
        }
        nativos = dados_para_campos_nativos(dados)
        return EquipamentoInventario.objects.create(
            grupo=grupo or self.grupo,
            tipo='Inventario personalizado',
            dados_personalizados=dados,
            **nativos,
        )


class InventarioNormalizacaoTest(TestCase):
    def test_local_e_identificadores_aceitam_letras_e_numeros(self):
        campos = normalizar_campos_inventario([
            {'nome': 'Grupo', 'tipo': 'texto'},
            {'nome': 'Local', 'tipo': 'texto'},
            {'nome': 'Id', 'tipo': 'texto'},
            {'nome': 'N-Serial', 'tipo': 'texto'},
            {'nome': 'N Patrimonio', 'tipo': 'texto'},
        ])
        self.assertEqual([campo['nome'] for campo in campos], ['Local', 'Id', 'N-Serial', 'N Patrimonio'])
        self.assertTrue(all(campo['tipo'] == 'ambos' for campo in campos))

    def test_local_e_adicionado_quando_ausente(self):
        campos = normalizar_campos_inventario([{'nome': 'Modelo', 'tipo': 'texto'}])
        self.assertEqual(campos[0], {'nome': 'Local', 'tipo': 'ambos'})

    def test_mapeia_campos_personalizados_para_campos_do_modelo(self):
        valores = dados_para_campos_nativos({
            'Local': 'Carrinho 2', 'Id': '32', 'N-Serial': '0562334623',
            'N Patrimonio': '0154535623',
        })
        self.assertEqual(valores['localizacao_atual'], 'Carrinho 2')
        self.assertEqual(valores['identificador'], '32')
        self.assertEqual(valores['numero_serie'], '0562334623')
        self.assertEqual(valores['numero_patrimonio'], '0154535623')

    def test_reconhece_variacoes_de_nome(self):
        self.assertEqual(campo_nativo_do_inventario('Numero de serie'), 'numero_serie')
        self.assertEqual(campo_nativo_do_inventario('Patrimonio'), 'numero_patrimonio')
        self.assertEqual(campo_nativo_do_inventario('Identificador'), 'identificador')
        self.assertIsNone(campo_nativo_do_inventario('Modelo'))


class FormularioInventarioTest(BaseEscolaTestCase):
    def test_formulario_unitario_salva_numeros_reais(self):
        form = EquipamentoInventarioForm(self.dados_unitarios(), escola=self.escola)
        self.assertTrue(form.is_valid(), form.errors)
        equipamento = form.save()
        self.assertEqual(equipamento.numero_patrimonio, '0154535623')
        self.assertEqual(equipamento.numero_serie, '0562334623')
        self.assertEqual(equipamento.identificador, '32')
        self.assertEqual(equipamento.localizacao_atual, 'Carrinho 2')

    def test_formulario_unitario_rejeita_grupo_de_outra_escola(self):
        form = EquipamentoInventarioForm(
            self.dados_unitarios(grupo=self.outro_grupo), escola=self.escola
        )
        self.assertFalse(form.is_valid())
        self.assertIn('grupo', form.errors)

    def test_cadastro_lote_cria_todos_os_equipamentos(self):
        form = CadastroLoteEquipamentosForm({
            'grupo': self.grupo.pk,
            'dados_lote': 'Carrinho 2;32;SER-01;PAT-01\nCarrinho 2;33;SER-02;PAT-02',
        }, escola=self.escola)
        self.assertTrue(form.is_valid(), form.errors)
        equipamentos = form.save()
        self.assertEqual(len(equipamentos), 2)
        self.assertEqual(EquipamentoInventario.objects.count(), 2)
        self.assertEqual(equipamentos[0].numero_serie, 'SER-01')
        self.assertEqual(equipamentos[1].numero_patrimonio, 'PAT-02')

    def test_cadastro_lote_informa_linha_com_colunas_invalidas(self):
        form = CadastroLoteEquipamentosForm({
            'grupo': self.grupo.pk,
            'dados_lote': 'Carrinho 2;32;SER-01',
        }, escola=self.escola)
        self.assertFalse(form.is_valid())
        self.assertIn('Linha 1', form.errors['dados_lote'][0])

    def test_cadastro_lote_rejeita_grupo_estrangeiro(self):
        form = CadastroLoteEquipamentosForm({
            'grupo': self.outro_grupo.pk,
            'dados_lote': 'Carrinho 2;32;SER-01;PAT-01',
        }, escola=self.escola)
        self.assertFalse(form.is_valid())
        self.assertIn('grupo', form.errors)


class InventarioViewsTest(BaseEscolaTestCase):
    def test_usuario_nao_autenticado_e_redirecionado(self):
        resposta = self.client.get(reverse('inventario_lista'))
        self.assertEqual(resposta.status_code, 302)

    def test_professor_nao_acessa_inventario_administrativo(self):
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('inventario_lista'))
        self.assertEqual(resposta.status_code, 403)

    def test_lista_exibe_somente_grupos_da_escola_ativa(self):
        self.login_admin()
        resposta = self.client.get(reverse('inventario_lista'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(self.grupo, list(resposta.context['grupos']))
        self.assertNotIn(self.outro_grupo, list(resposta.context['grupos']))

    def test_cadastro_unitario_redireciona_para_detalhe(self):
        self.login_admin()
        resposta = self.client.post(reverse('equipamento_novo'), self.dados_unitarios())
        equipamento = EquipamentoInventario.objects.get()
        self.assertRedirects(resposta, reverse('inventario_detalhe', args=[equipamento.pk]))
        self.assertEqual(equipamento.numero_patrimonio, '0154535623')

    def test_cadastro_em_lote_redireciona_para_grupo(self):
        self.login_admin()
        resposta = self.client.post(reverse('equipamento_novo'), {
            'cadastro_lote': '1', 'grupo': self.grupo.pk,
            'dados_lote': 'Carrinho 2;32;SER-01;PAT-01\nCarrinho 2;33;SER-02;PAT-02',
        })
        self.assertRedirects(resposta, reverse('grupo_equipamentos', args=[self.grupo.pk]))
        self.assertEqual(EquipamentoInventario.objects.count(), 2)

    def test_detalhe_mostra_numeros_digitados_sem_codigo_interno(self):
        equipamento = self.criar_inventario()
        self.login_admin()
        resposta = self.client.get(reverse('inventario_detalhe', args=[equipamento.pk]))
        self.assertContains(resposta, '0154535623')
        self.assertContains(resposta, '0562334623')
        self.assertNotContains(resposta, 'item-')

    def test_detalhe_oferece_cadastrar_outro_no_mesmo_grupo(self):
        equipamento = self.criar_inventario()
        self.login_admin()
        resposta = self.client.get(reverse('inventario_detalhe', args=[equipamento.pk]))
        self.assertContains(resposta, f'{reverse("equipamento_novo")}?grupo={self.grupo.pk}')

    def test_edicao_atualiza_campos_principais(self):
        equipamento = self.criar_inventario()
        self.login_admin()
        resposta = self.client.post(reverse('equipamento_editar', args=[equipamento.pk]), self.dados_unitarios(
            dado_1='33', dado_2='SER-NOVO', dado_3='PAT-NOVO'
        ))
        self.assertRedirects(resposta, reverse('inventario_detalhe', args=[equipamento.pk]))
        equipamento.refresh_from_db()
        self.assertEqual(equipamento.identificador, '33')
        self.assertEqual(equipamento.numero_serie, 'SER-NOVO')
        self.assertEqual(equipamento.numero_patrimonio, 'PAT-NOVO')

    def test_transferencia_registra_historico_e_atualiza_local(self):
        equipamento = self.criar_inventario()
        self.login_admin()
        resposta = self.client.post(reverse('transferir_equipamento', args=[equipamento.pk]), {
            'local_destino': 'Sala 12', 'observacao': 'Troca de sala',
        })
        self.assertRedirects(resposta, reverse('inventario_detalhe', args=[equipamento.pk]))
        equipamento.refresh_from_db()
        self.assertEqual(equipamento.localizacao_atual, 'Sala 12')
        transferencia = Transferencia.objects.get(equipamento=equipamento)
        self.assertEqual(transferencia.local_origem, 'Carrinho 2')
        self.assertEqual(transferencia.usuario, self.admin)

    def test_nao_acessa_item_de_outra_escola(self):
        estrangeiro = self.criar_inventario(grupo=self.outro_grupo, dado_2='SER-OUTRO', dado_3='PAT-OUTRO')
        self.login_admin()
        resposta = self.client.get(reverse('inventario_detalhe', args=[estrangeiro.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_exclusao_exige_post_e_remove_item(self):
        equipamento = self.criar_inventario()
        self.login_admin()
        url = reverse('equipamento_excluir', args=[equipamento.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        resposta = self.client.post(url)
        self.assertRedirects(resposta, reverse('inventario_lista'))
        self.assertFalse(EquipamentoInventario.objects.filter(pk=equipamento.pk).exists())

    def test_configuracao_rejeita_campos_duplicados(self):
        self.login_admin()
        resposta = self.client.post(reverse('configurar_campos_inventario'), {
            'nome_campo': ['Local', 'local'], 'tipo_campo': ['ambos', 'ambos'],
        }, follow=True)
        self.assertEqual(resposta.status_code, 200)
        self.escola.refresh_from_db()
        self.assertEqual(self.escola.campos_inventario, CAMPOS_INVENTARIO)


class ModelosEIsolamentoTest(BaseEscolaTestCase):
    def setUp(self):
        super().setUp()
        self.equipamento = Equipamento.objects.create(
            escola=self.escola, nome='Carrinho 1', tipo='notebook', quantidade=5,
            numero_inicial=1, numero_final=5,
        )
        self.sala = Sala.objects.create(escola=self.escola, nome='Sala 1')

    def test_faixa_e_quantidade_ativa_de_notebooks(self):
        Notebook.objects.create(equipamento=self.equipamento, numero=3, ativo=False)
        self.assertEqual(self.equipamento.lista_numeros(), [1, 2, 3, 4, 5])
        self.assertEqual(self.equipamento.quantidade_ativa(), 4)
        self.assertEqual(self.equipamento.status_numeros()[2], {'numero': 3, 'ativo': False})

    def test_nome_de_equipamento_e_unico_por_escola(self):
        with self.assertRaises(IntegrityError):
            Equipamento.objects.create(escola=self.escola, nome='Carrinho 1', tipo='tablet')
        equipamento_outra = Equipamento.objects.create(
            escola=self.outra_escola, nome='Carrinho 1', tipo='tablet'
        )
        self.assertEqual(equipamento_outra.nome, 'Carrinho 1')

    def test_reserva_nao_aceita_equipamento_ou_sala_de_outra_escola(self):
        equipamento_estrangeiro = Equipamento.objects.create(
            escola=self.outra_escola, nome='Outro carrinho', tipo='tablet'
        )
        sala_estrangeira = Sala.objects.create(escola=self.outra_escola, nome='Outra sala')
        reserva = Reserva(
            escola=self.escola, professor=self.professor, equipamento=equipamento_estrangeiro,
            sala=sala_estrangeira, data_uso=date.today(), horario_inicio=time(8), horario_fim=time(9),
        )
        with self.assertRaises(ValidationError) as contexto:
            reserva.clean()
        self.assertIn('equipamento', contexto.exception.message_dict)
        self.assertIn('sala', contexto.exception.message_dict)

    def test_filtros_de_utils_respeitam_escola_ativa(self):
        equipamento_estrangeiro = Equipamento.objects.create(
            escola=self.outra_escola, nome='Outro carrinho', tipo='tablet'
        )
        class Request:
            escola_ativa = self.escola
        self.assertEqual(list(filtrar_equipamentos(Request())), [self.equipamento])
        self.assertEqual(list(filtrar_salas(Request())), [self.sala])
        self.assertNotIn(equipamento_estrangeiro, filtrar_equipamentos(Request()))

    def test_codigo_de_verificacao_expira_e_pode_ser_usado(self):
        codigo = CodigoVerificacao.gerar(self.professor, 'cadastro')
        self.assertTrue(codigo.valido())
        codigo.usado = True
        codigo.save(update_fields=['usado'])
        self.assertFalse(codigo.valido())
        codigo.expira_em = timezone.now() - timedelta(minutes=1)
        codigo.usado = False
        codigo.save(update_fields=['expira_em', 'usado'])
        self.assertFalse(codigo.valido())

    def test_reservas_sao_filtradas_por_escola(self):
        reserva = Reserva.objects.create(
            escola=self.escola, professor=self.professor, equipamento=self.equipamento,
            sala=self.sala, data_uso=date.today(), horario_inicio=time(8), horario_fim=time(9),
        )
        class Request:
            escola_ativa = self.escola
        self.assertEqual(list(filtrar_reservas(Request())), [reserva])