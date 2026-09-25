from django.db import migrations


def popular_escola_padrao(apps, schema_editor):
    Escola = apps.get_model('reservas', 'Escola')
    PerfilProfessor = apps.get_model('reservas', 'PerfilProfessor')

    # 1. Garante a existência da escola padrão
    escola_padrao, _ = Escola.objects.get_or_create(nome="Escola Principal")

    # 2. Atualiza os professores
    PerfilProfessor.objects.filter(escola__isnull=True).update(escola=escola_padrao)

    # 3. Atualiza PerfilAdm apenas se o campo escola já estiver disponível na tabela
    try:
        PerfilAdm = apps.get_model('reservas', 'PerfilAdm')
        # Verifica se o campo escola existe no modelo antes de filtrar
        if any(f.name == 'escola' for f in PerfilAdm._meta.fields):
            PerfilAdm.objects.filter(escola__isnull=True).update(escola=escola_padrao)
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0008_cargo_texto_livre'),
    ]

    operations = [
        migrations.RunPython(popular_escola_padrao, reverse_code=migrations.RunPython.noop),
    ]