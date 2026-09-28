from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0016_rename_reserva_school_slot_idx_reservas_re_escola__3cd86f_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilprofessor',
            name='pin_envio',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name='PIN de envio'),
        ),
        migrations.AddField(
            model_name='perfilprofessorescola',
            name='pin_envio',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name='PIN de envio'),
        ),
    ]
