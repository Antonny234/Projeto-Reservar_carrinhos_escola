from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('reservas', '0012_hardening'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramBotEscola',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bot_username', models.CharField(blank=True, max_length=64)),
                ('bot_nome', models.CharField(blank=True, max_length=128)),
                ('bot_token_cifrado', models.TextField(blank=True)),
                ('webhook_slug', models.CharField(db_index=True, max_length=96, unique=True)),
                ('ativo', models.BooleanField(default=True)),
                ('webhook_configurado', models.BooleanField(default=False)),
                ('ultima_verificacao', models.DateTimeField(blank=True, null=True)),
                ('ultimo_erro', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('escola', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='telegram_bot', to='reservas.escola')),
            ],
            options={
                'verbose_name': 'Bot Telegram da Escola',
                'verbose_name_plural': 'Bots Telegram das Escolas',
            },
        ),
        migrations.CreateModel(
            name='TelegramDestino',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.CharField(max_length=64)),
                ('nome', models.CharField(blank=True, max_length=200)),
                ('ativo', models.BooleanField(default=True)),
                ('ultimo_envio', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='destinos', to='reservas.telegrambotescola')),
            ],
            options={
                'verbose_name': 'Destino Telegram',
                'verbose_name_plural': 'Destinos Telegram',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='TelegramPareamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_hash', models.CharField(db_index=True, max_length=64)),
                ('expira_em', models.DateTimeField()),
                ('usado_em', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pareamentos', to='reservas.telegrambotescola')),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pareamentos_telegram_criados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pareamento Telegram',
                'verbose_name_plural': 'Pareamentos Telegram',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='telegramdestino',
            constraint=models.UniqueConstraint(fields=('bot', 'chat_id'), name='unique_telegram_destino_bot_chat'),
        ),
    ]
