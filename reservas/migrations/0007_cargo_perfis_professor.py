from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('reservas', '0006_perfiladmescola')]

    operations = [
        migrations.AddField(model_name='perfilprofessor', name='cargo', field=models.CharField(choices=[('professor', 'Professor'), ('coordenador', 'Coordenador(a)'), ('diretor', 'Diretor(a)'), ('vice_diretor', 'Vice-diretor(a)'), ('proat', 'PROAT'), ('outro', 'Outro')], default='professor', max_length=20, verbose_name='Função')),
  ]
