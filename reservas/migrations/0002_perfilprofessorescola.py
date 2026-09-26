from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reservas', '0001_initial'),
    ]

    # 0001_initial already contains Escola and PerfilProfessor.escola.
    # This migration is intentionally a no-op to preserve the migration
    # history without attempting to create an existing table a second time.
    operations = []