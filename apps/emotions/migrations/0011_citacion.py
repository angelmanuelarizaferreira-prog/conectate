from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('emotions', '0010_notaprofesor_fecha_tipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Citacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha de la cita')),
                ('hora', models.TimeField(verbose_name='Hora de la cita')),
                ('lugar', models.CharField(
                    choices=[
                        ('psicologia', 'Oficina de Psicología'),
                        ('coordinacion', 'Coordinación'),
                        ('bienestar', 'Bienestar Estudiantil'),
                        ('salon', 'Salón del profesor'),
                        ('otro', 'Otro lugar'),
                    ],
                    default='psicologia', max_length=20,
                )),
                ('lugar_otro', models.CharField(blank=True, max_length=100, verbose_name='Especifica el lugar')),
                ('motivo', models.TextField(max_length=600, verbose_name='Motivo de la citación')),
                ('es_urgente', models.BooleanField(default=False, verbose_name='Urgente')),
                ('estado', models.CharField(
                    choices=[
                        ('pendiente', 'Pendiente'),
                        ('confirmada', 'Confirmada'),
                        ('cancelada', 'Cancelada'),
                        ('completada', 'Completada'),
                    ],
                    default='pendiente', max_length=12,
                )),
                ('notas_prof', models.TextField(blank=True, verbose_name='Notas internas del profesor')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('estudiante', models.ForeignKey(
                    limit_choices_to={'rol': 'estudiante'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='citaciones_recibidas',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('profesor', models.ForeignKey(
                    limit_choices_to={'rol__in': ['profesor', 'admin']},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='citaciones_enviadas',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Citación',
                'verbose_name_plural': 'Citaciones',
                'ordering': ['fecha', 'hora'],
            },
        ),
    ]
