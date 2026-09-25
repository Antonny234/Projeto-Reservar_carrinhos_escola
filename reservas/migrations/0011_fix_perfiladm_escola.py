from django.db import migrations, models
import django.db.models.deletion


def preencher_escola_padrao(apps, schema_editor):
    PerfilAdm = apps.get_model('reservas', 'PerfilAdm')
    Escola = apps.get_model('reservas', 'Escola')
    escola_padrao = Escola.objects.order_by('id').first()
    if escola_padrao:
        PerfilAdm.objects.filter(escola__isnull=True).update(escola=escola_padrao)


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0010_alter_escola_options_alter_escola_cidade_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfiladm',
            name='escola',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='administradores',
                to='reservas.escola',
                null=True,
            ),
        ),
        migrations.RunPython(preencher_escola_padrao, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='perfiladm',
            name='escola',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='administradores',
                to='reservas.escola',
            ),
        ),
    ]