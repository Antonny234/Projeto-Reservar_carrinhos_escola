from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('reservas', '0014_telegram'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferenciaEscola',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('recebida', 'Recebida'), ('recusada', 'Recusada')], default='pendente', max_length=12)),
                ('recebida_por_nome', models.CharField(blank=True, max_length=200)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('recebida_em', models.DateTimeField(blank=True, null=True)),
                ('observacao', models.TextField(blank=True)),
                ('criada_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transferencias_escola_criadas', to=settings.AUTH_USER_MODEL)),
                ('destino', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transferencias_recebidas', to='reservas.escola')),
                ('origem', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transferencias_enviadas', to='reservas.escola')),
                ('recebida_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transferencias_escola_conferidas', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-criada_em']},
        ),
        migrations.CreateModel(
            name='ItemTransferenciaEscola',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificador_tipo', models.CharField(max_length=20)),
                ('identificador_valor', models.CharField(max_length=100)),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes_escola', to='reservas.equipamentoinventario')),
                ('transferencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='reservas.transferenciaescola')),
            ],
        ),
        migrations.AddConstraint(
            model_name='itemtransferenciaescola',
            constraint=models.UniqueConstraint(fields=('transferencia', 'equipamento'), name='unique_item_transferencia_escola'),
        ),
    ]
