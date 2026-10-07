from django.contrib import admin
from django import forms
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from django.utils.html import format_html
from django.utils import timezone
from .models import Equipamento, Reserva, Aluno, RegistroUso, PerfilAdm, NotificacaoFichaAusente,Escola
from .models import GrupoEquipamento, EquipamentoInventario, Transferencia,Sala,PerfilProfessor, CodigoVerificacao, PerfilProfessorEscola, PerfilAdmEscola, TelegramBotEscola, TelegramDestino, TelegramPareamento
from django.utils.safestring import mark_safe


class AdminPinMixin:
    """Permite ao superuser definir um PIN novo sem expor o hash existente."""
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        return [field for field in fields if field not in ('pin_envio', 'pin_novo')]

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if not any('pin_novo' in options.get('fields', ()) for _, options in fieldsets):
            fieldsets.append(('PIN de envio', {'fields': ('pin_novo',)}))
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        if 'fields' in kwargs and kwargs['fields']:
            kwargs['fields'] = tuple(field for field in kwargs['fields'] if field != 'pin_novo')
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['pin_novo'] = forms.CharField(
            label='Definir novo PIN de envio',
            required=False,
            max_length=4,
            validators=[RegexValidator(r'^\d{4}$', 'Informe exatamente 4 dígitos numéricos.')],
            widget=forms.PasswordInput(render_value=False),
            help_text='Deixe em branco para manter o PIN atual. O PIN atual não pode ser exibido porque é armazenado com hash.',
        )
        return form

    def save_model(self, request, obj, form, change):
        pin = form.cleaned_data.get('pin_novo')
        if pin:
            obj.pin_envio = make_password(pin)
        super().save_model(request, obj, form, change)


@admin.register(PerfilAdm)
class PerfilAdmAdmin(AdminPinMixin, admin.ModelAdmin):
    list_display = ('usuario', 'requer_aprovacao', 'email_usuario')
    list_filter = ('requer_aprovacao',)
    search_fields = ('usuario__username', 'usuario__email')
    list_editable = ('requer_aprovacao',)

    def email_usuario(self, obj):
        return obj.usuario.email
    email_usuario.short_description = 'E-mail'

@admin.register(PerfilProfessorEscola)
class PerfilProfessorEscolaAdmin(AdminPinMixin, admin.ModelAdmin):
    list_display = ('usuario', 'escola_ativa', 'total_escolas', 'criado_em')
    list_filter = ('escolas', 'criado_em')
    search_fields = ('usuario__username', 'escolas__nome')
    filter_horizontal = ('escolas',)
    readonly_fields = ('criado_em', 'atualizado_em')
    fieldsets = (
        ('Usuário', {'fields': ('usuario',)}),
        ('Escolas', {'fields': ('escolas', 'escola_ativa')}),
        ('Datas', {'fields': ('criado_em', 'atualizado_em'), 'classes': ('collapse',)}),
    )

    def total_escolas(self, obj):
        return obj.escolas.count()
    total_escolas.short_description = 'Total de Escolas'


@admin.register(PerfilAdmEscola)
class PerfilAdmEscolaAdmin(AdminPinMixin, admin.ModelAdmin):
    list_display = ('usuario', 'escola_ativa', 'requer_aprovacao', 'atualizado_em')
    list_filter = ('escolas', 'requer_aprovacao')
    search_fields = ('usuario__username', 'escolas__nome')
    filter_horizontal = ('escolas',)
    
