# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from .models import Logro, LOGROS_CATALOGO, RegistroEmocional, verificar_logros
from apps.accounts.models import User
from datetime import date, timedelta
import json


@login_required
def logros_view(request):
    """Pagina de logros/achievements del estudiante."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    # Verificar logros al entrar
    verificar_logros(request.user)

    logros_obtenidos = {l.clave: l for l in Logro.objects.filter(estudiante=request.user)}

    # Construir catalogo con estado
    catalogo = []
    xp_total = 0
    for clave, info in LOGROS_CATALOGO.items():
        obtenido = logros_obtenidos.get(clave)
        catalogo.append({
            'clave': clave,
            'obtenido': obtenido,
            'fecha': obtenido.desbloqueado if obtenido else None,
            **info,
        })
        if obtenido:
            xp_total += info.get('xp', 0)

    # XP total posible
    xp_maximo = sum(v.get('xp', 0) for v in LOGROS_CATALOGO.values())
    nivel = 1 + xp_total // 100
    progreso_nivel = (xp_total % 100)

    context = {
        'catalogo': catalogo,
        'logros_count': len(logros_obtenidos),
        'total_logros': len(LOGROS_CATALOGO),
        'xp_total': xp_total,
        'xp_maximo': xp_maximo,
        'nivel': nivel,
        'progreso_nivel': progreso_nivel,
    }
    return render(request, 'emotions/logros.html', context)


@login_required
def mapa_calor_view(request):
    """Mapa de calor emocional por mes del estudiante (navegable como el calendario del profesor)."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    hoy = date.today()

    # Parámetros de navegación por mes/año
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes  = int(request.GET.get('mes',  hoy.month))
        if mes < 1:  mes = 12; anio -= 1
        if mes > 12: mes = 1;  anio += 1
    except ValueError:
        anio, mes = hoy.year, hoy.month

    import calendar
    primer_dia = date(anio, mes, 1)
    _, dias_mes = calendar.monthrange(anio, mes)
    ultimo_dia  = date(anio, mes, dias_mes)

    # Mes anterior / siguiente
    if mes == 1:
        mes_ant, anio_ant = 12, anio - 1
    else:
        mes_ant, anio_ant = mes - 1, anio
    if mes == 12:
        mes_sig, anio_sig = 1, anio + 1
    else:
        mes_sig, anio_sig = mes + 1, anio

    # Registros del mes
    registros_qs = RegistroEmocional.objects.filter(
        estudiante=request.user,
        fecha__gte=primer_dia,
        fecha__lte=ultimo_dia,
    ).order_by('fecha')

    datos = {}
    for r in registros_qs:
        datos[r.fecha.isoformat()] = {
            'puntaje': r.puntaje,
            'emocion': r.emocion,
        }

    # Estadísticas totales (todos los registros del usuario)
    todos = RegistroEmocional.objects.filter(estudiante=request.user)
    total_registros = todos.count()
    prom_total = None
    if total_registros:
        prom_total = round(sum(r.puntaje for r in todos) / total_registros, 1)

    # Racha actual — 1 query en vez de N
    _hoy = date.today()
    _fechas = set(
        RegistroEmocional.objects
        .filter(estudiante=request.user, fecha__gte=_hoy - timedelta(days=60))
        .values_list('fecha', flat=True)
    )
    racha_actual = 0
    chk = _hoy
    while chk in _fechas:
        racha_actual += 1
        chk -= timedelta(days=1)

    # Nombre del mes en español
    MESES_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    context = {
        'datos_json': json.dumps(datos),
        'hoy': hoy.isoformat(),
        'anio': anio,
        'mes': mes,
        'mes_nombre': MESES_ES[mes - 1],
        'primer_dia': primer_dia,
        'dias_mes': dias_mes,
        'primer_dow': primer_dia.weekday(),  # 0=Lun
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
        'es_mes_actual': (anio == hoy.year and mes == hoy.month),
        'total_registros': total_registros,
        'prom_total': prom_total,
        'racha_actual': racha_actual,
        'registros_mes': registros_qs.count(),
    }
    return render(request, 'emotions/mapa_calor.html', context)


@login_required
def capsulas_view(request):
    """Centro de capsulas de bienestar interactivas."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    capsulas = [
        {
            'id': 'respiracion_478',
            'nombre': 'Respiracion 4-7-8',
            'desc': 'Tecnica de relajacion profunda que calma el sistema nervioso en minutos.',
            'duracion': '3 min',
            'emoji': 'bi-wind',
            'color': '#7c6eff',
            'tipo': 'respiracion',
        },
        {
            'id': 'grounding_54321',
            'nombre': 'Grounding 5-4-3-2-1',
            'desc': 'Tecnica de enraizamiento para salir de la ansiedad y volver al presente.',
            'duracion': '5 min',
            'emoji': 'bi-tree-fill',
            'color': '#00b87a',
            'tipo': 'grounding',
        },
        {
            'id': 'escaneo_corporal',
            'nombre': 'Escaneo Corporal',
            'desc': 'Recorre tu cuerpo con atencion para identificar tension y soltarla.',
            'duracion': '4 min',
            'emoji': 'bi-person-arms-up',
            'color': '#ff6b9d',
            'tipo': 'escaneo',
        },
        {
            'id': 'gratitud_3',
            'nombre': 'Tres Cosas Buenas',
            'desc': 'Ejercicio de gratitud que reentrena el cerebro hacia lo positivo.',
            'duracion': '2 min',
            'emoji': 'bi-hand-thumbs-up-fill',
            'color': '#ffb340',
            'tipo': 'gratitud',
        },
        {
            'id': 'caja_respiracion',
            'nombre': 'Respiracion de Caja',
            'desc': 'Metodo usado por fuerzas especiales para controlar el estres agudo.',
            'duracion': '2 min',
            'emoji': 'bi-square',
            'color': '#17a2b8',
            'tipo': 'respiracion',
        },
        {
            'id': 'visualizacion',
            'nombre': 'Lugar Seguro',
            'desc': 'Visualizacion guiada para crear un refugio mental de calma y seguridad.',
            'duracion': '5 min',
            'emoji': 'bi-triangle-fill',
            'color': '#8884a8',
            'tipo': 'visualizacion',
        },
    ]

    return render(request, 'emotions/capsulas.html', {'capsulas': capsulas})
