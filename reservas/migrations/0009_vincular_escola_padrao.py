from django.db import migrations


def popular_escola_padrao(apps, schema_editor):
    Escola = apps.get_model('reservas', 'Escola')
    PerfilProfessor = apps.get_model('reservas', 'PerfilProfessor')

    # 1. Cria a escola padrão (Escola Principal)
    escola_padrao, _ = Escola.objects.get_or_create(nome="Escola Principal")

    # 2. Vincula apenas os professores existentes à escola padrão
    PerfilProfessor.objects.filter(escola__isnull=True).update(escola=escola_padrao)


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0008_cargo_texto_livre'),
    ]

    operations = [
        migrations.RunPython(popular_escola_padrao, reverse_code=migrations.RunPython.noop),
    ]