# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):
    """Agrega el campo 'semana' a Actividad para organizar contenido por semanas (estilo Moodle)."""

    dependencies = [
        ('activities', '0002_alter_actividad_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='actividad',
            name='semana',
            field=models.PositiveIntegerField(default=1, verbose_name='Semana del curso'),
        ),
    ]
