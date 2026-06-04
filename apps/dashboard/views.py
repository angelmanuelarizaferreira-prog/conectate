# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from datetime import date, timedelta
import json

from apps.accounts.models import User
from apps.emotions.models import RegistroEmocional, Alerta
from apps.courses.models import Curso, Inscripcion
from apps.activities.models import Actividad, RespuestaActividad


@login_required
def inicio(request):
    user = request.user

    if user.es_profesor:
        return dashboard_admin(request)
    elif user.es_padre:
        return redirect('accounts:panel_padre')
    else:
        return dashboard_estudiante(request)


@login_required
def dashboard_estudiante(request):
    user = request.user
    hoy = date.today()

    from apps.emotions.models import MetaSemanal, EntradaDiario
    lunes = hoy - timedelta(days=hoy.weekday())
    meta_semana, _ = MetaSemanal.objects.get_or_create(
        estudiante=user, semana_inicio=lunes, defaults={'texto': ''}
    )

    registro_hoy = RegistroEmocional.objects.filter(estudiante=user, fecha=hoy).first()
    
    # Ultimos 7 registros
    ultimos_registros = RegistroEmocional.objects.filter(
        estudiante=user
    ).order_by('-fecha')[:7]
    
    # Mis cursos
    inscripciones = Inscripcion.objects.filter(estudiante=user, activa=True).select_related('curso')
    
    # Actividades pendientes
    ids_cursos = inscripciones.values_list('curso_id', flat=True)
    ids_respondidas = RespuestaActividad.objects.filter(estudiante=user).values_list('actividad_id', flat=True)
    actividades_pendientes = Actividad.objects.filter(
        curso_id__in=ids_cursos, activa=True
    ).exclude(id__in=ids_respondidas).order_by('-created_at')[:5]
    
    # Racha de registro — 1 query en vez de N queries (una por día)
    racha = 0
    fechas_registradas = set(
        RegistroEmocional.objects
        .filter(estudiante=user, fecha__gte=hoy - timedelta(days=60))
        .values_list('fecha', flat=True)
    )
    dia = hoy
    while dia in fechas_registradas:
        racha += 1
        dia -= timedelta(days=1)
    
    context = {
        'registro_hoy': registro_hoy,
        'ultimos_registros': ultimos_registros,
        'inscripciones': inscripciones,
        'actividades_pendientes': actividades_pendientes,
        'racha': racha,
        'hoy': hoy,
        'meta_semana': meta_semana,
        'total_diario': EntradaDiario.objects.filter(estudiante=user).count(),
    }
    return render(request, 'dashboard/estudiante.html', context)


@login_required
def dashboard_profesor(request):
    user = request.user
    hoy = date.today()
    
    cursos = Curso.objects.filter(profesor=user, activo=True)
    
    ids_estudiantes = Inscripcion.objects.filter(
        curso__in=cursos, activa=True
    ).values_list('estudiante_id', flat=True).distinct()
    
    total_estudiantes = len(ids_estudiantes)
    
    # Registros de hoy
    registros_hoy = RegistroEmocional.objects.filter(
        estudiante_id__in=ids_estudiantes, fecha=hoy
    ).select_related('estudiante')
    
    # Promedio emocional del grupo hoy — usando agregación DB
    from django.db.models import Avg as _Avg
    promedio_hoy = None
    _prom = registros_hoy.aggregate(p=_Avg('puntaje'))['p']
    if _prom is not None:
        promedio_hoy = round(_prom, 1)
    
    # Alertas no resueltas
    alertas = Alerta.objects.filter(
        estudiante_id__in=ids_estudiantes, resuelta=False
    ).select_related('estudiante').order_by('-fecha_creacion')[:5]
    
    # Porcentaje de participacion hoy
    participacion_hoy = round((registros_hoy.count() / total_estudiantes * 100) if total_estudiantes > 0 else 0)
    
    # Datos grafica semanal — 1 query en vez de 7
    from django.db.models import Avg
    semana_inicio = hoy - timedelta(days=6)
    regs_semana = (
        RegistroEmocional.objects
        .filter(estudiante_id__in=ids_estudiantes, fecha__gte=semana_inicio)
        .values('fecha')
        .annotate(prom=Avg('puntaje'))
    )
    prom_por_fecha = {r['fecha']: round(r['prom'], 2) for r in regs_semana}
    fechas_semana = []
    promedios_semana = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        fechas_semana.append(dia.strftime('%a %d/%m'))
        promedios_semana.append(prom_por_fecha.get(dia))
    
    # Distribucion de emociones hoy — 1 query en vez de 5
    from apps.emotions.models import EMOCION_CHOICES
    from django.db.models import Count as _Count2
    emociones_hoy = {e: 0 for e, _ in EMOCION_CHOICES}
    for row in registros_hoy.values('emocion').annotate(n=_Count2('id')):
        emociones_hoy[row['emocion']] = row['n']
    
    # Estudiantes que no han registrado hoy
    ids_registraron = registros_hoy.values_list('estudiante_id', flat=True)
    sin_registrar = User.objects.filter(id__in=ids_estudiantes).exclude(id__in=ids_registraron)[:10]
    
    context = {
        'cursos': cursos,
        'total_estudiantes': total_estudiantes,
        'registros_hoy': registros_hoy,
        'promedio_hoy': promedio_hoy,
        'alertas': alertas,
        'total_alertas': Alerta.objects.filter(estudiante_id__in=ids_estudiantes, resuelta=False).count(),
        'participacion_hoy': participacion_hoy,
        'fechas_semana_json': json.dumps(fechas_semana),
        'promedios_semana_json': json.dumps(promedios_semana),
        'emociones_hoy_json': json.dumps(emociones_hoy),
        'sin_registrar': sin_registrar,
        'hoy': hoy,
    }
    return render(request, 'dashboard/profesor.html', context)


@login_required
def dashboard_admin(request):
    hoy = date.today()
    
    total_usuarios = User.objects.count()
    total_estudiantes = User.objects.filter(rol=User.ROL_ESTUDIANTE).count()
    total_profesores = User.objects.filter(rol=User.ROL_PROFESOR).count()
    total_cursos = Curso.objects.filter(activo=True).count()
    total_alertas = Alerta.objects.filter(resuelta=False).count()
    registros_hoy = RegistroEmocional.objects.filter(fecha=hoy).count()
    
    # Ultimas alertas
    alertas_recientes = Alerta.objects.filter(resuelta=False).select_related('estudiante').order_by('-fecha_creacion')[:8]
    
    # Cursos con mas alertas
    cursos = Curso.objects.filter(activo=True).prefetch_related('inscripciones')
    
    # Registros por dia (ultima semana)
    fechas = []
    registros_por_dia = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        count = RegistroEmocional.objects.filter(fecha=dia).count()
        fechas.append(dia.strftime('%d/%m'))
        registros_por_dia.append(count)
    
    context = {
        'total_usuarios': total_usuarios,
        'total_estudiantes': total_estudiantes,
        'total_profesores': total_profesores,
        'total_cursos': total_cursos,
        'total_alertas': total_alertas,
        'registros_hoy': registros_hoy,
        'alertas_recientes': alertas_recientes,
        'cursos': cursos,
        'fechas_json': json.dumps(fechas),
        'registros_json': json.dumps(registros_por_dia),
        'todos_usuarios': User.objects.order_by('-date_joined')[:10],
    }
    return render(request, 'dashboard/admin.html', context)
