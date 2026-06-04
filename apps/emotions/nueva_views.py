# -*- coding: utf-8 -*-
"""
Vistas para: encuestas, retos grupales, notificaciones,
panel institucional, exportar datos, deteccion de crisis.
"""
import json, csv
from datetime import date, timedelta
from collections import Counter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Avg, Count, Q

from .models import (
    RegistroEmocional, Encuesta, RespuestaEncuesta,
    RetoGrupal, Notificacion, crear_notificacion,
    EntradaDiario, MensajeChat, EMOCION_CHOICES, EMOCION_EMOJIS,
)
from apps.accounts.models import User
from apps.courses.models import Curso, Inscripcion


# ─── PALABRAS CLAVE DE CRISIS ─────────────────────────────────────────────────
PALABRAS_CRISIS = [
    'suicidio','suicidarme','quitarme la vida','no quiero vivir',
    'hacerme dano','autolesion','cortarme','no puedo mas',
    'desaparecer','morir','quiero morir','acabar con todo',
]

def detectar_crisis(texto):
    t = texto.lower()
    return any(p in t for p in PALABRAS_CRISIS)


# ─── ENCUESTAS ────────────────────────────────────────────────────────────────

@login_required
def encuestas_lista(request):
    user = request.user
    if user.es_estudiante:
        # Cursos donde esta inscrito
        ids_cursos = Inscripcion.objects.filter(
            estudiante=user, activa=True
        ).values_list('curso_id', flat=True)
        encuestas = Encuesta.objects.filter(
            Q(curso_id__in=ids_cursos) | Q(curso__isnull=True),
            activa=True,
        ).order_by('-created_at')
        ids_respondidas = set(
            RespuestaEncuesta.objects.filter(estudiante=user).values_list('encuesta_id', flat=True)
        )
        context = {'encuestas': encuestas, 'ids_respondidas': ids_respondidas}
    else:
        if user.es_admin:
            encuestas = Encuesta.objects.all().select_related('creada_por', 'curso')
        else:
            encuestas = Encuesta.objects.filter(creada_por=user).select_related('creada_por', 'curso')
        context = {'encuestas': encuestas}

    return render(request, 'emotions/encuestas_lista.html', context)


@login_required
def encuesta_detalle(request, pk):
    encuesta = get_object_or_404(Encuesta, pk=pk)
    user = request.user

    if user.es_estudiante:
        ya_respondio = RespuestaEncuesta.objects.filter(encuesta=encuesta, estudiante=user).exists()

        if request.method == 'POST' and not ya_respondio:
            v_escala = request.POST.get('valor_escala')
            v_opcion = request.POST.get('valor_opcion', '')
            v_texto  = request.POST.get('valor_texto', '')

            RespuestaEncuesta.objects.create(
                encuesta=encuesta, estudiante=user,
                valor_escala=int(v_escala) if v_escala else None,
                valor_opcion=v_opcion,
                valor_texto=v_texto,
            )
            crear_notificacion(user, 'sistema', 'Encuesta completada', encuesta.titulo, f'/emotions/encuestas/{pk}/')
            messages.success(request, 'Respuesta enviada. Gracias por participar.')
            return redirect('emotions:encuestas_lista')

        context = {'encuesta': encuesta, 'ya_respondio': ya_respondio}
    else:
        # Vista de resultados para profesor/admin
        respuestas = encuesta.respuestas_encuesta.all().select_related('estudiante')
        total = respuestas.count()

        stats = {}
        if encuesta.tipo == 'escala':
            vals = list(respuestas.filter(valor_escala__isnull=False).values_list('valor_escala', flat=True))
            stats['promedio'] = round(sum(vals)/len(vals), 2) if vals else None
            stats['distribucion'] = {str(i): vals.count(i) for i in range(1, 6)}
        elif encuesta.tipo == 'opciones' and encuesta.opciones:
            conteo = Counter(respuestas.values_list('valor_opcion', flat=True))
            stats['distribucion'] = dict(conteo)

        context = {'encuesta': encuesta, 'respuestas': respuestas, 'total': total, 'stats': stats, 'stats_json': json.dumps(stats)}

    return render(request, 'emotions/encuesta_detalle.html', context)


