from django.db import migrations, models
import django.db.models.deletion


def preencher_equipamento(apps, schema_editor):
    RegistroUso = apps.get_model("reservas", "RegistroUso")
    for registro in RegistroUso.objects.filter(equipamento__isnull=True).select_related("reserva"):
        registro.equipamento_id = registro.reserva.equipamento_id
        registro.save(update_fields=["equipamento"])


class Migration(migrations.Migration):
    dependencies = [("reservas", "0018_bloqueio_login")]

    operations = [
        migrations.AddField(
            model_name="registrouso",
            name="equipamento",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="registros_uso", to="reservas.equipamento"),
        ),
        migrations.RunPython(preencher_equipamento, migrations.RunPython.noop),
    ]
