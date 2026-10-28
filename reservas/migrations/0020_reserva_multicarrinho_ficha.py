from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reservas", "0019_registrouso_equipamento")]

    operations = [
        migrations.AddField(
            model_name="reserva",
            name="permite_multiplos_carrinhos",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="reserva",
            name="ficha_enviada",
            field=models.BooleanField(default=False),
        ),
    ]
