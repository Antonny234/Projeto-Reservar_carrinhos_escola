from django import forms
from django_select2 import forms as s2forms
from .models import Reserva, Sala
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.db import transaction
import uuid
import unicodedata
from .models import Equipamento,HorarioAula,BloqueioEquipamento,GrupoEquipamento, EquipamentoInventario, Transferencia
from .models import Escola, PerfilProfessor

# Essa classe customiza como o nome do professor aparece na lista
# Em vez de mostrar só o "username", mostra "Nome Completo (username)"
class ProfessorWidget(s2forms.ModelSelect2Widget):
    model = User
    search_fields = ['username__icontains', 'first_name__icontains', 'last_name__icontains']

    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} ({obj.username})" if nome else obj.username

class ReservaForm(forms.ModelForm):
    def __init__(self, *args, escola=None, **kwargs):
        super().__init__(*args, **kwargs)
        if escola:
            professores_da_escola = User.objects.filter(
                Q(perfil_professor__escola=escola) |
                Q(perfil_escola__escolas=escola)
            ).distinct().order_by('username')
            self.fields['professor'].queryset = professores_da_escola
            self.fields['sala'].queryset = Sala.objects.filter(escola=escola).order_by('nome')
            self.fields['equipamento'].queryset = Equipamento.objects.filter(escola=escola).order_by('nome')

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

    def __init__(self, *args, escola=None, **kwargs):
        super().__init__(*args, **kwargs)
        if escola:
            self.fields['professor'].queryset = User.objects.filter(
                Q(perfil_professor__escola=escola) |
                Q(perfil_escola__escolas=escola)
            ).distinct().order_by('username')
            self.fields['sala'].queryset = Sala.objects.filter(escola=escola).order_by('nome')
            self.fields['equipamento'].queryset = Equipamento.objects.filter(escola=escola).order_by('nome')


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
        queryset=User.objects.none(),
        widget=ProfessorWidget(attrs={'data-placeholder': 'Buscar professor...'})
    )

    def __init__(self, *args, escola=None, **kwargs):
        super().__init__(*args, **kwargs)
        if escola is not None:
            self.fields['professor'].queryset = (
                User.objects.filter(
                    Q(perfil_professor__escola=escola)
                    | Q(perfil_escola__escolas=escola)
                )
                .distinct()
                .order_by('first_name', 'last_name', 'username')
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
            'nome': forms.TextInput(attrs={'placeholder': 'Ex.: Notebooks, Projetores, Tablets'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }


class TransferenciaForm(forms.Form):
    local_destino = forms.CharField(max_length=150, label='Novo local')
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Observação (opcional)'
    )
    
class EquipamentoInventarioForm(forms.ModelForm):
    def __init__(self, *args, escola=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.escola = escola
        if escola:
            self.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)
        dados = self.instance.dados_personalizados if self.instance and self.instance.pk else {}
        self.campos_configurados = normalizar_campos_inventario(escola.campos_inventario if escola else [])
        for indice, campo in enumerate(self.campos_configurados):
            nome_campo = f'dado_{indice}'
            kwargs = {
                'label': campo['nome'], 'required': True,
                'initial': dados.get(campo['nome'], ''),
                'widget': forms.TextInput(attrs={'class': 'form-control'}),
            }
            if campo['tipo'] == 'numero':
                self.fields[nome_campo] = forms.IntegerField(**kwargs)
            elif campo['tipo'] == 'texto':
                self.fields[nome_campo] = forms.RegexField(
                    regex=r'^[^\d]*$',
                    error_messages={'invalid': 'Este campo aceita somente letras/texto.'},
                    **kwargs,
                )
            else:
                self.fields[nome_campo] = forms.CharField(**kwargs)

    def save(self, commit=True):
        equipamento = super().save(commit=False)
        dados = {
            campo['nome']: self.cleaned_data[f'dado_{indice}']
            for indice, campo in enumerate(self.campos_configurados)
        }
        equipamento.dados_personalizados = dados
        valores_nativos = dados_para_campos_nativos(dados)
        equipamento.identificador = valores_nativos['identificador']
        equipamento.numero_patrimonio = valores_nativos['numero_patrimonio']
        equipamento.numero_serie = valores_nativos['numero_serie']
        equipamento.localizacao_atual = valores_nativos['localizacao_atual']
        if not equipamento.pk:
            equipamento.tipo = 'Inventario personalizado'
        if commit:
            equipamento.save()
            self.save_m2m()
        return equipamento

    class Meta:
        model = EquipamentoInventario
        fields = ['grupo']


class CadastroLoteEquipamentosForm(forms.Form):
    """Cadastra vários itens que pertencem ao mesmo grupo de uma só vez."""

    grupo = forms.ModelChoiceField(queryset=GrupoEquipamento.objects.none())
    dados_lote = forms.CharField(
        label='Equipamentos',
        widget=forms.Textarea(attrs={
            'rows': 9,
            'placeholder': 'Um equipamento por linha. Separe os campos por ponto e vírgula ou Tab.',
        }),
    )

    def __init__(self, *args, escola=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.campos_configurados = normalizar_campos_inventario(
            escola.campos_inventario if escola else []
        )
        if escola:
            self.fields['grupo'].queryset = GrupoEquipamento.objects.filter(escola=escola)

    @staticmethod
    def _separar_linha(linha):
        return [valor.strip() for valor in (linha.split('\t') if '\t' in linha else linha.split(';'))]

    def clean_dados_lote(self):
        linhas = [linha.strip() for linha in self.cleaned_data['dados_lote'].splitlines() if linha.strip()]
        if not linhas:
            raise forms.ValidationError('Informe pelo menos um equipamento.')

        registros = []
        for numero_linha, linha in enumerate(linhas, start=1):
            valores = self._separar_linha(linha)
            if len(valores) != len(self.campos_configurados):
                raise forms.ValidationError(
                    f'Linha {numero_linha}: informe {len(self.campos_configurados)} campo(s), '
                    'na mesma ordem do cabeçalho.'
                )
            registro = {}
            for campo, valor in zip(self.campos_configurados, valores):
                if not valor:
                    raise forms.ValidationError(f'Linha {numero_linha}: "{campo["nome"]}" é obrigatório.')
                if campo['tipo'] == 'numero' and not valor.isdigit():
                    raise forms.ValidationError(f'Linha {numero_linha}: "{campo["nome"]}" aceita somente números.')
                if campo['tipo'] == 'texto' and any(caractere.isdigit() for caractere in valor):
                    raise forms.ValidationError(f'Linha {numero_linha}: "{campo["nome"]}" aceita somente texto.')
                registro[campo['nome']] = valor
            registros.append(registro)
        return registros

    def save(self):
        grupo = self.cleaned_data['grupo']
        with transaction.atomic():
            equipamentos = [
                EquipamentoInventario(
                    grupo=grupo,
                    tipo='Inventario personalizado',
                    identificador=dados_para_campos_nativos(registro)['identificador'],
                    numero_patrimonio=dados_para_campos_nativos(registro)['numero_patrimonio'],
                    numero_serie=dados_para_campos_nativos(registro)['numero_serie'],
                    localizacao_atual=dados_para_campos_nativos(registro)['localizacao_atual'],
                    dados_personalizados=registro,
                )
                for registro in self.cleaned_data['dados_lote']
            ]
            EquipamentoInventario.objects.bulk_create(equipamentos)
        return equipamentos


def normalizar_campos_inventario(campos):
    """Mantém compatibilidade com configurações antigas, que eram só texto."""
    resultado = []
    for campo in campos or []:
        if isinstance(campo, str):
            campo = {'nome': campo, 'tipo': 'texto'}
        nome = campo.get('nome', '').strip()
        # Grupo já é escolhido no seletor do formulário; duplicá-lo como campo
        # personalizado causava a mensagem de validação exibida na tela.
        if nome and nome.casefold() != 'grupo':
            tipo = campo.get('tipo', 'texto')
            # IDs, números de série e patrimônio normalmente combinam letras,
            # números e hífens. Configurações antigas como "texto" não devem
            # impedir o cadastro desses identificadores.
            if nome.casefold() == 'local' or any(termo in nome.casefold() for termo in ('id', 'serial', 'série', 'serie', 'patrim')):
                tipo = 'ambos'
            resultado.append({'nome': nome, 'tipo': tipo})
    if not any(campo['nome'].casefold() == 'local' for campo in resultado):
        resultado.insert(0, {'nome': 'Local', 'tipo': 'ambos'})
    return resultado

def campo_nativo_do_inventario(nome):
    chave = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().casefold()
    chave = ''.join(caractere for caractere in chave if caractere.isalnum())
    if 'patrim' in chave:
        return 'numero_patrimonio'
    if 'serial' in chave or 'serie' in chave or chave in {'ns', 'numerodeserie'}:
        return 'numero_serie'
    if chave == 'id' or 'identif' in chave:
        return 'identificador'
    if chave.startswith('local'):
        return 'localizacao_atual'
    return None


def dados_para_campos_nativos(dados, padroes=None):
    padroes = padroes or {}
    valores = {
        'identificador': padroes.get('identificador', ''),
        'numero_patrimonio': padroes.get('numero_patrimonio', f'item-{uuid.uuid4().hex}'),
        'numero_serie': padroes.get('numero_serie', f'item-{uuid.uuid4().hex}'),
        'localizacao_atual': padroes.get('localizacao_atual', ''),
    }
    for nome, valor in dados.items():
        campo = campo_nativo_do_inventario(nome)
        if campo:
            valores[campo] = valor
    return valores

class EscolaForm(forms.ModelForm):
    class Meta:
        model = Escola
        fields = ['nome', 'cidade']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da escola'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade'}),
        }
        
class AdminEscolaForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label='Usuário do administrador',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: admin_escola'
        })
    )

    email = forms.EmailField(
        required=False,
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'E-mail do administrador'
        })
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha'
        })
    )

    password_confirm = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a senha'
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                'Este nome de usuário já está cadastrado.'
            )

        return username

    def clean(self):
        cleaned = super().clean()

        senha = cleaned.get('password')
        confirmacao = cleaned.get('password_confirm')

        if senha and confirmacao and senha != confirmacao:
            self.add_error(
                'password_confirm',
                'As senhas não coincidem.'
            )
        elif senha:
            try:
                validate_password(senha)
            except forms.ValidationError as exc:
                self.add_error('password', exc)

        return cleaned
class ProatsExistentesForm(forms.Form):
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_superuser=False).order_by('username'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
        label='PROATs já cadastrados',
    )

class NovoProatForm(forms.Form):
    username = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuário'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-mail (opcional)'})
    )
    whatsapp = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp (DDD+número)'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha'})
    )

    def clean(self):
        cleaned = super().clean()
        preenchido = any(cleaned.get(f) for f in ['username', 'whatsapp', 'password'])
        if preenchido:
            for campo in ['username', 'whatsapp', 'password']:
                if not cleaned.get(campo):
                    self.add_error(campo, 'Obrigatório se for cadastrar um novo PROAT.')
        return cleaned


NovoProatFormSet = forms.formset_factory(NovoProatForm, extra=3, can_delete=False)
