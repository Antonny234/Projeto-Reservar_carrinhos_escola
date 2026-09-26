from django.db import models
from django.contrib.auth.models import User
import secrets
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Escola(models.Model):
    nome = models.CharField("Nome da Escola", max_length=150, unique=True)
    cidade = models.CharField("Cidade", max_length=100, blank=True)
    campos_inventario = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Escola"
        verbose_name_plural = "Escolas"
        ordering = ['nome']


class PerfilProfessor(models.Model):
    """Dados extras do professor usados na verificação por WhatsApp
    (cadastro e redefinição de senha)."""
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='professores')
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_professor')
    whatsapp = models.CharField(
        "Número de WhatsApp", max_length=20,
        null=True, blank=True,
        help_text="Formato: DDD + número, ex: 11999998888"
    )
    cargo = models.CharField('Função', max_length=100, default='Professor')

    def __str__(self):
        return f"{self.usuario.username} - {self.whatsapp} ({self.escola.nome})"

    class Meta:
        verbose_name = "Perfil do Professor"
        verbose_name_plural = "Perfis dos Professores"
        # whatsapp único apenas dentro da mesma escola
        unique_together = ('escola', 'whatsapp')

class PerfilProfessorEscola(models.Model):
    """Extensão do perfil que permite professor trabalhar em múltiplas escolas.
    Usado quando o professor seleciona 2+ escolas no cadastro."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_escola')
    escolas = models.ManyToManyField(Escola, related_name='professores_multiplos', verbose_name='Escolas onde trabalha')
    escola_ativa = models.ForeignKey(
        Escola, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='professores_ativos_multiplos',
        verbose_name='Escola atualmente selecionada'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    cargo = models.CharField('Função', max_length=100, default='Professor')

    class Meta:
        verbose_name = 'Perfil Escola do Professor'
        verbose_name_plural = 'Perfis Escola dos Professores'

    def __str__(self):
        escolas_txt = ', '.join([e.nome for e in self.escolas.all()])
        return f"{self.usuario.username} - {escolas_txt}"


class CodigoVerificacao(models.Model):
    """Código de 4 dígitos enviado por WhatsApp — usado no cadastro
    e na redefinição de senha. Escopo de escola vem do próprio usuário."""
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
        codigo = f"{secrets.randbelow(10000):04d}"
        return cls.objects.create(
            usuario=usuario,
            codigo=codigo,
            tipo=tipo,
            expira_em=timezone.now() + timezone.timedelta(minutes=cls.MINUTOS_VALIDADE),
        )

    def valido(self):
        return (not self.usado) and timezone.now() <= self.expira_em

    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()}"

    class Meta:
        verbose_name = "Código de Verificação"
        verbose_name_plural = "Códigos de Verificação"


class PerfilAdm(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='administradores')
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_adm')
    requer_aprovacao = models.BooleanField(
        default=False,
        verbose_name="Reservas requerem aprovação de ADM"
    )
    pin_envio = models.CharField(
        "PIN de envio", max_length=128, blank=True, null=True,
        help_text="Senha de 4 dígitos para enviar fichas no tablet"
    )

    def __str__(self):
        return f"{self.usuario.username} - {'requer aprovação' if self.requer_aprovacao else 'automático'} ({self.escola.nome})"

    class Meta:
        verbose_name = "Perfil ADM"
        verbose_name_plural = "Perfis ADM"

class PerfilAdmEscola(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_adm_escola')
    escolas = models.ManyToManyField(Escola, related_name='administradores_multiplos', verbose_name='Escolas onde é admin')
    escola_ativa = models.ForeignKey(
        Escola, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='administradores_ativos_multiplos',
        verbose_name='Escola atualmente selecionada'
    )
    requer_aprovacao = models.BooleanField(default=False, verbose_name="Reservas requerem aprovação de ADM")
    pin_envio = models.CharField("PIN de envio", max_length=128, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        escolas_txt = ', '.join(e.nome for e in self.escolas.all())
        return f"{self.usuario.username} (Admin) - {escolas_txt}"

    class Meta:
        verbose_name = 'Perfil Admin (múltiplas escolas)'
        verbose_name_plural = 'Perfis Admin (múltiplas escolas)'


class Equipamento(models.Model):
    TIPO_CHOICES = [('tablet', 'Carrinho de Tablets'), ('notebook', 'Carrinho de Notebooks')]
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='equipamentos')
    nome = models.CharField("Nome do Carrinho", max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    disponivel = models.BooleanField(default=True)
    quantidade = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
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
        """Retorna a quantidade disponível, descontando unidades inativas quando houver numeração."""
        if self.numero_inicial is None or self.numero_final is None:
            return self.quantidade
        total = self.numero_final - self.numero_inicial + 1
        inativos = Notebook.objects.filter(
            equipamento=self, ativo=False
        ).count()
        return max(total - inativos, 0)

    def clean(self):
        super().clean()
        if self.numero_inicial is not None and self.numero_final is not None:
            if self.numero_final < self.numero_inicial:
                raise ValidationError({
                    "numero_final": "O número final deve ser maior ou igual ao número inicial."
                })

    def status_numeros(self):
        """Retorna uma lista de dicts {numero, ativo} para cada número da faixa,
        cruzando com os registros de Notebook marcados manualmente como quebrados."""
        inativos = set(
            Notebook.objects.filter(equipamento=self, ativo=False).values_list('numero', flat=True)
        )
        return [{'numero': n, 'ativo': n not in inativos} for n in self.lista_numeros()]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()}) - {self.escola.nome}"

    class Meta:
        # nome do carrinho único dentro da mesma escola (duas escolas podem
        # ter, cada uma, um carrinho chamado "Carrinho 1")
        unique_together = ('escola', 'nome')


class Notebook(models.Model):
    # Escola herdada via equipamento.escola — não duplicamos o campo aqui.
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='notebooks')
    numero = models.PositiveIntegerField()
    ativo = models.BooleanField(default=True, verbose_name="Está funcionando")

    class Meta:
        unique_together = ('equipamento', 'numero')

    def __str__(self):
        status = "ativo" if self.ativo else "quebrado"
        return f"{self.equipamento.nome} - Notebook {self.numero} ({status})"


class Sala(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='salas')
    nome = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nome} - {self.escola.nome}"

    class Meta:
        unique_together = ('escola', 'nome')


class Reserva(models.Model):
    STATUS_CHOICES = [
        ('confirmada', 'Confirmada'),
        ('pendente', 'Pendente de Aprovação'),
        ('recusada', 'Recusada'),
    ]
    # Denormalizado de propósito (mesmo já vindo de equipamento/professor)
    # para permitir filtrar reservas por escola com uma única query rápida
    # e para servir de trava extra contra misturar dados entre escolas.
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='reservas')
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

    def clean(self):
        """Garante que equipamento e sala pertencem à mesma escola da reserva."""
        from django.core.exceptions import ValidationError
        erros = {}
        if self.horario_inicio and self.horario_fim and self.horario_fim <= self.horario_inicio:
            erros["horario_fim"] = "O horário final deve ser posterior ao horário inicial."
        if self.quantidade is not None and self.quantidade <= 0:
            erros["quantidade"] = "A quantidade deve ser maior que zero."
        if self.numero_notebook_unico is not None and self.quantidade is not None:
            erros["quantidade"] = "Uma reserva não pode usar número individual e quantidade ao mesmo tempo."
        if self.equipamento_id and self.equipamento.escola_id != self.escola_id:
            erros['equipamento'] = "Este equipamento pertence a outra escola."
        if self.sala_id and self.sala.escola_id != self.escola_id:
            erros['sala'] = "Esta sala pertence a outra escola."
        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return f"{self.professor.username} - {self.equipamento.nome} [{self.status}] ({self.escola.nome})"

    class Meta:
        indexes = [
            models.Index(fields=["escola", "data_uso", "horario_inicio", "horario_fim"]),
            models.Index(fields=["equipamento", "data_uso", "horario_inicio", "horario_fim", "status"]),
            models.Index(fields=["professor", "data_uso"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="recusada")
                    | models.Q(horario_fim__gt=models.F("horario_inicio"))
                ),
                name="reserva_horario_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade__isnull=True) | models.Q(quantidade__gt=0),
                name="reserva_quantidade_positiva",
            ),
            models.UniqueConstraint(
                fields=["escola", "equipamento", "data_uso", "horario_inicio", "horario_fim"],
                condition=(
                    models.Q(status__in=["confirmada", "pendente"])
                    & models.Q(numero_notebook_unico__isnull=True)
                    & models.Q(quantidade__isnull=True)
                ),
                name="unique_carrinho_inteiro_horario_ativo",
            ),
        ]


class HorarioAula(models.Model):
    PERIODO_CHOICES = [
        ('manha_tarde', '1º Período Manhã/Tarde'),
        ('tarde_noite', '2º Período Tarde/Noite'),
    ]

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='horarios_aula')
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
        unique_together = ('escola', 'periodo', 'numero')

    def __str__(self):
        return f"{self.get_periodo_display()} - {self.numero}º horário ({self.horario_inicio.strftime('%H:%M')} - {self.horario_fim.strftime('%H:%M')}) - {self.escola.nome}"


class NumeroReservaQuantidade(models.Model):
    # Escola herdada via reserva.escola
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name='numeros_quantidade'
    )
    numero = models.PositiveIntegerField()

    class Meta:
        unique_together = ('reserva', 'numero')

    def __str__(self):
        return f"Reserva #{self.reserva_id} - Notebook {self.numero}"


class Aluno(models.Model):
    # Escola herdada via sala.escola
    nome = models.CharField(max_length=100)
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nome} ({self.sala.nome} - {self.sala.escola.nome})"


class RegistroUso(models.Model):
    # Escola herdada via reserva.escola
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    numero_notebook = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('reserva', 'aluno')


class NotificacaoFichaAusente(models.Model):
    # Escola herdada via reserva.escola
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reserva',)


class EquipamentoLiberado(models.Model):
    """Professor com passe livre para reservar este equipamento sem aprovação.
    Se o equipamento não tiver nenhum registro aqui, qualquer professor reserva
    normalmente (só entra a regra global de PerfilAdm.requer_aprovacao).
    Escola herdada via equipamento.escola."""
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='professores_liberados')
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipamentos_liberados')

    class Meta:
        unique_together = ('equipamento', 'professor')

    def __str__(self):
        return f"{self.professor.username} liberado para {self.equipamento.nome}"


class BloqueioEquipamento(models.Model):
    """Período em que um equipamento fica indisponível pra reserva (quebrado,
    manutenção, emprestado etc.). Escola herdada via equipamento.escola."""
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
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='grupos_equipamento')
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Grupo de Equipamento'
        verbose_name_plural = 'Grupos de Equipamento'
        unique_together = ('escola', 'nome')

    def __str__(self):
        return self.nome


class EquipamentoInventario(models.Model):
    dados_personalizados = models.JSONField(default=dict, blank=True)
    # Escola herdada via grupo.escola
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
        max_length=50,
        verbose_name='Número de patrimônio',
        help_text="Número de identificação/patrimônio do equipamento"
    )
    numero_serie = models.CharField(max_length=100, verbose_name='N/S')
    localizacao_atual = models.CharField(max_length=150, verbose_name='Localização atual')
    comentario = models.TextField(blank=True, null=True, help_text="Observações opcionais")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['grupo__nome', 'tipo']
        verbose_name = 'Equipamento'
        verbose_name_plural = 'Equipamentos'
        # patrimônio e número de série únicos dentro do grupo (que já
        # pertence a uma única escola) — duas escolas podem ter, cada
        # uma, um equipamento com o mesmo número de patrimônio.
        unique_together = (
            ('grupo', 'numero_patrimonio'),
            ('grupo', 'numero_serie'),
        )

    def __str__(self):
        return f"{self.tipo} - Patrimônio {self.numero_patrimonio} ({self.grupo.escola.nome})"


class Transferencia(models.Model):
    # Escola herdada via equipamento.grupo.escola
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


class TransferenciaEscola(models.Model):
    """Transferência inter-escolar com recebimento explícito e trilha de auditoria."""
    STATUS = [('pendente', 'Pendente'), ('recebida', 'Recebida'), ('recusada', 'Recusada')]
    origem = models.ForeignKey(Escola, on_delete=models.PROTECT, related_name='transferencias_enviadas')
    destino = models.ForeignKey(Escola, on_delete=models.PROTECT, related_name='transferencias_recebidas')
    status = models.CharField(max_length=12, choices=STATUS, default='pendente')
    criada_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='transferencias_escola_criadas')
    recebida_por_nome = models.CharField(max_length=200, blank=True)
    recebida_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='transferencias_escola_conferidas')
    criada_em = models.DateTimeField(auto_now_add=True)
    recebida_em = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-criada_em']


class ItemTransferenciaEscola(models.Model):
    transferencia = models.ForeignKey(TransferenciaEscola, on_delete=models.CASCADE, related_name='itens')
    equipamento = models.ForeignKey(EquipamentoInventario, on_delete=models.PROTECT, related_name='movimentacoes_escola')
    identificador_tipo = models.CharField(max_length=20)
    identificador_valor = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['transferencia', 'equipamento'], name='unique_item_transferencia_escola')]


class TelegramBotEscola(models.Model):
    """Configuração de um bot Telegram exclusivo de uma escola."""
    escola = models.OneToOneField(
        Escola,
        on_delete=models.CASCADE,
        related_name='telegram_bot',
    )
    bot_username = models.CharField(max_length=64, blank=True)
    bot_nome = models.CharField(max_length=128, blank=True)
    bot_token_cifrado = models.TextField(blank=True)
    webhook_slug = models.CharField(max_length=96, unique=True, db_index=True)
    ativo = models.BooleanField(default=True)
    webhook_configurado = models.BooleanField(default=False)
    ultima_verificacao = models.DateTimeField(null=True, blank=True)
    ultimo_erro = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bot Telegram da Escola'
        verbose_name_plural = 'Bots Telegram das Escolas'

    def __str__(self):
        identificador = f'@{self.bot_username}' if self.bot_username else 'não configurado'
        return f'{self.escola.nome} — {identificador}'


class TelegramDestino(models.Model):
    """Chat (privado, grupo ou supergrupo) que receberá alertas da escola."""
    bot = models.ForeignKey(
        TelegramBotEscola,
        on_delete=models.CASCADE,
        related_name='destinos',
    )
    chat_id = models.CharField(max_length=64)
    nome = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)
    ultimo_envio = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Destino Telegram'
        verbose_name_plural = 'Destinos Telegram'
        constraints = [
            models.UniqueConstraint(
                fields=['bot', 'chat_id'],
                name='unique_telegram_destino_bot_chat',
            )
        ]
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome or self.chat_id} — {self.bot.escola.nome}'


class TelegramPareamento(models.Model):
    """Código temporário usado para vincular um chat ao bot da escola."""
    bot = models.ForeignKey(
        TelegramBotEscola,
        on_delete=models.CASCADE,
        related_name='pareamentos',
    )
    codigo_hash = models.CharField(max_length=64, db_index=True)
    expira_em = models.DateTimeField()
    usado_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pareamentos_telegram_criados',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pareamento Telegram'
        verbose_name_plural = 'Pareamentos Telegram'
        ordering = ['-criado_em']
