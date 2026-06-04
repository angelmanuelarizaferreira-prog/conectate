# -*- coding: utf-8 -*-
from apps.emotions.models import Alerta
from apps.courses.models import Inscripcion
from datetime import date


def alertas_context(request):
    if not request.user.is_authenticated:
        return {'alertas_count': 0, 'hoy': date.today()}

    alertas_count = 0
    user = request.user

    if user.is_superuser:
        # Solo superusuarios ven TODAS las alertas
        alertas_count = Alerta.objects.filter(resuelta=False).count()
    elif user.es_profesor:
        # Profesores ven alertas de estudiantes en sus cursos
        ids = Inscripcion.objects.filter(
            curso__profesor=user, activa=True
        ).values_list('estudiante_id', flat=True)
        alertas_count = Alerta.objects.filter(estudiante_id__in=ids, resuelta=False).count()

    return {
        'alertas_count': alertas_count,
        'hoy': date.today(),
    }
