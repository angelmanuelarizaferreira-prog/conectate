# -*- coding: utf-8 -*-
# Migración 0016: Amplía las opciones de tipo en Notificacion para incluir
# 'alerta_padre', que se usa cuando el sistema notifica a un padre/acudiente
# que su hijo tiene un estado emocional preocupante.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emotions', '0015_retogrupal_curso_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificacion',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('logro',        'Logro desbloqueado'),
                    ('mensaje',      'Nuevo mensaje'),
                    ('encuesta',     'Encuesta pendiente'),
                    ('reto',         'Nuevo reto'),
                    ('alerta',       'Alerta emocional'),
                    ('alerta_padre', 'Alerta emocional (padre)'),
                    ('sistema',      'Sistema'),
                    ('citacion',     'Citación'),
                ],
                max_length=15,
            ),
        ),
    ]
