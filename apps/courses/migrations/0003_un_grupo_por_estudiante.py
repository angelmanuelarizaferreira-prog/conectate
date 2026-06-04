"""
Migración: garantiza que cada estudiante tenga como máximo UNA inscripción activa.
Si un estudiante tiene varias activas, se conserva la más reciente y las demás
se marcan como inactivas.
"""
from django.db import migrations


def un_grupo_por_estudiante(apps, schema_editor):
    Inscripcion = apps.get_model('courses', 'Inscripcion')

    # Obtener todos los estudiantes con más de una inscripción activa
    from django.db.models import Count
    estudiantes_duplicados = (
        Inscripcion.objects
        .filter(activa=True)
        .values('estudiante_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .values_list('estudiante_id', flat=True)
    )

    for est_id in estudiantes_duplicados:
        inscripciones = Inscripcion.objects.filter(
            estudiante_id=est_id, activa=True
        ).order_by('-fecha_inscripcion')  # más reciente primero

        # Conservar la primera (más reciente), desactivar el resto
        for insc in inscripciones[1:]:
            insc.activa = False
            insc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_grupos_por_grado'),
    ]

    operations = [
        migrations.RunPython(un_grupo_por_estudiante, migrations.RunPython.noop),
    ]
