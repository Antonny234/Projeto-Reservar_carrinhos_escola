from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Escola',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200, unique=True)),
                ('cidade', models.CharField(blank=True, default='', max_length=100)),
            ],
            options={
                'verbose_name': 'Escola',
                'verbose_name_plural': 'Escolas',
            },
        ),
        migrations.AddField(
            model_name='perfilprofessor',
            name='escola',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='professores',
                to='reservas.escola',
            ),
        ),
    ]