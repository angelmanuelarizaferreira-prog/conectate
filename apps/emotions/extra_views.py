# -*- coding: utf-8 -*-
"""
Vistas para: insights semanales, mensajes directos, foro anonimo,
rutina de cierre del dia, semaforo del grupo, calendario emocional.
"""
import json
from datetime import date, timedelta
from collections import Counter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from .models import (
    NotaProfesor,
    Citacion,
    RegistroEmocional, MensajeDirecto, PostForo, RutinaCierre,
    EMOCION_CHOICES, EMOCION_EMOJIS
)
from apps.accounts.models import User
from apps.courses.models import Curso, Inscripcion


# ─── INSIGHTS SEMANALES ──────────────────────────────────────────────────────

def _generar_insight(registros_semana):
    """Genera un insight textual basado en los registros de la semana."""
    if not registros_semana:
        return None

    puntajes = [r.puntaje for r in registros_semana]
    emociones = [r.emocion for r in registros_semana]
    conteo = Counter(emociones)
    top_emo = conteo.most_common(1)[0][0] if conteo else None
    promedio = sum(puntajes) / len(puntajes)

    DIAS = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
    mejor_dia = None
    peor_dia  = None
    if len(registros_semana) >= 3:
        por_dia = {}
        for r in registros_semana:
            dia = r.fecha.weekday()
            por_dia.setdefault(dia, []).append(r.puntaje)
        promedios_dia = {d: sum(ps)/len(ps) for d,ps in por_dia.items()}
        mejor_dia = DIAS[max(promedios_dia, key=promedios_dia.get)]
        peor_dia  = DIAS[min(promedios_dia, key=promedios_dia.get)]

    EMOCION_EMOJI_CHARS = {
        'feliz': '😊', 'tranquilo': '😐', 'estresado': '😵',
        'triste': '😢', 'enojado': '😠',
    }
    emoji = EMOCION_EMOJI_CHARS.get(top_emo, '')
    emo_label = dict(EMOCION_CHOICES).get(top_emo, '')

    if promedio >= 4:
        apertura = "Tuviste una semana emocionalmente positiva."
    elif promedio >= 3:
        apertura = "Tu semana estuvo equilibrada, con altibajos normales."
    else:
        apertura = "Fue una semana dificil emocionalmente. Eso es valido."

    lineas = [apertura]
    if top_emo:
        lineas.append(f"Tu emocion mas frecuente fue {emoji} {emo_label} ({conteo[top_emo]} de {len(registros_semana)} dias).")
    if mejor_dia and peor_dia and mejor_dia != peor_dia:
        lineas.append(f"Los {mejor_dia}s tendiste a sentirte mejor; los {peor_dia}s fueron mas dificiles.")
    if len(puntajes) == 7:
        lineas.append("Registraste los 7 dias de la semana. Excelente constancia.")
    elif len(puntajes) >= 5:
        lineas.append(f"Registraste {len(puntajes)} de 7 dias. Sigue asi.")

    return ' '.join(lineas)