@login_required
def encuesta_crear(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.user.es_admin:
        cursos = Curso.objects.filter(activo=True)
    else:
        cursos = Curso.objects.filter(profesor=request.user, activo=True)

    if request.method == 'POST':
        titulo      = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        tipo        = request.POST.get('tipo', 'escala')
        curso_id    = request.POST.get('curso_id') or None
        anonima     = request.POST.get('anonima', 'on') == 'on'
        fecha_lim   = request.POST.get('fecha_limite') or None
        opciones_raw= request.POST.get('opciones', '').strip()
        opciones    = [o.strip() for o in opciones_raw.split('\n') if o.strip()] if opciones_raw else None

        if titulo:
            enc = Encuesta.objects.create(
                titulo=titulo, descripcion=descripcion, tipo=tipo,
                curso_id=curso_id, creada_por=request.user,
                anonima=anonima, fecha_limite=fecha_lim, opciones=opciones,
            )
            # Notificar a estudiantes del curso
            if curso_id:
                ids_est = Inscripcion.objects.filter(curso_id=curso_id, activa=True).values_list('estudiante_id', flat=True)
                for est_id in ids_est:
                    crear_notificacion(
                        User.objects.get(pk=est_id), 'encuesta',
                        f'Nueva encuesta: {titulo}', descripcion,
                        f'/emotions/encuestas/{enc.pk}/'
                    )
            messages.success(request, 'Encuesta creada y notificaciones enviadas.')
            return redirect('emotions:encuestas_lista')

    context = {'cursos': cursos}
    return render(request, 'emotions/encuesta_crear.html', context)


# ─── RETOS GRUPALES ──────────────────────────────────────────────────────────

@login_required
def retos_lista(request):
    user = request.user
    if user.es_estudiante:
        ids_cursos = Inscripcion.objects.filter(estudiante=user, activa=True).values_list('curso_id', flat=True)
        from django.db.models import Q
        retos = RetoGrupal.objects.filter(Q(curso_id__in=ids_cursos) | Q(curso__isnull=True), activo=True)
    else:
        if user.es_admin:
            retos = RetoGrupal.objects.filter(activo=True)
        else:
            from django.db.models import Q
            retos = RetoGrupal.objects.filter(Q(curso__profesor=user) | Q(curso__isnull=True), activo=True)

    retos_data = []
    hoy = date.today()
    for r in retos:
        part, total, pct = r.progreso()
        dias_restantes = (r.fecha_fin - hoy).days if r.fecha_fin >= hoy else 0
        retos_data.append({'reto': r, 'participantes': part, 'total': total, 'pct': pct, 'dias_restantes': dias_restantes})

    context = {'retos_data': retos_data}
    return render(request, 'emotions/retos_lista.html', context)


@login_required
def reto_crear(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.user.es_admin:
        cursos = Curso.objects.filter(activo=True)
    else:
        cursos = Curso.objects.filter(profesor=request.user, activo=True)

    if request.method == 'POST':
        titulo      = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        curso_id    = request.POST.get('curso_id')
        f_inicio    = request.POST.get('fecha_inicio')
        f_fin       = request.POST.get('fecha_fin')

        if titulo:
            reto = RetoGrupal.objects.create(
                titulo=titulo, descripcion=descripcion,
                curso_id=curso_id if curso_id else None, creado_por=request.user,
                fecha_inicio=f_inicio, fecha_fin=f_fin,
            )
            # Notificar
            if curso_id:
                ids_est = Inscripcion.objects.filter(curso_id=curso_id, activa=True).values_list('estudiante_id', flat=True)
            else:
                ids_est = Inscripcion.objects.filter(activa=True).values_list('estudiante_id', flat=True)
            for est_id in ids_est:
                crear_notificacion(
                    User.objects.get(pk=est_id), 'reto',
                    f'Nuevo reto: {titulo}', descripcion,
                    '/emotions/retos/'
                )
            messages.success(request, 'Reto creado exitosamente.')
            return redirect('emotions:retos_lista')

    context = {'cursos': cursos, 'hoy': date.today().isoformat()}
    return render(request, 'emotions/reto_crear.html', context)


# ─── NOTIFICACIONES ──────────────────────────────────────────────────────────

@login_required
def notificaciones_view(request):
    notifs = Notificacion.objects.filter(usuario=request.user)
    notifs.filter(leida=False).update(leida=True)
    context = {'notificaciones': notifs}
    return render(request, 'emotions/notificaciones.html', context)


@login_required
def notificaciones_count(request):
    count = Notificacion.objects.filter(usuario=request.user, leida=False).count()
    return JsonResponse({'count': count})


# ─── PANEL INSTITUCIONAL (solo admin) ────────────────────────────────────────

@login_required
def panel_institucional(request):
    if not request.user.es_admin:
        return HttpResponseForbidden()

    hoy = date.today()
    hace30 = hoy - timedelta(days=29)
    hace7  = hoy - timedelta(days=6)

    # Datos generales
    total_est  = User.objects.filter(rol='estudiante', activo=True).count()
    total_prof = User.objects.filter(rol=User.ROL_PROFESOR, activo=True).count()
    total_regs = RegistroEmocional.objects.filter(fecha__gte=hace30).count()
    prom_gral  = RegistroEmocional.objects.filter(fecha__gte=hace30).aggregate(p=Avg('puntaje'))['p']
    prom_gral  = round(prom_gral, 2) if prom_gral else None

    # Participacion por dia (ultimos 30 dias)
    regs_por_dia = []
    fechas_dia   = []
    for i in range(29, -1, -1):
        d = hoy - timedelta(days=i)
        n = RegistroEmocional.objects.filter(fecha=d).count()
        regs_por_dia.append(n)
        fechas_dia.append(d.strftime('%d/%m'))

    # Promedio por dia de la semana
    DIAS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
    prom_dia_semana = []
    # Django week_day: 1=Sunday, 2=Monday, ..., 7=Saturday
    # dow here: 0=Monday, 1=Tuesday, ..., 6=Sunday
    dow_to_django = [2, 3, 4, 5, 6, 7, 1]  # Mon→2, Tue→3, ..., Sun→1
    for dow in range(7):
        regs = RegistroEmocional.objects.filter(
            fecha__week_day=dow_to_django[dow],
            fecha__gte=hace30
        )
        avg = regs.aggregate(p=Avg('puntaje'))['p']
        prom_dia_semana.append(round(avg, 2) if avg else 0)

    # Distribucion emocional global
    conteo_emo = {}
    for e, _ in EMOCION_CHOICES:
        conteo_emo[e] = RegistroEmocional.objects.filter(emocion=e, fecha__gte=hace30).count()

    # Comparativa por curso
    cursos_data = []
    for c in Curso.objects.filter(activo=True).order_by('grado', 'seccion'):
        regs_c = RegistroEmocional.objects.filter(
            estudiante__inscripciones__curso=c,
            fecha__gte=hace7
        )
        prom_c = regs_c.aggregate(p=Avg('puntaje'))['p']
        cursos_data.append({
            'nombre': c.nombre,
            'grado': c.grado,
            'prom': round(prom_c, 2) if prom_c else None,
        })

    # Estudiantes sin registrar en los ultimos 7 dias
    ids_con_regs = RegistroEmocional.objects.filter(
        fecha__gte=hace7
    ).values_list('estudiante_id', flat=True).distinct()
    sin_registrar = User.objects.filter(
        rol='estudiante', activo=True
    ).exclude(pk__in=ids_con_regs).count()

    context = {
        'total_est': total_est,
        'total_prof': total_prof,
        'total_regs': total_regs,
        'prom_gral': prom_gral,
        'sin_registrar': sin_registrar,
        'fechas_json': json.dumps(fechas_dia),
        'regs_json': json.dumps(regs_por_dia),
        'dias_semana_json': json.dumps(DIAS),
        'prom_semana_json': json.dumps(prom_dia_semana),
        'conteo_emo_json': json.dumps(conteo_emo),
        'cursos_data_json': json.dumps(cursos_data),
    }
    return render(request, 'emotions/panel_institucional.html', context)


# ─── EXPORTAR DATOS PERSONALES ───────────────────────────────────────────────

@login_required
def exportar_mis_datos(request):

    try:
        from .excel_export import generar_excel_estudiante
        buffer = generar_excel_estudiante(request.user)
        nombre = f"conectate_{request.user.username}_{date.today().strftime('%Y%m%d')}.xlsx"
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response
    except ImportError:
        # Fallback a CSV si openpyxl no está instalado
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="conectate_{request.user.username}_{date.today()}.csv"'
        response.write('\ufeff')
        import csv as csv_mod
        writer = csv_mod.writer(response)
        writer.writerow(['Fecha', 'Emocion', 'Puntaje', 'Comentario'])
        for r in RegistroEmocional.objects.filter(estudiante=request.user).order_by('-fecha'):
            writer.writerow([r.fecha, r.get_emocion_display(), r.puntaje, r.comentario])
        return response


# ─── PAGINA DE CRISIS ────────────────────────────────────────────────────────

@login_required
def pagina_crisis(request):
    return render(request, 'emotions/crisis.html')


@login_required
@require_POST
def verificar_crisis(request):
    """Verifica si un texto contiene palabras de crisis. Llamado por AJAX."""
    try:
        data = json.loads(request.body)
        texto = data.get('texto', '')
        crisis = detectar_crisis(texto)
        return JsonResponse({'crisis': crisis})
    except Exception:
        return JsonResponse({'crisis': False})
