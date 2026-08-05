from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from reservas.models import Reserva, Sala, Equipamento


Reserva_Fixas_Manha = [
    {"professor_username": "Priscila Matos", "equipamento_nome": "carrinho 4", "sala_nome": "9A", "dia_semana": 0, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "carrinho 4", "sala_nome": "9A", "dia_semana": 0, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3B", "dia_semana": 0, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "7A", "dia_semana": 0, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "2C", "dia_semana": 0, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "8A", "dia_semana": 0, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "2C", "dia_semana": 0, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3D", "dia_semana": 0, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "8A", "dia_semana": 0, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "9A", "dia_semana": 0, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2A", "dia_semana": 1, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2B", "dia_semana": 1, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Maritça", "equipamento_nome": "Carrinho 3", "sala_nome": "2C", "dia_semana": 1, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2A", "dia_semana": 1, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "7A", "dia_semana": 1, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Bruna Nascimento", "equipamento_nome": "Carrinho 2", "sala_nome": "1A", "dia_semana": 1, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3A", "dia_semana": 1, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3A", "dia_semana": 1, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1A", "dia_semana": 1, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "3A", "dia_semana": 2, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "Daiane Lopes", "equipamento_nome": "Carrinho 6", "sala_nome": "2B", "dia_semana": 2, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "3D", "dia_semana": 2, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "9A", "dia_semana": 2, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Bruna Nascimento", "equipamento_nome": "Carrinho 5", "sala_nome": "3D", "dia_semana": 2, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Roberto", "equipamento_nome": "Carrinho 2", "sala_nome": "7A", "dia_semana": 2, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "carlos", "equipamento_nome": "Carrinho 1", "sala_nome": "2A", "dia_semana": 2, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1A", "dia_semana": 2, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "9A", "dia_semana": 2, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Bruna Nascimento", "equipamento_nome": "Carrinho 1", "sala_nome": "8A", "dia_semana": 2, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3A", "dia_semana": 2, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "1A", "dia_semana": 2, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "7A", "dia_semana": 2, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "Daiane Lopes", "equipamento_nome": "Carrinho 6", "sala_nome": "2B", "dia_semana": 2, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "João", "equipamento_nome": "Carrinho 2", "sala_nome": "7A", "dia_semana": 2, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Sala de Informatica", "sala_nome": "8A", "dia_semana": 3, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "MARLI", "equipamento_nome": "Carrinho 3", "sala_nome": "3A", "dia_semana": 3, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3C", "dia_semana": 3, "hora_inicio": "07:00", "hora_fim": "07:50"},
    {"professor_username": "Bruna Nascimento", "equipamento_nome": "Carrinho 2", "sala_nome": "9A", "dia_semana": 3, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3B", "dia_semana": 3, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Roberto", "equipamento_nome": "Carrinho 1", "sala_nome": "2C", "dia_semana": 3, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3C", "dia_semana": 3, "hora_inicio": "07:50", "hora_fim": "08:40"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3D", "dia_semana": 3, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "MARLI", "equipamento_nome": "Carrinho 3", "sala_nome": "3B", "dia_semana": 3, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "carlos", "equipamento_nome": "Carrinho 1", "sala_nome": "2A", "dia_semana": 3, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "8A", "dia_semana": 3, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3D", "dia_semana": 3, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "MARLI", "equipamento_nome": "Carrinho 3", "sala_nome": "3C", "dia_semana": 3, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "7A", "dia_semana": 3, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2C", "dia_semana": 3, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3A", "dia_semana": 3, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2C", "dia_semana": 3, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informatica", "sala_nome": "3A", "dia_semana": 4, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "1A", "dia_semana": 4, "hora_inicio": "08:40", "hora_fim": "09:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2B", "dia_semana": 4, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3D", "dia_semana": 4, "hora_inicio": "09:50", "hora_fim": "10:40"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "3B", "dia_semana": 4, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informatica", "sala_nome": "3A", "dia_semana": 4, "hora_inicio": "10:40", "hora_fim": "11:30"},
    {"professor_username": "Tahynara Prata", "equipamento_nome": "Carrinho 2", "sala_nome": "8A", "dia_semana": 4, "hora_inicio": "11:40", "hora_fim": "11:30"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3C", "dia_semana": 4, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "7A", "dia_semana": 4, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informatica", "sala_nome": "3B", "dia_semana": 4, "hora_inicio": "12:20", "hora_fim": "13:10"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informatica", "sala_nome": "3B", "dia_semana": 4, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "3C", "dia_semana": 4, "hora_inicio": "13:10", "hora_fim": "14:00"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "8A", "dia_semana": 4, "hora_inicio": "13:10", "hora_fim": "14:00"},

]

Reservas_Fixas_Tarde = [
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 5", "sala_nome": "1F", "dia_semana": 0, "hora_inicio": "14:15", "hora_fim": "15:05"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 5", "sala_nome": "1F", "dia_semana": 0, "hora_inicio": "15:05", "hora_fim": "15:55"},
    {"professor_username": "Ewaldo", "equipamento_nome": "Carrinho 1", "sala_nome": "2D", "dia_semana": 0, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "Ewaldo", "equipamento_nome": "Carrinho 1", "sala_nome": "2D", "dia_semana": 0, "hora_inicio": "17:55", "hora_fim": "18:45"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 3", "sala_nome": "1B", "dia_semana": 0, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 5", "sala_nome": "1D", "dia_semana": 1, "hora_inicio": "14:15", "hora_fim": "15:05"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 5", "sala_nome": "1B", "dia_semana": 1, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1E", "dia_semana": 1, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1F", "dia_semana": 1, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1D", "dia_semana": 1, "hora_inicio": "17:55", "hora_fim": "18:45"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1D", "dia_semana": 1, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "Ana Maria", "equipamento_nome": "Carrinho 1", "sala_nome": "1B", "dia_semana": 1, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1F", "dia_semana": 1, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "Ana Maria", "equipamento_nome": "Carrinho 1", "sala_nome": "1B", "dia_semana": 1, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1D", "dia_semana": 1, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 1", "sala_nome": "1B", "dia_semana": 2, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 3", "sala_nome": "1E", "dia_semana": 2, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 1", "sala_nome": "1C", "dia_semana": 2, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1F", "dia_semana": 2, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "Ana Maria", "equipamento_nome": "Carrinho 5", "sala_nome": "2D", "dia_semana": 2, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1D", "dia_semana": 2, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "Daiane Lopes", "equipamento_nome": "Carrinho 6", "sala_nome": "2E", "dia_semana": 2, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "Ana Maria", "equipamento_nome": "Carrinho 1", "sala_nome": "2D", "dia_semana": 2, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1F", "dia_semana": 2, "hora_inicio": "20:25", "hora_fim": "21:15"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1C", "dia_semana": 3, "hora_inicio": "14:15", "hora_fim": "15:05"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1E", "dia_semana": 3, "hora_inicio": "15:05", "hora_fim": "15:55"},
    {"professor_username": "MarcusKiyota", "equipamento_nome": "Carrinho 5", "sala_nome": "1F", "dia_semana": 3, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informática", "sala_nome": "2D", "dia_semana": 3, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1C", "dia_semana": 3, "hora_inicio": "17:05", "hora_fim": "17:55"},
    {"professor_username": "João", "equipamento_nome": "Sala de Informática", "sala_nome": "2D", "dia_semana": 3, "hora_inicio": "17:55", "hora_fim": "18:45"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1C", "dia_semana": 3, "hora_inicio": "19:35", "hora_fim": "20:25"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2E", "dia_semana": 4, "hora_inicio": "14:15", "hora_fim": "15:05"},
    {"professor_username": "Juliana Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1D", "dia_semana": 4, "hora_inicio": "14:15", "hora_fim": "15:05"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1D", "dia_semana": 4, "hora_inicio": "15:05", "hora_fim": "15:55"},
    {"professor_username": "Priscila Matos", "equipamento_nome": "Carrinho 4", "sala_nome": "2E", "dia_semana": 4, "hora_inicio": "15:05", "hora_fim": "15:55"},
    {"professor_username": "Julia Bernardo", "equipamento_nome": "Carrinho 5", "sala_nome": "1E", "dia_semana": 4, "hora_inicio": "15:55", "hora_fim": "16:45"},
    {"professor_username": "Josy Nunes", "equipamento_nome": "Carrinho 4", "sala_nome": "1C", "dia_semana": 4, "hora_inicio": "17:55", "hora_fim": "18:45"},

]

Reservas_Fixas = Reserva_Fixas_Manha + Reservas_Fixas_Tarde

Data_Inicio = "2026-08-03"
Data_Fim = "2026-12-18"

Criar_Sala_se_nao_existir = True


class Command(BaseCommand):
    help = "Gerar Reservas fixas semanais (uma reserva por semana) até o fim do semestre."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="sem essa flag, o comando só mostra o que seria criado (modo simulado).",
        )

    def buscar_professor(self, username):
        """
        Busca o professor de forma tolerante:
        1) por username (case-insensitive)
        2) por nome completo (first_name + last_name), caso o username real
           seja diferente do nome usado na planilha/lista fixa.
        Levanta User.DoesNotExist se não achar de nenhuma forma, ou avisa se
        achar mais de um (em vez de estourar exception não tratada).
        """
        qs = User.objects.filter(username__iexact=username)
        if qs.count() == 1:
            return qs.first()
        if qs.count() > 1:
            raise User.MultipleObjectsReturned(
                f"Mais de um usuário com username parecido com '{username}'"
            )

        # fallback: tenta bater pelo nome completo
        partes = username.strip().split()
        if len(partes) >= 2:
            primeiro, resto = partes[0], " ".join(partes[1:])
            qs2 = User.objects.filter(first_name__iexact=primeiro, last_name__iexact=resto)
            if qs2.count() == 1:
                return qs2.first()
            if qs2.count() > 1:
                raise User.MultipleObjectsReturned(
                    f"Mais de um usuário com nome parecido com '{username}'"
                )

        raise User.DoesNotExist(username)

    def buscar_por_nome(self, model, nome):
        """
        Busca genérica case-insensitive (iexact) para Equipamento/Sala.
        Retorna (objeto, erro) onde erro é None, 'nao_encontrado' ou 'duplicado'.
        """
        qs = model.objects.filter(nome__iexact=nome.strip())
        count = qs.count()
        if count == 1:
            return qs.first(), None
        if count > 1:
            return None, "duplicado"
        return None, "nao_encontrado"

    def handle(self, *args, **options):
        confirmar = options["confirmar"]
        data_inicio_global = datetime.strptime(Data_Inicio, "%Y-%m-%d").date()
        data_fim_global = datetime.strptime(Data_Fim, "%Y-%m-%d").date()

        total_criadas = 0
        total_conflitos = 0
        total_erros = 0

        for item in Reservas_Fixas:
            # --- Professor ---
            try:
                professor = self.buscar_professor(item["professor_username"])
            except User.DoesNotExist:
                total_erros += 1
                self.stdout.write(self.style.ERROR(
                    f"[ERRO] Professor não encontrado: '{item['professor_username']}' "
                    f"(sala {item['sala_nome']}, dia {item['dia_semana']}, {item['hora_inicio']})"
                ))
                continue
            except User.MultipleObjectsReturned as e:
                total_erros += 1
                self.stdout.write(self.style.ERROR(f"[ERRO] {e}"))
                continue

            # --- Equipamento ---
            obj_equipamento, erro = self.buscar_por_nome(Equipamento, item["equipamento_nome"])
            if erro == "nao_encontrado":
                total_erros += 1
                self.stdout.write(self.style.ERROR(
                    f"[ERRO] Equipamento/Carrinho não encontrado: '{item['equipamento_nome']}'"
                ))
                continue
            if erro == "duplicado":
                total_erros += 1
                self.stdout.write(self.style.ERROR(
                    f"[ERRO] Mais de um Equipamento chamado '{item['equipamento_nome']}' no banco. "
                    f"Corrija os duplicados antes de rodar de novo."
                ))
                continue

            # --- Sala ---
            sala, erro = self.buscar_por_nome(Sala, item["sala_nome"])
            if erro == "duplicado":
                total_erros += 1
                self.stdout.write(self.style.ERROR(
                    f"[ERRO] Mais de uma Sala/turma chamada '{item['sala_nome']}' no banco."
                ))
                continue
            if erro == "nao_encontrado":
                if Criar_Sala_se_nao_existir:
                    if confirmar:
                        sala = Sala.objects.create(nome=item["sala_nome"])
                    else:
                        sala = None
                    self.stdout.write(
                        f"{'CRIADA' if confirmar else '[simulação]'} nova Sala/turma: {item['sala_nome']}"
                    )
                else:
                    total_erros += 1
                    self.stdout.write(self.style.ERROR(f"[ERRO] Sala/turma não encontrada: {item['sala_nome']}"))
                    continue

            item_inicio = (
                datetime.strptime(item["data_inicio"], "%Y-%m-%d").date()
                if item.get("data_inicio") else data_inicio_global
            )
            item_fim = (
                datetime.strptime(item["data_fim"], "%Y-%m-%d").date()
                if item.get("data_fim") else data_fim_global
            )
            data_atual = item_inicio
            dias_faltando = (item["dia_semana"] - data_atual.weekday()) % 7
            data_atual += timedelta(days=dias_faltando)

            while data_atual <= item_fim:
                existe = Reserva.objects.filter(
                    equipamento=obj_equipamento,
                    data_uso=data_atual,
                    horario_inicio=item["hora_inicio"],
                ).exists()

                if existe:
                    total_conflitos += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"CONFLITO: {obj_equipamento} em {data_atual} às {item['hora_inicio']} já reservado."
                        )
                    )
                else:
                    if confirmar:
                        Reserva.objects.create(
                            professor=professor,
                            equipamento=obj_equipamento,
                            sala=sala,
                            data_uso=data_atual,
                            horario_inicio=item["hora_inicio"],
                            horario_fim=item["hora_fim"],
                            status="confirmada",
                        )
                    total_criadas += 1
                    nome_sala = sala.nome if sala else item["sala_nome"]
                    self.stdout.write(
                        f"{'CRIADA' if confirmar else '[simulação]'}: {obj_equipamento} - {nome_sala} - {data_atual} "
                        f"{item['hora_inicio']} - {item['hora_fim']} ({professor})"
                    )
                data_atual += timedelta(days=7)

        # Resumo final - agora FORA do for, roda uma única vez no final de tudo
        self.stdout.write(self.style.SUCCESS(
            f"\nTotal: {total_criadas} reservas, {total_conflitos} conflitos, {total_erros} erros (itens pulados)."
        ))
        if not confirmar:
            self.stdout.write(self.style.NOTICE("rode com --confirmar para gravar de verdade no banco de dados."))