from django import forms
from django_select2 import forms as s2forms
from .models import Reserva, Sala
from django.contrib.auth.models import User

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