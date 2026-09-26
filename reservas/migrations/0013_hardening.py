from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q, F, Count


def normalize_legacy_reservations(apps, schema_editor):
    Reserva = apps.get_model("reservas", "Reserva")

    # Preserve all historical rows, but make conflicting active whole-cart
    # reservations non-active so the new database uniqueness rule can be added.
    groups = (
        Reserva.objects.filter(
            status__in=["confirmada", "pendente"],
            numero_notebook_unico__isnull=True,
            quantidade__isnull=True,
        )
        .values("escola_id", "equipamento_id", "data_uso", "horario_inicio", "horario_fim")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for group in groups.iterator():
        ids = list(
            Reserva.objects.filter(
                escola_id=group["escola_id"],
                equipamento_id=group["equipamento_id"],
                data_uso=group["data_uso"],
                horario_inicio=group["horario_inicio"],
                horario_fim=group["horario_fim"],
                status__in=["confirmada", "pendente"],
                numero_notebook_unico__isnull=True,
                quantidade__isnull=True,
            )
            .order_by("data_criacao", "id")
            .values_list("id", flat=True)
        )
        Reserva.objects.filter(id__in=ids[1:]).update(status="recusada")

    # Legacy rows with invalid intervals cannot satisfy the new active-row
    # check. Mark them rejected rather than inventing a new time.
    Reserva.objects.filter(
        status__in=["confirmada", "pendente"],
        horario_fim__lte=F("horario_inicio"),
    ).update(status="recusada")


def hash_existing_pins(apps, schema_editor):
    for model_name in ("PerfilAdm", "PerfilAdmEscola"):
        Model = apps.get_model("reservas", model_name)
        for obj in Model.objects.exclude(pin_envio__isnull=True).exclude(pin_envio="").iterator():
            value = str(obj.pin_envio)
            # Only raw four-digit legacy PINs are migrated. Django password
            # hashes are much longer and are left untouched.
            if len(value) == 4 and value.isdigit():
                obj.pin_envio = make_password(value)
                obj.save(update_fields=["pin_envio"])


class Migration(migrations.Migration):
    dependencies = [("reservas", "0012_add_escola_missing_columns")]

    operations = [
        migrations.AlterField(
            model_name="perfiladm",
            name="pin_envio",
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name="PIN de envio"),
        ),
        migrations.AlterField(
            model_name="perfiladmescola",
            name="pin_envio",
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name="PIN de envio"),
        ),
        migrations.RunPython(normalize_legacy_reservations, migrations.RunPython.noop),
        migrations.RunPython(hash_existing_pins, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(fields=["escola", "data_uso", "horario_inicio", "horario_fim"], name="reserva_school_slot_idx"),
        ),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(fields=["equipamento", "data_uso", "horario_inicio", "horario_fim", "status"], name="reserva_equipment_slot_idx"),
        ),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(fields=["professor", "data_uso"], name="reserva_professor_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="reserva",
            constraint=models.CheckConstraint(
                condition=(Q(status="recusada") | Q(horario_fim__gt=F("horario_inicio"))),
                name="reserva_horario_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="reserva",
            constraint=models.CheckConstraint(
                condition=Q(quantidade__isnull=True) | Q(quantidade__gt=0),
                name="reserva_quantidade_positiva",
            ),
        ),
        migrations.AddConstraint(
            model_name="reserva",
            constraint=models.UniqueConstraint(
                fields=["escola", "equipamento", "data_uso", "horario_inicio", "horario_fim"],
                condition=(Q(status__in=["confirmada", "pendente"]) & Q(numero_notebook_unico__isnull=True) & Q(quantidade__isnull=True)),
                name="unique_carrinho_inteiro_horario_ativo",
            ),
        ),
    ]