@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'quantidade', 'disponivel', 'status_badge')
    list_filter = ('tipo', 'disponivel')
    search_fields = ('nome',)
    readonly_fields = ('id',)
    fieldsets = (
        ('Informações Básicas', {'fields': ('id', 'nome', 'tipo')}),
        ('Disponibilidade', {'fields': ('disponivel', 'quantidade')}),
    )

    def status_badge(self, obj):
        if obj.disponivel:
            return mark_safe('<span style="color:green;font-weight:bold;">✓ Disponível</span>')
        return mark_safe('<span style="color:red;font-weight:bold;">✗ Indisponível</span>')
    status_badge.short_description = 'Status'


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('professor', 'equipamento', 'data_uso', 'horario_formatado', 'sala', 'status_badge', 'status_reserva')
    list_filter = ('data_uso', 'equipamento__tipo', 'professor', 'status', 'sala')
    search_fields = ('professor__username', 'equipamento__nome', 'sala__nome')
    readonly_fields = ('id', 'data_criacao')
    date_hierarchy = 'data_uso'
    autocomplete_fields = ('sala',)
    fieldsets = (
        ('Informações da Reserva', {'fields': ('id', 'professor', 'equipamento', 'sala', 'status')}),
        ('Data e Horário', {'fields': ('data_uso', 'horario_inicio', 'horario_fim')}),
        ('Metadados', {'fields': ('data_criacao',), 'classes': ('collapse',)}),
    )

    def horario_formatado(self, obj):
        if obj.horario_inicio and obj.horario_fim:
            return f"{obj.horario_inicio.strftime('%H:%M')} - {obj.horario_fim.strftime('%H:%M')}"
        return "N/A"
    horario_formatado.short_description = 'Horário'

    def status_badge(self, obj):
        cores = {
            'confirmada': ('#28a745', '✓ Confirmada'),
            'pendente': ('#ffc107', '⏳ Pendente'),
            'recusada': ('#dc3545', '✗ Recusada'),
        }
        cor, texto = cores.get(obj.status, ('#999', obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', cor, texto)
    status_badge.short_description = 'Aprovação'

    def status_reserva(self, obj):
        agora = timezone.localtime(timezone.now())
        if obj.data_uso > agora.date():
            return mark_safe('<span style="color:blue;font-weight:bold;">📅 Futura</span>')
        elif obj.data_uso == agora.date() and obj.horario_fim > agora.time():
            return mark_safe('<span style="color:orange;font-weight:bold;">⏳ Em andamento</span>')
        return mark_safe('<span style="color:gray;font-weight:bold;">✓ Concluída</span>')
    status_reserva.short_description = 'Situação'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('professor', 'equipamento')



@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sala')
    list_filter = ('sala',)
    search_fields = ('nome',)


@admin.register(RegistroUso)
class RegistroUsoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'reserva', 'numero_notebook')
    list_filter = ('reserva', 'aluno__sala')

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(PerfilProfessor)
class PerfilProfessorAdmin(AdminPinMixin, admin.ModelAdmin):
    list_display = ('usuario', 'whatsapp')
    search_fields = ('usuario__username', 'whatsapp')

@admin.register(CodigoVerificacao)
class CodigoVerificacaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'criado_em', 'expira_em', 'usado')
    list_filter = ('tipo', 'usado')
    search_fields = ('usuario__username',)
    exclude = ('codigo',)

@admin.register(GrupoEquipamento)
class GrupoEquipamentoAdmin(admin.ModelAdmin):
    list_display = ['nome']

@admin.register(EquipamentoInventario)
class EquipamentoInventarioAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'grupo', 'numero_patrimonio', 'numero_serie', 'localizacao_atual']
    list_filter = ['grupo']
    search_fields = ['numero_patrimonio', 'numero_serie', 'tipo']

@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ['equipamento', 'local_origem', 'local_destino', 'usuario', 'data']
    list_filter = ['data']

@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)
    ordering = ('nome',)

@admin.register(TelegramBotEscola)
class TelegramBotEscolaAdmin(admin.ModelAdmin):
    list_display = ('escola', 'bot_identificacao', 'ativo', 'webhook_configurado', 'ultima_verificacao')
    list_filter = ('ativo', 'webhook_configurado')
    search_fields = ('escola__nome', 'bot_username')
    readonly_fields = ('bot_token_cifrado', 'webhook_slug', 'criado_em', 'atualizado_em', 'ultima_verificacao')
    exclude = ('bot_token_cifrado',)

    @admin.display(description='Bot')
    def bot_identificacao(self, obj):
        return f'@{obj.bot_username}' if obj.bot_username else 'Não configurado'


@admin.register(TelegramDestino)
class TelegramDestinoAdmin(admin.ModelAdmin):
    list_display = ('bot', 'nome', 'chat_id', 'ativo', 'ultimo_envio')
    list_filter = ('ativo',)
    search_fields = ('nome', 'chat_id', 'bot__escola__nome')
    readonly_fields = ('criado_em', 'ultimo_envio')


@admin.register(TelegramPareamento)
class TelegramPareamentoAdmin(admin.ModelAdmin):
    list_display = ('bot', 'expira_em', 'usado_em', 'criado_por', 'criado_em')
    list_filter = ('usado_em',)
    search_fields = ('bot__escola__nome', 'criado_por__username')
    readonly_fields = ('codigo_hash', 'expira_em', 'usado_em', 'criado_por', 'criado_em')
