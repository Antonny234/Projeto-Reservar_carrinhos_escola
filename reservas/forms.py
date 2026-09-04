from django import forms
from django_select2 import forms as s2forms
from .models import Reserva, Sala
from django.contrib.auth.models import User
from .models import Equipamento,HorarioAula,BloqueioEquipamento,GrupoEquipamento, EquipamentoInventario, Transferencia

# Essa classe customiza como o nome do professor aparece na lista
# Em vez de mostrar só o "username", mostra "Nome Completo (username)"
class ProfessorWidget(s2forms.ModelSelect2Widget):
    model = User
    search_fields = ['username__icontains', 'first_name__icontains', 'last_name__icontains']

    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} ({obj.username})" if nome else obj.username

class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['professor', 'sala', 'equipamento', 'data_uso', 'horario_inicio', 'horario_fim']
        widgets = {
            # Usa o widget customizado que mostra nome completo
            'professor': ProfessorWidget(
                attrs={'data-placeholder': 'Buscar professor...'}
            ),
            # Campo sala busca pelo nome cadastrado no banco
            'sala': s2forms.ModelSelect2Widget(
                model=Sala,
                search_fields=['nome__icontains'],
                attrs={'data-placeholder': 'Buscar sala...'}
            ),
        }
class ReservaFixaForm(forms.Form):
    DIAS_SEMANA = [
        ('0','Segundas'), ('1', 'Terça'), ('2', 'Quarta'),
        ('3', 'Quinta'), ('4', 'Sexta'),
    ]
    professor = forms.ModelChoiceField(queryset=User.objects.all(), widget=ProfessorWidget)
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        widget=s2forms.ModelSelect2Widget(model=Sala, search_fields=['nome__icontains'])
    )
    equipamento = forms.ModelChoiceField(queryset=Equipamento.objects.all())
    dias_semana = forms.MultipleChoiceField(choices=DIAS_SEMANA, widget=forms.CheckboxSelectMultiple)
    horario_inicio = forms.TimeField(widget=forms.TimeInput(attrs={'type':'time'}))
    horario_fim = forms.TimeField(widget=forms.TimeInput(attrs={'type':'time'}))
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    data_fim = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = ['nome', 'tipo', 'disponivel', 'quantidade', 'numero_inicial', 'numero_final']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Carrinho A'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'disponivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'numero_inicial': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'numero_final': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
        help_texts = {
            'quantidade': 'Use para carrinhos de tablets (quantidade total, sem numeração individual).',
            'numero_inicial': 'Use para carrinhos de notebooks com numeração individual (ex: notebooks 1 a 20).',
            'numero_final': 'Último número do notebook deste carrinho.',
        }

    def clean(self):
        cleaned = super().clean()
        ni = cleaned.get('numero_inicial')
        nf = cleaned.get('numero_final')
        if ni is not None and nf is not None and nf < ni:
            self.add_error('numero_final', 'O número final não pode ser menor que o número inicial.')
        return cleaned


class HorarioAulaForm(forms.ModelForm):
    class Meta:
        model = HorarioAula
        fields = ['numero', 'periodo', 'horario_inicio', 'horario_fim', 'ativo']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'periodo': forms.Select(attrs={'class': 'form-control'}),
            'horario_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horario_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'ativo': forms.CheckboxInput(),
        }

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('horario_inicio')
        fim = cleaned.get('horario_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('horario_fim', 'O horário final deve ser depois do horário inicial.')
        return cleaned
class EquipamentoLiberacaoForm(forms.Form):
    professor = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=ProfessorWidget(attrs={'data-placeholder': 'Buscar professor...'})
    )


class BloqueioEquipamentoForm(forms.ModelForm):
    class Meta:
        model = BloqueioEquipamento
        fields = ['data', 'horario_inicio', 'horario_fim', 'motivo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Em manutenção'}),
        }

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('horario_inicio')
        fim = cleaned.get('horario_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('horario_fim', 'O horário final deve ser depois do início.')
        return cleaned

class GrupoEquipamentoForm(forms.ModelForm):
    class Meta:
        model = GrupoEquipamento
        fields = ['nome', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }


class EquipamentoInventarioForm(forms.ModelForm):
    class Meta:
        model = EquipamentoInventario
        fields = ['grupo', 'tipo', 'numero_patrimonio', 'numero_serie', 'localizacao_atual', 'comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 3}),
        }


class TransferenciaForm(forms.Form):
    local_destino = forms.CharField(max_length=150, label='Novo local')
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Observação (opcional)'
    )
    
class EquipamentoInventarioForm(forms.ModelForm):
    class Meta:
        model = EquipamentoInventario
        fields = ['grupo', 'identificador', 'tipo', 'numero_patrimonio', 'numero_serie', 'localizacao_atual', 'comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 3}),
        }