from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone


class PerfilProfessor(models.Model):
    """Dados extras do professor usados na verificação por WhatsApp
    (cadastro e redefinição de senha)."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_professor')
    whatsapp = models.CharField(
        "Número de WhatsApp", max_length=20, unique=True,
        null=True, blank=True,
        help_text="Formato: DDD + número, ex: 11999998888"
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.whatsapp}"

    class Meta:
        verbose_name = "Perfil do Professor"
        verbose_name_plural = "Perfis dos Professores"


class CodigoVerificacao(models.Model):
    """Código de 4 dígitos enviado por WhatsApp — usado no cadastro
    e na redefinição de senha."""
    TIPO_CHOICES = [
        ('cadastro', 'Confirmação de Cadastro'),
        ('redefinicao', 'Redefinição de Senha'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='codigos_verificacao')
    codigo = models.CharField(max_length=4)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    usado = models.BooleanField(default=False)

    MINUTOS_VALIDADE = 15

    @classmethod
    def gerar(cls, usuario, tipo):
        cls.objects.filter(usuario=usuario, tipo=tipo, usado=False).update(usado=True)
        codigo = f"{random.randint(0, 9999):04d}"
        return cls.objects.create(
            usuario=usuario,
            codigo=codigo,
            tipo=tipo,
            expira_em=timezone.now() + timezone.timedelta(minutes=cls.MINUTOS_VALIDADE),
        )

    def valido(self):
        return (not self.usado) and timezone.now() <= self.expira_em

    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()} - {self.codigo}"

    class Meta:
        verbose_name = "Código de Verificação"
        verbose_name_plural = "Códigos de Verificação"


class PerfilAdm(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_adm')
    requer_aprovacao = models.BooleanField(
        default=False,
        verbose_name="Reservas requerem aprovação de ADM"
    )
    pin_envio = models.CharField(
        "PIN de envio (4 dígitos)", max_length=4, blank=True, null=True,
        help_text="Senha de 4 dígitos para enviar fichas no tablet"
    )

    def __str__(self):
        return f"{self.usuario.username} - {'requer aprovação' if self.requer_aprovacao else 'automático'}"

    class Meta:
        verbose_name = "Perfil ADM"
        verbose_name_plural = "Perfis ADM"


class Equipamento(models.Model):
    TIPO_CHOICES = [('tablet', 'Carrinho de Tablets'), ('notebook', 'Carrinho de Notebooks')]
    nome = models.CharField("Nome do Carrinho", max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    disponivel = models.BooleanField(default=True)
    quantidade = models.PositiveIntegerField(default=0)
    numero_inicial = models.PositiveIntegerField(
        "Nº inicial do notebook", null=True, blank=True,
        help_text="Primeiro número de notebook que pertence a este carrinho"
    )
    numero_final = models.PositiveIntegerField(
        "Nº final do notebook", null=True, blank=True,
        help_text="Último número de notebook que pertence a este carrinho"
    )

    def faixa_numeros(self):
        """Retorna o conjunto de números de notebook esperados para este carrinho."""
        if self.numero_inicial is None or self.numero_final is None:
            return set()
        return set(range(self.numero_inicial, self.numero_final + 1))

    def lista_numeros(self):
        """Retorna a lista ORDENADA de números (para exibir no template)."""
        return sorted(self.faixa_numeros())

    def quantidade_ativa(self):
        """Retorna a quantidade de notebooks ativos (não marcados como quebrados)."""
        if self.numero_inicial is None or self.numero_final is None:
            return 0
        total = self.numero_final - self.numero_inicial + 1
        inativos = Notebook.objects.filter(
            equipamento=self, ativo=False
        ).count()
        return total - inativos

    def status_numeros(self):
        """Retorna uma lista de dicts {numero, ativo} para cada número da faixa,
        cruzando com os registros de Notebook marcados manualmente como quebrados."""
        inativos = set(
            Notebook.objects.filter(equipamento=self, ativo=False).values_list('numero', flat=True)
        )
        return [{'numero': n, 'ativo': n not in inativos} for n in self.lista_numeros()]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Notebook(models.Model):
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='notebooks')
    numero = models.PositiveIntegerField()
    ativo = models.BooleanField(default=True, verbose_name="Está funcionando")

    class Meta:
        unique_together = ('equipamento', 'numero')

    def __str__(self):
        status = "ativo" if self.ativo else "quebrado"
        return f"{self.equipamento.nome} - Notebook {self.numero} ({status})"


class Sala(models.Model):
    nome = models.CharField(max_length=50)

    def __str__(self):
        return self.nome

class Reserva(models.Model):
    STATUS_CHOICES = [
        ('confirmada', 'Confirmada'),
        ('pendente', 'Pendente de Aprovação'),
        ('recusada', 'Recusada'),
    ]
    professor = models.ForeignKey(User, on_delete=models.CASCADE)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    data_uso = models.DateField("Data da Reserva")
    horario_inicio = models.TimeField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    horario_fim = models.TimeField()
    sala = models.ForeignKey('Sala', on_delete=models.PROTECT, verbose_name="Sala")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmada')
    numero_notebook_unico = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Nº do notebook (reserva individual)"
    )
    quantidade = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Quantidade reservada",
        help_text="Preenchido apenas nas reservas por quantidade específica."
    )

    numeracao_preenchida = models.BooleanField(
        default=False,
        verbose_name="Numeração dos notebooks preenchida"
    )

    grupo_fixo = models.UUIDField(null=True, blank=True, db_index=True)
    
    def __str__(self):
        return f"{self.professor.username} - {self.equipamento.nome} [{self.status}]"
    


# Adicionar esta classe no final do seu models.py existente

class HorarioAula(models.Model):
    PERIODO_CHOICES = [
        ('manha_tarde', '1º Período Manhã/Tarde'),
        ('tarde_noite', '2º Período Tarde/Noite'),
    ]

    numero = models.PositiveIntegerField(
        "Número do horário",
        help_text="Ordem de exibição dentro do período, ex: 1 para o 1º horário, 2 para o 2º horário..."
    )
    periodo = models.CharField(
        "Período",
        max_length=20,
        choices=PERIODO_CHOICES,
        default='manha_tarde',
    )
    horario_inicio = models.TimeField("Início")
    horario_fim = models.TimeField("Fim")
    ativo = models.BooleanField(
        default=True,
        verbose_name="Disponível para reserva",
        help_text="Desmarque para esconder este horário sem precisar excluir"
    )

    class Meta:
        ordering = ['periodo', 'numero']
        verbose_name = "Horário de Aula"
        verbose_name_plural = "Horários de Aula"

    def __str__(self):
        return f"{self.get_periodo_display()} - {self.numero}º horário ({self.horario_inicio.strftime('%H:%M')} - {self.horario_fim.strftime('%H:%M')})"

class NumeroReservaQuantidade(models.Model):
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name='numeros_quantidade'
    )
    numero = models.PositiveIntegerField()

    class Meta:
        unique_together = ('reserva', 'numero')

    def __str__(self):
        return f"Reserva #{self.reserva_id} - Notebook {self.numero}"

class Aluno(models.Model):
    nome = models.CharField(max_length=100)
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nome} ({self.sala.nome})"


class RegistroUso(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    numero_notebook = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('reserva', 'aluno')


class NotificacaoFichaAusente(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reserva',)
class EquipamentoLiberado(models.Model):
    """Professor com passe livre para reservar este equipamento sem aprovação.
    Se o equipamento não tiver nenhum registro aqui, qualquer professor reserva
    normalmente (só entra a regra global de PerfilAdm.requer_aprovacao)."""
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='professores_liberados')
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipamentos_liberados')

    class Meta:
        unique_together = ('equipamento', 'professor')

    def __str__(self):
        return f"{self.professor.username} liberado para {self.equipamento.nome}"


class BloqueioEquipamento(models.Model):
    """Período em que um equipamento fica indisponível pra reserva (quebrado, manutenção, emprestado etc.)."""
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='bloqueios')
    data = models.DateField("Data do bloqueio")
    horario_inicio = models.TimeField("Bloqueado a partir de")
    horario_fim = models.TimeField("Bloqueado até")
    motivo = models.CharField("Motivo", max_length=255, blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bloqueios_criados')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data', 'horario_inicio']

    def __str__(self):
        return f"{self.equipamento.nome} — {self.data.strftime('%d/%m/%Y')} {self.horario_inicio.strftime('%H:%M')}-{self.horario_fim.strftime('%H:%M')}"
    
class GrupoEquipamento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Grupo de Equipamento'
        verbose_name_plural = 'Grupos de Equipamento'

    def __str__(self):
        return self.nome


class EquipamentoInventario(models.Model):
    grupo = models.ForeignKey(
        GrupoEquipamento,
        on_delete=models.PROTECT,
        related_name='equipamentos'
    )
    identificador = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='ID',
        help_text="Identificador interno adicional (opcional)"
    )
    tipo = models.CharField(max_length=100, help_text="Ex: Notebook Dell, Tablet Samsung, Projetor Epson")
    numero_patrimonio = models.CharField(
        max_length=50, unique=True,
        verbose_name='Número de patrimônio',
        help_text="Número de identificação/patrimônio do equipamento"
    )
    numero_serie = models.CharField(max_length=100, unique=True, verbose_name='N/S')
    localizacao_atual = models.CharField(max_length=150, verbose_name='Localização atual')
    comentario = models.TextField(blank=True, null=True, help_text="Observações opcionais")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['grupo__nome', 'tipo']
        verbose_name = 'Equipamento'
        verbose_name_plural = 'Equipamentos'

    def __str__(self):
        return f"{self.tipo} - Patrimônio {self.numero_patrimonio}"


class Transferencia(models.Model):
    equipamento = models.ForeignKey(
        EquipamentoInventario,
        on_delete=models.CASCADE,
        related_name='transferencias'
    )
    local_origem = models.CharField(max_length=150)
    local_destino = models.CharField(max_length=150)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Transferência'
        verbose_name_plural = 'Transferências'

    def __str__(self):
        return f"{self.equipamento} | {self.local_origem} → {self.local_destino}"