@login_required
def insights_view(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    hoy = date.today()
    # Semana pasada (lunes a domingo)
    lunes_pasado = hoy - timedelta(days=hoy.weekday() + 7)
    domingo_pasado = lunes_pasado + timedelta(days=6)

    regs_semana_pasada = list(RegistroEmocional.objects.filter(
        estudiante=request.user,
        fecha__range=[lunes_pasado, domingo_pasado]
    ).order_by('fecha'))

    # Semana actual
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    regs_semana_actual = list(RegistroEmocional.objects.filter(
        estudiante=request.user,
        fecha__range=[lunes_actual, hoy]
    ).order_by('fecha'))

    insight_pasada = _generar_insight(regs_semana_pasada)
    insight_actual = _generar_insight(regs_semana_actual)

    # Comparativa: mejoro o empeoro?
    comparativa = None
    if regs_semana_pasada and regs_semana_actual:
        prom_pas = sum(r.puntaje for r in regs_semana_pasada) / len(regs_semana_pasada)
        prom_act = sum(r.puntaje for r in regs_semana_actual) / len(regs_semana_actual)
        diff = prom_act - prom_pas
        if diff > 0.3:
            comparativa = {'texto': f"Esta semana estas mejor que la pasada (+{diff:.1f} puntos)", 'tipo': 'positivo'}
        elif diff < -0.3:
            comparativa = {'texto': f"Esta semana ha sido mas dificil que la pasada ({diff:.1f} puntos)", 'tipo': 'negativo'}
        else:
            comparativa = {'texto': "Tu estado emocional se mantiene estable respecto a la semana pasada.", 'tipo': 'neutro'}

    # Ultimas 4 semanas para grafica
    semanas = []
    for w in range(3, -1, -1):
        lun = hoy - timedelta(days=hoy.weekday() + w*7)
        dom = lun + timedelta(days=6)
        regs = RegistroEmocional.objects.filter(
            estudiante=request.user, fecha__range=[lun, dom]
        )
        prom = None
        if regs.exists():
            ps = list(regs.values_list('puntaje', flat=True))
            prom = round(sum(ps)/len(ps), 1)
        semanas.append({'label': f"S{4-w}", 'promedio': prom, 'inicio': lun.strftime('%d/%m')})

    context = {
        'insight_pasada': insight_pasada,
        'insight_actual': insight_actual,
        'comparativa': comparativa,
        'regs_pasada': regs_semana_pasada,
        'regs_actual': regs_semana_actual,
        'semanas_json': json.dumps([{'label': s['label'], 'prom': s['promedio'], 'inicio': s['inicio']} for s in semanas]),
        'lunes_pasado': lunes_pasado,
        'domingo_pasado': domingo_pasado,
        'lunes_actual': lunes_actual,
        'hoy': hoy,
    }
    return render(request, 'emotions/insights.html', context)


# ─── MENSAJES DIRECTOS ───────────────────────────────────────────────────────

@login_required
def mensajes_view(request):
    user = request.user
    recibidos = MensajeDirecto.objects.filter(destinatario=user).select_related('remitente')
    enviados  = MensajeDirecto.objects.filter(remitente=user).select_related('destinatario')

    # Marcar como leidos
    recibidos.filter(leido=False).update(leido=True)

    context = {'recibidos': recibidos, 'enviados': enviados}
    return render(request, 'emotions/mensajes.html', context)


@login_required
def enviar_mensaje(request, pk):
    """Profesor envia mensaje a estudiante desde su perfil."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    destinatario = get_object_or_404(User, pk=pk, rol=User.ROL_ESTUDIANTE)

    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        if contenido:
            MensajeDirecto.objects.create(
                remitente=request.user,
                destinatario=destinatario,
                contenido=contenido,
            )
            messages.success(request, f'Mensaje enviado a {destinatario.get_full_name()}.')
        return redirect('accounts:perfil_estudiante', pk=pk)

    return redirect('accounts:perfil_estudiante', pk=pk)


@login_required
def mensajes_no_leidos(request):
    count = MensajeDirecto.objects.filter(destinatario=request.user, leido=False).count()
    return JsonResponse({'count': count})


# ─── FORO ANONIMO ────────────────────────────────────────────────────────────

@login_required
def foro_curso(request, curso_id):
    curso = get_object_or_404(Curso, pk=curso_id, activo=True)

    # Verificar acceso
    if request.user.es_estudiante:
        if not Inscripcion.objects.filter(estudiante=request.user, curso=curso, activa=True).exists():
            return HttpResponseForbidden()
    elif not request.user.es_admin and curso.profesor != request.user:
        return HttpResponseForbidden()

    posts = PostForo.objects.filter(curso=curso).select_related('autor')

    if request.method == 'POST' and request.user.es_estudiante:
        contenido = request.POST.get('contenido', '').strip()
        anonimo   = request.POST.get('anonimo', 'on') == 'on'
        if contenido and len(contenido) <= 500:
            PostForo.objects.create(
                curso=curso, autor=request.user,
                contenido=contenido, anonimo=anonimo,
            )
            messages.success(request, 'Tu mensaje fue publicado.')
            return redirect('emotions:foro', curso_id=curso.pk)

    context = {
        'curso': curso,
        'posts': posts,
        'es_profesor': request.user.es_profesor or request.user.es_admin,
    }
    return render(request, 'emotions/foro.html', context)


@login_required
@require_POST
def apoyo_post(request, post_id):
    """Toggle de apoyo (like) a un post del foro."""
    post = get_object_or_404(PostForo, pk=post_id)
    if request.user in post.apoyos.all():
        post.apoyos.remove(request.user)
        apoyado = False
    else:
        post.apoyos.add(request.user)
        apoyado = True
    return JsonResponse({'apoyado': apoyado, 'total': post.total_apoyos()})


# ─── RUTINA DE CIERRE DEL DIA ────────────────────────────────────────────────

@login_required
def rutina_cierre(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    hoy = date.today()
    rutina_hoy, _ = RutinaCierre.objects.get_or_create(
        estudiante=request.user, fecha=hoy,
        defaults={'salio_bien': '', 'fue_dificil': '', 'manana': ''}
    )

    if request.method == 'POST':
        salio_bien  = request.POST.get('salio_bien', '').strip()
        fue_dificil = request.POST.get('fue_dificil', '').strip()
        manana      = request.POST.get('manana', '').strip()
        if salio_bien:
            rutina_hoy.salio_bien  = salio_bien
            rutina_hoy.fue_dificil = fue_dificil
            rutina_hoy.manana      = manana
            rutina_hoy.save()
            messages.success(request, 'Rutina de cierre guardada. Descansa bien.')
            return redirect('dashboard:inicio')

    historico = RutinaCierre.objects.filter(
        estudiante=request.user
    ).order_by('-fecha')[:7]

    context = {
        'rutina_hoy': rutina_hoy,
        'historico': historico,
        'hoy': hoy,
        'ya_completada': bool(rutina_hoy.salio_bien),
    }
    return render(request, 'emotions/rutina_cierre.html', context)


# ─── SEMAFORO DEL GRUPO ──────────────────────────────────────────────────────

@login_required
def semaforo_grupo(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    hoy = date.today()

    if request.user.es_admin:
        cursos = Curso.objects.filter(activo=True).select_related('profesor')
    else:
        cursos = Curso.objects.filter(profesor=request.user, activo=True)

    curso_id = request.GET.get('curso')
    curso_sel = None
    datos = []

    if curso_id:
        curso_sel = get_object_or_404(Curso, pk=curso_id)
        inscritos = Inscripcion.objects.filter(curso=curso_sel, activa=True).select_related('estudiante')

        for insc in inscritos:
            est = insc.estudiante
            regs_7d = list(RegistroEmocional.objects.filter(
                estudiante=est,
                fecha__gte=hoy - timedelta(days=6)
            ).order_by('fecha').values_list('puntaje', flat=True))

            if not regs_7d:
                semaforo = 'gris'
                prom_7d  = None
            else:
                prom_7d = round(sum(regs_7d) / len(regs_7d), 1)
                if prom_7d >= 3.5:
                    semaforo = 'verde'
                elif prom_7d >= 2.5:
                    semaforo = 'amarillo'
                else:
                    semaforo = 'rojo'

            # Tendencia
            tendencia = None
            if len(regs_7d) >= 4:
                mitad = len(regs_7d) // 2
                if sum(regs_7d[mitad:]) / (len(regs_7d) - mitad) > sum(regs_7d[:mitad]) / mitad + 0.2:
                    tendencia = 'mejorando'
                elif sum(regs_7d[mitad:]) / (len(regs_7d) - mitad) < sum(regs_7d[:mitad]) / mitad - 0.2:
                    tendencia = 'bajando'
                else:
                    tendencia = 'estable'

            reg_hoy = RegistroEmocional.objects.filter(estudiante=est, fecha=hoy).first()
            alertas = 0  # alertas handled via Alerta model separately

            datos.append({
                'estudiante': est,
                'semaforo': semaforo,
                'prom_7d': prom_7d,
                'tendencia': tendencia,
                'reg_hoy': reg_hoy,
                'registros_semana': len(regs_7d),
            })

        # Ordenar: rojo primero, luego amarillo, verde, gris
        orden = {'rojo': 0, 'amarillo': 1, 'verde': 2, 'gris': 3}
        datos.sort(key=lambda x: orden.get(x['semaforo'], 4))

    resumen = {'verde': 0, 'amarillo': 0, 'rojo': 0, 'gris': 0}
    for d in datos:
        resumen[d['semaforo']] = resumen.get(d['semaforo'], 0) + 1

    context = {
        'cursos': cursos,
        'curso_sel': curso_sel,
        'datos': datos,
        'resumen': resumen,
        'hoy': hoy,
    }
    return render(request, 'emotions/semaforo.html', context)


# ─── CALENDARIO EMOCIONAL DEL GRUPO ─────────────────────────────────────────

@login_required
def calendario_grupo(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    hoy = date.today()

    cursos = Curso.objects.filter(activo=True)

    curso_id = request.GET.get('curso')
    mes_str  = request.GET.get('mes')  # formato YYYY-MM
    curso_sel = None
    cal_data = {}
    citaciones_data = {}

    # Determinar mes a mostrar
    if mes_str:
        try:
            year, month = int(mes_str[:4]), int(mes_str[5:7])
        except Exception:
            year, month = hoy.year, hoy.month
    else:
        year, month = hoy.year, hoy.month

    def _color(prom):
        if prom >= 3.8: return '#00b87a'
        elif prom >= 3.0: return '#f5b800'
        elif prom >= 2.0: return '#fd7e14'
        return '#e0284f'

    cursos_info = []

    if curso_id:
        curso_sel = get_object_or_404(Curso, pk=curso_id)
        ids_estudiantes = Inscripcion.objects.filter(
            curso=curso_sel, activa=True
        ).values_list('estudiante_id', flat=True)

        inicio = hoy - timedelta(days=89)
        registros = RegistroEmocional.objects.filter(
            estudiante_id__in=ids_estudiantes,
            fecha__range=[inicio, hoy]
        ).values('fecha', 'puntaje')

        por_fecha = {}
        for r in registros:
            por_fecha.setdefault(r['fecha'].isoformat(), []).append(r['puntaje'])

        for fecha_iso, puntajes in por_fecha.items():
            prom = sum(puntajes) / len(puntajes)
            cal_data[fecha_iso] = {
                'prom': round(prom, 1),
                'n': len(puntajes),
                'color': _color(prom)
            }
    else:
        # Todos los cursos: agregar registros de todos los estudiantes del profesor
        if request.user.es_admin:
            ids_cursos = cursos.values_list('pk', flat=True)
        else:
            ids_cursos = cursos.values_list('pk', flat=True)
        ids_estudiantes = Inscripcion.objects.filter(
            curso_id__in=ids_cursos, activa=True
        ).values_list('estudiante_id', flat=True)

        inicio = hoy - timedelta(days=89)
        registros = RegistroEmocional.objects.filter(
            estudiante_id__in=ids_estudiantes,
            fecha__range=[inicio, hoy]
        ).values('fecha', 'puntaje')

        por_fecha = {}
        for r in registros:
            por_fecha.setdefault(r['fecha'].isoformat(), []).append(r['puntaje'])

        # También guardar por curso para el desglose
        curso_colores = {}
        cur_qs = cursos.prefetch_related()
        PALETTE = ['#7c6eff','#00d4aa','#ff6b9d','#f5b800','#00b8e6','#fd7e14','#e0284f','#a78bfa']
        for i, c in enumerate(cur_qs):
            curso_colores[c.pk] = PALETTE[i % len(PALETTE)]

        # por-curso por-fecha para el resumen multi-color
        cal_multi = {}  # fecha -> list of {curso, color, prom, n}
        insc_qs = Inscripcion.objects.filter(
            curso_id__in=ids_cursos, activa=True
        ).values('curso_id', 'estudiante_id')
        est_curso = {}
        for insc in insc_qs:
            est_curso.setdefault(insc['estudiante_id'], insc['curso_id'])

        regs_ext = RegistroEmocional.objects.filter(
            estudiante_id__in=ids_estudiantes,
            fecha__range=[inicio, hoy]
        ).values('fecha', 'puntaje', 'estudiante_id')

        por_curso_fecha = {}
        for r in regs_ext:
            cid = est_curso.get(r['estudiante_id'])
            key = (r['fecha'].isoformat(), cid)
            por_curso_fecha.setdefault(key, []).append(r['puntaje'])

        for (fecha_iso, cid), puntajes in por_curso_fecha.items():
            prom = sum(puntajes) / len(puntajes)
            cal_multi.setdefault(fecha_iso, []).append({
                'curso_id': cid,
                'color': curso_colores.get(cid, '#7c6eff'),
                'prom': round(prom, 1),
                'n': len(puntajes),
            })

        for fecha_iso, puntajes in por_fecha.items():
            prom = sum(puntajes) / len(puntajes)
            cal_data[fecha_iso] = {
                'prom': round(prom, 1),
                'n': len(puntajes),
                'color': _color(prom),
                'multi': cal_multi.get(fecha_iso, []),
            }

        # Pasar info de cursos con colores al contexto
        cursos_info = [
            {'nombre': c.nombre, 'color': curso_colores.get(c.pk, '#7c6eff')}
            for c in cur_qs
        ]

    # Citaciones del mes visible (para todos los profesores)
    from datetime import date as date_cls
    import calendar as cal_mod
    last_day = cal_mod.monthrange(year, month)[1]
    mes_inicio = date_cls(year, month, 1)
    mes_fin    = date_cls(year, month, last_day)
    citas_mes  = Citacion.objects.filter(
        fecha__range=[mes_inicio, mes_fin]
    ).select_related('estudiante', 'profesor').order_by('fecha', 'hora')

    for cita in citas_mes:
        iso = cita.fecha.isoformat()
        if iso not in citaciones_data:
            citaciones_data[iso] = []
        citaciones_data[iso].append({
            'id': cita.pk,
            'estudiante': cita.estudiante.get_full_name(),
            'profesor': cita.profesor.get_full_name(),
            'hora': cita.hora.strftime('%H:%M'),
            'motivo': cita.motivo[:60] + ('…' if len(cita.motivo) > 60 else ''),
            'estado': cita.estado,
            'urgente': cita.es_urgente,
        })

    pm = month-1 if month > 1 else 12
    py = year if month > 1 else year-1
    nm = month+1 if month < 12 else 1
    ny = year if month < 12 else year+1

    context = {
        'cursos': cursos,
        'curso_sel': curso_sel,
        'cal_data_json': json.dumps(cal_data),
        'citaciones_json': json.dumps(citaciones_data),
        'cursos_info_json': json.dumps(cursos_info if not curso_id else []),
        'hoy': hoy.isoformat(),
        'inicio': (hoy - timedelta(days=89)).isoformat(),
        'mes_actual': f'{year:04d}-{month:02d}',
        'mes_prev': f'{py:04d}-{pm:02d}',
        'mes_next': f'{ny:04d}-{nm:02d}',
        'mes_nombre': ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                       'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'][month-1],
        'mes_year': year,
    }
    return render(request, 'emotions/calendario_grupo.html', context)


# ─── NOTAS DEL PROFESOR ──────────────────────────────────────────────────────

@login_required
def notas_estudiante(request, estudiante_pk):
    """Lista y crea notas sobre un estudiante, organizadas por fecha."""
    from datetime import date as date_cls
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    estudiante = get_object_or_404(User, pk=estudiante_pk, rol=User.ROL_ESTUDIANTE)

    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        tipo = request.POST.get('tipo', 'observacion')
        fecha_str = request.POST.get('fecha', '')
        try:
            fecha = date_cls.fromisoformat(fecha_str) if fecha_str else date_cls.today()
        except ValueError:
            fecha = date_cls.today()
        if contenido:
            NotaProfesor.objects.create(
                profesor=request.user,
                estudiante=estudiante,
                contenido=contenido,
                tipo=tipo,
                fecha=fecha,
            )
            messages.success(request, 'Nota guardada correctamente.')
        return redirect(request.path)

    # Notas agrupadas por fecha — todos los profesores ven las notas de todos
    notas_qs = NotaProfesor.objects.filter(estudiante=estudiante).select_related('profesor').order_by('-fecha', '-created_at')

    # Agrupar por fecha
    from itertools import groupby
    notas_por_fecha = []
    for fecha, grupo in groupby(notas_qs, key=lambda n: n.fecha):
        notas_por_fecha.append({'fecha': fecha, 'notas': list(grupo)})

    # Registros recientes del estudiante para contexto
    registros = RegistroEmocional.objects.filter(
        estudiante=estudiante
    ).order_by('-fecha')[:14]

    context = {
        'estudiante': estudiante,
        'notas_por_fecha': notas_por_fecha,
        'registros': registros,
        'tipos': NotaProfesor.TIPO_CHOICES,
        'hoy': date_cls.today(),
    }
    return render(request, 'emotions/notas_estudiante.html', context)


@login_required
def nota_eliminar(request, pk):
    """Elimina una nota (solo el autor puede eliminarla)."""
    nota = get_object_or_404(NotaProfesor, pk=pk)
    if nota.profesor != request.user and not request.user.es_admin:
        return HttpResponseForbidden()
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'Nota eliminada.')
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ─── CITACIONES ──────────────────────────────────────────────────────────────

@login_required
def citaciones_lista(request):
    """Lista de citaciones:
    - Estudiantes: sus propias citaciones (próximas e historial)
    - Padres: citaciones de sus hijos vinculados solamente
    - Profesores/admin: todas las citaciones de la institución
    """
    hoy = date.today()

    if request.user.es_estudiante:
        proximas = Citacion.objects.filter(
            estudiante=request.user, fecha__gte=hoy
        ).exclude(estado='cancelada').select_related('profesor').order_by('fecha', 'hora')
        pasadas = Citacion.objects.filter(
            estudiante=request.user, fecha__lt=hoy
        ).select_related('profesor').order_by('-fecha', '-hora')
        context = {
            'proximas': proximas, 'pasadas': pasadas,
            'es_estudiante': True,
            'es_padre': False,
        }

    elif request.user.es_padre:
        from apps.accounts.models import VinculoPadreHijo
        ids_hijos = VinculoPadreHijo.objects.filter(
            padre=request.user, activo=True
        ).values_list('estudiante_id', flat=True)

        proximas = Citacion.objects.filter(
            estudiante_id__in=ids_hijos, fecha__gte=hoy
        ).exclude(estado='cancelada').select_related('estudiante', 'profesor').order_by('fecha', 'hora')
        pasadas = Citacion.objects.filter(
            estudiante_id__in=ids_hijos, fecha__lt=hoy
        ).select_related('estudiante', 'profesor').order_by('-fecha', '-hora')

        context = {
            'proximas': proximas, 'pasadas': pasadas,
            'es_estudiante': False,
            'es_padre': True,
        }

    else:
        # Profesores/admin: ven todas las citaciones de la institución
        proximas = Citacion.objects.filter(
            fecha__gte=hoy,
        ).exclude(estado='cancelada').select_related('estudiante', 'profesor').order_by('fecha', 'hora')
        pasadas = Citacion.objects.filter(
            fecha__lt=hoy,
        ).select_related('estudiante', 'profesor').order_by('-fecha', '-hora')

        estudiantes_disp = User.objects.filter(
            rol=User.ROL_ESTUDIANTE, activo=True
        ).order_by('first_name', 'last_name')

        context = {
            'proximas': proximas, 'pasadas': pasadas,
            'estudiantes_disp': estudiantes_disp,
            'lugares': Citacion.LUGAR_CHOICES,
            'hoy': hoy,
            'es_estudiante': False,
            'es_padre': False,
        }

    return render(request, 'emotions/citaciones.html', context)


@login_required
def citacion_crear(request):
    """Crea una citación. Solo profesores/admin."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.method == 'POST':
        est_pk    = request.POST.get('estudiante')
        fecha_str = request.POST.get('fecha','')
        hora_str  = request.POST.get('hora','')
        lugar     = request.POST.get('lugar','psicologia')
        lugar_otro= request.POST.get('lugar_otro','').strip()
        motivo    = request.POST.get('motivo','').strip()
        urgente   = request.POST.get('es_urgente') == '1'
        notas     = request.POST.get('notas_prof','').strip()

        estudiante = get_object_or_404(User, pk=est_pk, rol=User.ROL_ESTUDIANTE)

        try:
            from datetime import date as date_cls, time as time_cls, datetime as dt_cls
            fecha = date_cls.fromisoformat(fecha_str)
            hora  = dt_cls.strptime(hora_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, 'Fecha u hora inválida.')
            return redirect('emotions:citaciones_lista')

        if not motivo:
            messages.error(request, 'El motivo es obligatorio.')
            return redirect('emotions:citaciones_lista')

        cita = Citacion.objects.create(
            profesor=request.user,
            estudiante=estudiante,
            fecha=fecha,
            hora=hora,
            lugar=lugar,
            lugar_otro=lugar_otro,
            motivo=motivo,
            es_urgente=urgente,
            notas_prof=notas,
        )

        # Notificación al estudiante
        from .models import crear_notificacion
        urgente_txt = ' [URGENTE]' if urgente else ''
        crear_notificacion(
            usuario=estudiante,
            tipo='citacion',
            titulo=f'Nueva citación{urgente_txt} — {fecha.strftime("%d/%m/%Y")} {hora.strftime("%H:%M")}',
            cuerpo=(
                f'El profesor/a {request.user.get_full_name()} te cita en '
                f'{cita.get_lugar_display_full()} el {fecha.strftime("%d de %B de %Y")} '
                f'a las {hora.strftime("%H:%M")}. Motivo: {motivo[:120]}'
            ),
            url='/emotions/citaciones/',
        )
        # También mensaje directo para que aparezca en bandeja
        MensajeDirecto.objects.create(
            remitente=request.user,
            destinatario=estudiante,
            contenido=(
                f'--- CITACIÓN OFICIAL{urgente_txt} ---\n'
                f'Fecha: {fecha.strftime("%A, %d de %B de %Y")}\n'
                f'Hora: {hora.strftime("%H:%M")}\n'
                f'Lugar: {cita.get_lugar_display_full()}\n'
                f'Motivo: {motivo}\n'
                f'Estado: Pendiente de confirmación'
            ),
        )

        # Notificación a los padres/acudientes del estudiante
        from apps.accounts.models import VinculoPadreHijo
        padres_vinculados = VinculoPadreHijo.objects.filter(
            estudiante=estudiante, activo=True
        ).select_related('padre')
        for vinculo in padres_vinculados:
            crear_notificacion(
                usuario=vinculo.padre,
                tipo='citacion',
                titulo=f'Citación{urgente_txt} para {estudiante.get_full_name()} — {fecha.strftime("%d/%m/%Y")}',
                cuerpo=(
                    f'El/la Prof. {request.user.get_full_name()} ha citado a '
                    f'{estudiante.get_full_name()} en {cita.get_lugar_display_full()} '
                    f'el {fecha.strftime("%d de %B de %Y")} a las {hora.strftime("%H:%M")}. '
                    f'Motivo: {motivo[:120]}'
                ),
                url='/accounts/padre/citaciones/',
            )

        messages.success(request, f'Citación enviada a {estudiante.get_full_name()}.')
        return redirect('emotions:citaciones_lista')

    return redirect('emotions:citaciones_lista')


@login_required
def citacion_cambiar_estado(request, pk):
    """Cambia el estado de una citación (cancelar, completar, confirmar)."""
    cita = get_object_or_404(Citacion, pk=pk)
    es_prof = not request.user.es_estudiante
    es_est  = request.user == cita.estudiante

    if not (es_prof or es_est):
        return HttpResponseForbidden()

    nuevo = request.POST.get('estado', '')
    estados_validos = [e[0] for e in Citacion.ESTADO_CHOICES]
    if nuevo in estados_validos:
        # Estudiante solo puede confirmar; profesor puede todo
        if es_est and nuevo not in ('confirmada',):
            return HttpResponseForbidden()
        cita.estado = nuevo
        cita.save()
        if nuevo == 'cancelada':
            from .models import crear_notificacion
            otro = cita.estudiante if es_prof else cita.profesor
            crear_notificacion(
                usuario=otro, tipo='citacion',
                titulo='Citación cancelada',
                cuerpo=f'La cita del {cita.fecha.strftime("%d/%m/%Y")} a las {cita.hora.strftime("%H:%M")} fue cancelada.',
                url='/emotions/citaciones/',
            )
        messages.success(request, 'Estado actualizado.')
    return redirect(request.META.get('HTTP_REFERER', '/emotions/citaciones/'))


@login_required
def citaciones_pendientes_count(request):
    """Retorna el conteo de citaciones pendientes para el badge del sidebar."""
    from datetime import date as date_cls
    hoy = date_cls.today()
    if request.user.es_estudiante:
        count = Citacion.objects.filter(
            estudiante=request.user,
            estado='pendiente',
            fecha__gte=hoy,
        ).count()
    else:
        count = Citacion.objects.filter(
            profesor=request.user,
            estado='pendiente',
            fecha__gte=hoy,
        ).count()
    return JsonResponse({'count': count})


# ─── CHAT WIDGET FLOTANTE — mensajes entre usuarios reales ────────────────────

@login_required
def chat_widget_contactos(request):
    """
    Devuelve la lista de contactos con quienes el usuario puede chatear.
    - Estudiante: sus profesores (via inscripción) y los padres que lo tienen vinculado
    - Padre: los profesores de sus hijos (via inscripción)
    - Profesor: todos sus estudiantes (via inscripción) y los padres vinculados
    """
    from apps.courses.models import Inscripcion
    from apps.accounts.models import VinculoPadreHijo

    user = request.user
    contactos_pks = set()

    if user.es_estudiante:
        # Profesores del estudiante
        prof_pks = Inscripcion.objects.filter(
            estudiante=user, activa=True
        ).values_list('curso__profesor_id', flat=True)
        contactos_pks.update(prof_pks)
        # Padres vinculados al estudiante
        padre_pks = VinculoPadreHijo.objects.filter(
            estudiante=user, activo=True
        ).values_list('padre_id', flat=True)
        contactos_pks.update(padre_pks)

    elif user.es_padre:
        # Profesores de los hijos
        hijo_pks = VinculoPadreHijo.objects.filter(
            padre=user, activo=True
        ).values_list('estudiante_id', flat=True)
        prof_pks = Inscripcion.objects.filter(
            estudiante_id__in=hijo_pks, activa=True
        ).values_list('curso__profesor_id', flat=True)
        contactos_pks.update(prof_pks)
        # Hijos directamente
        contactos_pks.update(hijo_pks)

    elif user.es_profesor:
        # Estudiantes del profesor (sus cursos)
        est_pks = Inscripcion.objects.filter(
            curso__profesor=user, activa=True
        ).values_list('estudiante_id', flat=True)
        contactos_pks.update(est_pks)
        # Padres vinculados a esos estudiantes
        padre_pks = VinculoPadreHijo.objects.filter(
            estudiante_id__in=est_pks, activo=True
        ).values_list('padre_id', flat=True)
        contactos_pks.update(padre_pks)

    contactos_pks.discard(user.pk)

    ROL_LABELS = {
        User.ROL_PROFESOR:   'Profesor/a',
        User.ROL_ESTUDIANTE: 'Estudiante',
        User.ROL_PADRE:      'Padre / Acudiente',
    }

    contactos_qs = User.objects.filter(pk__in=contactos_pks).order_by('first_name', 'last_name')

    total_no_leidos = 0
    result = []
    for c in contactos_qs:
        no_leidos = MensajeDirecto.objects.filter(
            remitente=c, destinatario=user, leido=False
        ).count()
        total_no_leidos += no_leidos
        result.append({
            'pk': c.pk,
            'nombre': c.get_full_name() or c.username,
            'rol_label': ROL_LABELS.get(c.rol, c.rol),
            'no_leidos': no_leidos,
        })

    # Ordenar: primero los que tienen mensajes no leídos
    result.sort(key=lambda x: -x['no_leidos'])

    return JsonResponse({'contactos': result, 'total_no_leidos': total_no_leidos})


@login_required
def chat_widget_conversacion(request, pk):
    """Devuelve los últimos 50 mensajes entre el usuario actual y el contacto pk."""
    from django.db.models import Q
    contacto = get_object_or_404(User, pk=pk)

    mensajes = MensajeDirecto.objects.filter(
        Q(remitente=request.user, destinatario=contacto) |
        Q(remitente=contacto, destinatario=request.user)
    ).order_by('-created_at')[:50]

    mensajes = list(reversed(mensajes))

    # Marcar como leídos los recibidos
    MensajeDirecto.objects.filter(
        remitente=contacto, destinatario=request.user, leido=False
    ).update(leido=True)

    return JsonResponse({
        'mensajes': [
            {
                'pk': m.pk,
                'remitente_pk': m.remitente_id,
                'remitente_nombre': m.remitente.get_full_name() or m.remitente.username,
                'contenido': m.contenido,
                'created_at': m.created_at.isoformat(),
            }
            for m in mensajes
        ]
    })


@login_required
@require_POST
def chat_widget_enviar(request, pk):
    """Envía un mensaje directo al usuario con pk."""
    import json as _json
    contacto = get_object_or_404(User, pk=pk)

    try:
        data = _json.loads(request.body)
        contenido = data.get('contenido', '').strip()
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not contenido:
        return JsonResponse({'ok': False, 'error': 'Mensaje vacío'}, status=400)

    if len(contenido) > 1000:
        return JsonResponse({'ok': False, 'error': 'Mensaje muy largo (máx. 1000 caracteres)'}, status=400)

    MensajeDirecto.objects.create(
        remitente=request.user,
        destinatario=contacto,
        contenido=contenido,
    )
    return JsonResponse({'ok': True})
