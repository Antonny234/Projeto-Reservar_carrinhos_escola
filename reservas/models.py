from django.db import models
from django.contrib.auth.models import User



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
    
    def __str__(self):
        return f"{self.professor.username} - {self.equipamento.nome} [{self.status}]"




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
