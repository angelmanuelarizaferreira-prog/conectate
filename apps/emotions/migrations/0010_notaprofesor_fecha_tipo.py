from django.db import migrations, models
import datetime

class Migration(migrations.Migration):
    dependencies = [
        ('emotions', '0009_alter_encuesta_id_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='notaprofesor',
            name='fecha',
            field=models.DateField(default=datetime.date.today, verbose_name='Fecha de la nota'),
        ),
        migrations.AddField(
            model_name='notaprofesor',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('observacion', 'Observacion'),
                    ('alerta', 'Alerta'),
                    ('logro', 'Logro'),
                    ('seguimiento', 'Seguimiento'),
                ],
                default='observacion',
                max_length=20,
            ),
        ),
    ]
