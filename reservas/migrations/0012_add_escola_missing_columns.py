from django.db import migrations


def preencher_escola_padrao(apps, schema_editor):
    # Única escola existente hoje no banco (id=13, "Manoel Martins").
    # Como só existe uma escola, todo registro sem escola_id pertence a ela.
    schema_editor.execute("UPDATE reservas_equipamento SET escola_id = 13 WHERE escola_id IS NULL")
    schema_editor.execute("UPDATE reservas_sala SET escola_id = 13 WHERE escola_id IS NULL")
    schema_editor.execute("UPDATE reservas_reserva SET escola_id = 13 WHERE escola_id IS NULL")
    schema_editor.execute("UPDATE reservas_horarioaula SET escola_id = 13 WHERE escola_id IS NULL")
    schema_editor.execute("UPDATE reservas_grupoequipamento SET escola_id = 13 WHERE escola_id IS NULL")


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0011_fix_perfiladm_escola'),
    ]

    operations = [
        # 1) Adiciona a coluna aceitando nulo, pra não quebrar com dados existentes.
        migrations.RunSQL(
            sql=[
                "ALTER TABLE reservas_equipamento ADD COLUMN escola_id bigint NULL;",
                "ALTER TABLE reservas_sala ADD COLUMN escola_id bigint NULL;",
                "ALTER TABLE reservas_reserva ADD COLUMN escola_id bigint NULL;",
                "ALTER TABLE reservas_horarioaula ADD COLUMN escola_id bigint NULL;",
                "ALTER TABLE reservas_grupoequipamento ADD COLUMN escola_id bigint NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE reservas_equipamento DROP COLUMN escola_id;",
                "ALTER TABLE reservas_sala DROP COLUMN escola_id;",
                "ALTER TABLE reservas_reserva DROP COLUMN escola_id;",
                "ALTER TABLE reservas_horarioaula DROP COLUMN escola_id;",
                "ALTER TABLE reservas_grupoequipamento DROP COLUMN escola_id;",
            ],
        ),

        # 2) Preenche todo mundo com a escola única existente.
        migrations.RunPython(preencher_escola_padrao, reverse_code=migrations.RunPython.noop),

        # 3) Torna obrigatório, adiciona FK, índices e as unique constraints
        #    que o models.py já espera (unique_together por escola).
        migrations.RunSQL(
            sql=[
                "ALTER TABLE reservas_equipamento ALTER COLUMN escola_id SET NOT NULL;",
                "ALTER TABLE reservas_sala ALTER COLUMN escola_id SET NOT NULL;",
                "ALTER TABLE reservas_reserva ALTER COLUMN escola_id SET NOT NULL;",
                "ALTER TABLE reservas_horarioaula ALTER COLUMN escola_id SET NOT NULL;",
                "ALTER TABLE reservas_grupoequipamento ALTER COLUMN escola_id SET NOT NULL;",

                "ALTER TABLE reservas_equipamento ADD CONSTRAINT reservas_equipamento_escola_id_fk FOREIGN KEY (escola_id) REFERENCES reservas_escola(id) ON DELETE CASCADE;",
                "ALTER TABLE reservas_sala ADD CONSTRAINT reservas_sala_escola_id_fk FOREIGN KEY (escola_id) REFERENCES reservas_escola(id) ON DELETE CASCADE;",
                "ALTER TABLE reservas_reserva ADD CONSTRAINT reservas_reserva_escola_id_fk FOREIGN KEY (escola_id) REFERENCES reservas_escola(id) ON DELETE CASCADE;",
                "ALTER TABLE reservas_horarioaula ADD CONSTRAINT reservas_horarioaula_escola_id_fk FOREIGN KEY (escola_id) REFERENCES reservas_escola(id) ON DELETE CASCADE;",
                "ALTER TABLE reservas_grupoequipamento ADD CONSTRAINT reservas_grupoequipamento_escola_id_fk FOREIGN KEY (escola_id) REFERENCES reservas_escola(id) ON DELETE CASCADE;",

                "CREATE INDEX reservas_equipamento_escola_id_idx ON reservas_equipamento (escola_id);",
                "CREATE INDEX reservas_sala_escola_id_idx ON reservas_sala (escola_id);",
                "CREATE INDEX reservas_horarioaula_escola_id_idx ON reservas_horarioaula (escola_id);",
                "CREATE INDEX reservas_grupoequipamento_escola_id_idx ON reservas_grupoequipamento (escola_id);",

                "ALTER TABLE reservas_equipamento ADD CONSTRAINT unique_equipamento_escola_nome UNIQUE (escola_id, nome);",
                "ALTER TABLE reservas_sala ADD CONSTRAINT unique_sala_escola_nome UNIQUE (escola_id, nome);",
                "ALTER TABLE reservas_horarioaula ADD CONSTRAINT unique_horarioaula_escola_periodo_numero UNIQUE (escola_id, periodo, numero);",

                "ALTER TABLE reservas_grupoequipamento DROP CONSTRAINT reservas_grupoequipamento_nome_key;",
                "ALTER TABLE reservas_grupoequipamento ADD CONSTRAINT unique_grupoequipamento_escola_nome UNIQUE (escola_id, nome);",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]