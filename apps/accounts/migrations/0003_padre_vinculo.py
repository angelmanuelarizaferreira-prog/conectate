from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_unify_roles'),
    ]
    operations = [
        # Add 'padre' to rol choices
        migrations.AlterField(
            model_name='user',
            name='rol',
            field=models.CharField(
                choices=[
                    ('profesor',   'Profesor'),
                    ('estudiante', 'Estudiante'),
                    ('padre',      'Padre / Acudiente'),
                ],
                default='estudiante',
                max_length=20,
            ),
        ),
        # Create VinculoPadreHijo table
        migrations.CreateModel(
            name='VinculoPadreHijo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('relacion', models.CharField(
                    choices=[
                        ('padre',     'Padre'),
                        ('madre',     'Madre'),
                        ('acudiente', 'Acudiente'),
                        ('tutor',     'Tutor legal'),
                    ],
                    default='padre', max_length=30, verbose_name='Relación',
                )),
                ('activo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('padre', models.ForeignKey(
                    limit_choices_to={'rol': 'padre'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='hijos_vinculados',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('estudiante', models.ForeignKey(
                    limit_choices_to={'rol': 'estudiante'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='padres_vinculados',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Vínculo Padre-Hijo',
                'verbose_name_plural': 'Vínculos Padre-Hijo',
                'ordering': ['estudiante__first_name'],
                'unique_together': {('padre', 'estudiante')},
            },
        ),
    ]
