# -*- coding: utf-8 -*-
"""
Migration: agrega índices de base de datos para consultas frecuentes con 1000+ estudiantes.
Cubre los patrones de búsqueda más comunes del profesor y del dashboard.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emotions', '0012_alter_notaprofesor_options_alter_alerta_tipo_and_more'),
    ]

    operations = [
        # RegistroEmocional: las consultas más frecuentes son por (estudiante, fecha)
        # y por (estudiante_id__in=ids, fecha=hoy) — ambas cubiertas por estos índices
        migrations.AddIndex(
            model_name='registroemocional',
            index=models.Index(
                fields=['fecha', 'estudiante'],
                name='reg_fecha_estudiante_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='registroemocional',
            index=models.Index(
                fields=['estudiante', 'fecha'],
                name='reg_estudiante_fecha_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='registroemocional',
            index=models.Index(
                fields=['estudiante', 'puntaje'],
                name='reg_estudiante_puntaje_idx',
            ),
        ),
        # Alerta: búsquedas frecuentes por (estudiante, resuelta) y (resuelta, prioridad)
        migrations.AddIndex(
            model_name='alerta',
            index=models.Index(
                fields=['estudiante', 'resuelta'],
                name='alerta_est_resuelta_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='alerta',
            index=models.Index(
                fields=['resuelta', 'prioridad', 'fecha_creacion'],
                name='alerta_resol_prior_idx',
            ),
        ),
        # MensajeDirecto: búsquedas por destinatario + leido
        migrations.AddIndex(
            model_name='mensajedirecto',
            index=models.Index(
                fields=['destinatario', 'leido'],
                name='msg_dest_leido_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='mensajedirecto',
            index=models.Index(
                fields=['remitente', 'destinatario'],
                name='msg_rem_dest_idx',
            ),
        ),
    ]
