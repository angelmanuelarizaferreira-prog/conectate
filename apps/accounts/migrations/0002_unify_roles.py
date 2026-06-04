from django.db import migrations


class Migration(migrations.Migration):
    """
    Migra usuarios con rol 'admin' a rol 'profesor'.
    A partir de esta version, el profesor tiene todos los permisos.
    """
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="UPDATE accounts_user SET rol = 'profesor' WHERE rol = 'admin';",
            reverse_sql="UPDATE accounts_user SET rol = 'admin' WHERE rol = 'profesor' AND is_superuser = 1;",
        ),
        migrations.AlterField(
            model_name='user',
            name='rol',
            field=__import__('django.db.models', fromlist=['CharField']).CharField(
                choices=[('profesor', 'Profesor'), ('estudiante', 'Estudiante')],
                default='estudiante',
                max_length=20,
            ),
        ),
    ]
