from django.db import migrations


class Migration(migrations.Migration):
    """Keep the historical migration dependency without repeating schema.

    The school foreign keys, indexes and unique constraints are already created
    by 0001_initial. The former raw SQL added those columns a second time and
    used PostgreSQL-only ALTER syntax, so it failed on SQLite during setup.
    """

    dependencies = [
        ('reservas', '0011_fix_perfiladm_escola'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
