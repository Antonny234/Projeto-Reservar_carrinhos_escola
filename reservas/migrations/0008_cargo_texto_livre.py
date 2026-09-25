from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('reservas', '0007_cargo_perfis_professor')]

    operations = [
        migrations.AlterField(
            model_name='perfilprofessor',
            name='cargo',
            field=models.CharField(default='Professor', max_length=100, verbose_name='Função'),
        ),
        migrations.AlterField(
            model_name='perfilprofessorescola',
            name='cargo',
            field=models.CharField(default='Professor', max_length=100, verbose_name='Função'),
        ),
    ]
