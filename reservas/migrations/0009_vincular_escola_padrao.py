from django.db import migrations

def popular_escola_padrao(apps, schema_editor):
    Escola = apps.get_model('reservas', 'Escola')
    PerfilProfessor = apps.get_model('reservas', 'PerfilProfessor')
    PerfilAdm = apps.get_model('reservas', 'PerfilAdm')

    # 1. Cria a escola atual no banco (ajuste o nome se desejar)
    escola_padrao, _ = Escola.objects.get_or_create(
        nome="Escola Principal"
    )

    # 2. Associa todos os professores e administradores existentes a essa escola
    PerfilProfessor.objects.filter(escola__isnull=True).update(escola=escola_padrao)
    PerfilAdm.objects.filter(escola__isnull=True).update(escola=escola_padrao)

class Migration(migrations.Migration):

    dependencies = [
        # Mantém a dependência gerada automaticamente pelo Django
        ('reservas', '0008_cargo_texto_livre'),
    ]

    operations = [
        migrations.RunPython(popular_escola_padrao, reverse_code=migrations.RunPython.noop),
    ]