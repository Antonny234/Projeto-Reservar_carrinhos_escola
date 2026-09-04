from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Equipamento, Reserva, Aluno, RegistroUso, PerfilAdm, NotificacaoFichaAusente
from .models import GrupoEquipamento, EquipamentoInventario, Transferencia,Sala,PerfilProfessor, CodigoVerificacao
from django.utils.safestring import mark_safe


@admin.register(PerfilAdm)
class PerfilAdmAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'requer_aprovacao', 'email_usuario')
    list_filter = ('requer_aprovacao',)
    search_fields = ('usuario__username', 'usuario__email')
    list_editable = ('requer_aprovacao',)

    def email_usuario(self, obj):
        return obj.usuario.email
    email_usuario.short_description = 'E-mail'


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
class PerfilProfessorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'whatsapp')
    search_fields = ('usuario__username', 'whatsapp')

@admin.register(CodigoVerificacao)
class CodigoVerificacaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'codigo', 'criado_em', 'expira_em', 'usado')
    list_filter = ('tipo', 'usado')
    search_fields = ('usuario__username',)

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