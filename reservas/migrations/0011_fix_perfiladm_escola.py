from django.db import migrations


def preencher_escola_padrao(apps, schema_editor):
    """
    Migration de compatibilidade.

    O campo PerfilAdm.escola já existe desde a migration 0001_initial.
    A versão anterior desta migration tentava adicioná-lo novamente, o que
    causava `duplicate column name: escola_id` em bancos criados a partir da
    migration inicial.
    """
    PerfilAdm = apps.get_model('reservas', 'PerfilAdm')
    Escola = apps.get_model('reservas', 'Escola')

    # Mantido como salvaguarda para bancos legados que eventualmente tenham
    # registros sem escola. Em bancos atuais, o FK já é NOT NULL.
    escola_padrao = Escola.objects.order_by('id').first()
    if escola_padrao:
        PerfilAdm.objects.filter(escola__isnull=True).update(escola=escola_padrao)


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0010_alter_escola_options_alter_escola_cidade_and_more'),
    ]

    operations = [
        # PerfilAdm.escola já foi criado em 0001_initial. Esta migration
        # apenas preserva a etapa histórica e executa a correção de dados,
        # sem tentar recriar/adicionar a coluna.
        migrations.RunPython(preencher_escola_padrao, migrations.RunPython.noop),
    ]
