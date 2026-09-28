from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0017_pin_envio_professores'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BloqueioLogin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tentativas_consecutivas', models.PositiveSmallIntegerField(default=0)),
                ('bloqueada', models.BooleanField(default=False)),
                ('email_bloqueio_enviado_em', models.DateTimeField(blank=True, null=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bloqueio_login', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
