# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import RegistroEmocional, Alerta, MetaSemanal, EntradaDiario, EMOCION_CHOICES, EMOCION_EMOJIS, EMOCION_COLORES, verificar_logros, LOGROS_CATALOGO
from apps.accounts.models import User


def _lunes_de(d):
    return d - timedelta(days=d.weekday())


@login_required
def registrar_emocion(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden('Solo los estudiantes pueden registrar emociones.')

    hoy = date.today()
    ya_registro = RegistroEmocional.objects.filter(estudiante=request.user, fecha=hoy).first()

    # Meta semanal
    lunes = _lunes_de(hoy)
    meta_semana, _ = MetaSemanal.objects.get_or_create(
        estudiante=request.user, semana_inicio=lunes,
        defaults={'texto': ''}
    )

    if request.method == 'POST':
        accion = request.POST.get('accion', 'emocion')

        # Guardar meta semanal
        if accion == 'meta':
            texto = request.POST.get('meta_texto', '').strip()
            if texto:
                meta_semana.texto = texto
                meta_semana.save()
                messages.success(request, '¡Meta de la semana guardada.')
            return redirect('emotions:registrar')

        # Marcar meta como cumplida
        if accion == 'meta_cumplida':
            meta_semana.cumplida = not meta_semana.cumplida
            meta_semana.save()
            return redirect('emotions:registrar')

        # Registro emocional
        emocion = request.POST.get('emocion')
        puntaje = request.POST.get('puntaje')
        comentario = request.POST.get('comentario', '').strip()
        emociones_validas = [e[0] for e in EMOCION_CHOICES]

        if emocion not in emociones_validas:
            messages.error(request, 'Por favor selecciona una emocion valida.')
        elif not puntaje or not puntaje.isdigit() or not (1 <= int(puntaje) <= 5):
            messages.error(request, 'Por favor selecciona una escala del 1 al 5.')
        else:
            if ya_registro:
                ya_registro.emocion = emocion
                ya_registro.puntaje = int(puntaje)
                ya_registro.comentario = comentario
                ya_registro.save()
                messages.success(request, '¡Registro emocional actualizado! ')
            else:
                RegistroEmocional.objects.create(
                    estudiante=request.user, fecha=hoy,
                    emocion=emocion, puntaje=int(puntaje), comentario=comentario,
                )
                messages.success(request, '¡Gracias por compartir como te sientes hoy! ')
            return redirect('dashboard:inicio')

    historial = RegistroEmocional.objects.filter(
        estudiante=request.user, fecha__gte=hoy - timedelta(days=6)
    ).order_by('-fecha')

    context = {
        'emociones': EMOCION_CHOICES,
        'emojis': EMOCION_EMOJIS,
        'ya_registro': ya_registro,
        'historial': historial,
        'hoy': hoy,
        'meta_semana': meta_semana,
    }
    return render(request, 'emotions/registrar.html', context)


@login_required
def historial_propio(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    registros = RegistroEmocional.objects.filter(estudiante=request.user).order_by('-fecha')

    hoy = date.today()
    fechas, puntajes = [], []
    for i in range(29, -1, -1):
        dia = hoy - timedelta(days=i)
        reg = registros.filter(fecha=dia).first()
        fechas.append(dia.strftime('%d/%m'))
        puntajes.append(reg.puntaje if reg else None)

    # Estadisticas personales
    total = registros.count()
    sample = list(registros[:90])
    promedio = round(sum(r.puntaje for r in sample) / len(sample), 1) if sample else None
    conteo_emociones = {}
    for e, _ in EMOCION_CHOICES:
        conteo_emociones[e] = registros.filter(emocion=e).count()

    # Racha actual
    racha = 0
    dia = hoy
    while registros.filter(fecha=dia).exists():
        racha += 1
        dia -= timedelta(days=1)
        if racha > 60:
            break

    # Metas de las ultimas 4 semanas
    metas = MetaSemanal.objects.filter(
        estudiante=request.user,
        semana_inicio__gte=hoy - timedelta(weeks=4)
    ).order_by('-semana_inicio')

    context = {
        'registros': registros[:30],
        'fechas_json': json.dumps(fechas),
        'puntajes_json': json.dumps(puntajes),
        'conteo_emociones_json': json.dumps(conteo_emociones),
        'conteo_emociones': conteo_emociones,
        'total_registros': max(total, 1),
        'promedio': promedio,
        'racha': racha,
        'metas': metas,
    }
    return render(request, 'emotions/historial.html', context)


@login_required
def alertas_view(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.user.es_admin:
        alertas = Alerta.objects.filter(resuelta=False).select_related('estudiante').order_by('-fecha_creacion')
        ids_estudiantes = User.objects.filter(rol=User.ROL_ESTUDIANTE).values_list('id', flat=True)
    else:
        from apps.courses.models import Inscripcion
        ids_estudiantes = Inscripcion.objects.filter(
            curso__profesor=request.user, activa=True
        ).values_list('estudiante_id', flat=True)
        alertas = Alerta.objects.filter(
            estudiante_id__in=ids_estudiantes, resuelta=False
        ).select_related('estudiante').order_by('-fecha_creacion')

    alertas_resueltas = Alerta.objects.filter(
        estudiante_id__in=ids_estudiantes,
        resuelta=True
    ).select_related('estudiante', 'resuelta_por').order_by('-fecha_resolucion')[:20]

    # Paginación: 25 alertas por página para no saturar la vista con 1000+ estudiantes
    pag = Paginator(alertas, 25)
    page_obj = pag.get_page(request.GET.get('page'))
    context = {
        'alertas': page_obj,
        'page_obj': page_obj,
        'alertas_resueltas': alertas_resueltas,
        'total_alertas': alertas.count(),
    }
    return render(request, 'emotions/alertas.html', context)


@login_required
def resolver_alerta(request, pk):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == 'POST':
        nota = request.POST.get('nota', '').strip()
        alerta.resuelta = True
        alerta.nota_resolucion = nota
        alerta.fecha_resolucion = timezone.now()
        alerta.resuelta_por = request.user
        alerta.save()
        messages.success(request, 'Alerta marcada como resuelta.')

    return redirect('emotions:alertas')


@login_required
def resumen_grupo(request):
    """Vista de resumen emocional de un grupo para el profesor."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    from apps.courses.models import Inscripcion, Curso
    hoy = date.today()

    if request.user.es_admin:
        cursos = Curso.objects.filter(activo=True)
    else:
        cursos = Curso.objects.filter(profesor=request.user, activo=True)

    curso_id = request.GET.get('curso')
    curso_sel = None
    estudiantes_data = []

    if curso_id:
        curso_sel = get_object_or_404(Curso, pk=curso_id)
        inscripciones = Inscripcion.objects.filter(curso=curso_sel, activa=True).select_related('estudiante')
        ids_est = [insc.estudiante_id for insc in inscripciones]
        est_map = {insc.estudiante_id: insc.estudiante for insc in inscripciones}

        # Bulk: registros de hoy de todos los estudiantes de una sola query
        regs_hoy_map = {
            r.estudiante_id: r
            for r in RegistroEmocional.objects.filter(estudiante_id__in=ids_est, fecha=hoy)
        }
        # Bulk: último registro de cada estudiante (una sola query)
        from django.db.models import Max
        ultimas_fechas = (
            RegistroEmocional.objects
            .filter(estudiante_id__in=ids_est)
            .values('estudiante_id')
            .annotate(ultima=Max('fecha'))
        )
        ultima_fecha_map = {r['estudiante_id']: r['ultima'] for r in ultimas_fechas}
        ult_regs_qs = RegistroEmocional.objects.filter(
            estudiante_id__in=[r['estudiante_id'] for r in ultimas_fechas],
            fecha__in=[r['ultima'] for r in ultimas_fechas],
        )
        ult_reg_map = {r.estudiante_id: r for r in ult_regs_qs}

        # Bulk: alertas activas por estudiante
        from django.db.models import Count
        alertas_counts = {
            r['estudiante_id']: r['total']
            for r in Alerta.objects.filter(estudiante_id__in=ids_est, resuelta=False)
            .values('estudiante_id')
            .annotate(total=Count('id'))
        }
        # Bulk: registros de los últimos 7 días para calcular tendencia
        semana_inicio = hoy - timedelta(days=6)
        regs_semana_todos = list(
            RegistroEmocional.objects
            .filter(estudiante_id__in=ids_est, fecha__gte=semana_inicio)
            .order_by('estudiante_id', 'fecha')
            .values('estudiante_id', 'puntaje', 'fecha')
        )
        from collections import defaultdict
        regs_semana_map = defaultdict(list)
        for r in regs_semana_todos:
            regs_semana_map[r['estudiante_id']].append(r['puntaje'])

        for est_id in ids_est:
            est = est_map[est_id]
            regs_semana = regs_semana_map[est_id]
            tendencia = None
            if len(regs_semana) >= 2:
                diff = regs_semana[-1] - regs_semana[0]
                tendencia = 'subiendo' if diff > 0 else ('bajando' if diff < 0 else 'estable')
            estudiantes_data.append({
                'estudiante': est,
                'ult_reg': ult_reg_map.get(est_id),
                'reg_hoy': regs_hoy_map.get(est_id),
                'alertas': alertas_counts.get(est_id, 0),
                'tendencia': tendencia,
            })

    # Filtros opcionales para facilitar gestión con grupos grandes
    filtro = request.GET.get('filtro', '')  # 'alertas', 'sin_registrar', 'tendencia_baja'
    orden = request.GET.get('orden', 'nombre')

    if filtro == 'alertas':
        estudiantes_data = [e for e in estudiantes_data if e['alertas'] > 0]
    elif filtro == 'sin_registrar':
        estudiantes_data = [e for e in estudiantes_data if not e['reg_hoy']]
    elif filtro == 'tendencia_baja':
        estudiantes_data = [e for e in estudiantes_data if e['tendencia'] == 'bajando']

    if orden == 'alertas':
        estudiantes_data.sort(key=lambda x: -x['alertas'])
    elif orden == 'puntaje':
        estudiantes_data.sort(key=lambda x: (x['ult_reg'].puntaje if x['ult_reg'] else 99))
    else:
        estudiantes_data.sort(key=lambda x: x['estudiante'].get_full_name())

    # Paginación — 30 por página para grupos de 1000+
    pag = Paginator(estudiantes_data, 30)
    page_obj = pag.get_page(request.GET.get('page'))

    context = {
        'cursos': cursos,
        'curso_sel': curso_sel,
        'estudiantes_data': page_obj,
        'page_obj': page_obj,
        'total': len(estudiantes_data),
        'hoy': hoy,
        'filtro': filtro,
        'orden': orden,
    }
    return render(request, 'emotions/resumen_grupo.html', context)


# ─── DIARIO DEL ESTUDIANTE ────────────────────────────────────────────────────

@login_required
def diario_lista(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    entradas_qs = EntradaDiario.objects.filter(estudiante=request.user).order_by('-created_at')

    filtro_emocion = request.GET.get('emocion', '')
    if filtro_emocion:
        entradas_qs = entradas_qs.filter(emocion_del_dia=filtro_emocion)

    q = request.GET.get('q', '')
    if q:
        from django.db.models import Q
        entradas_qs = entradas_qs.filter(Q(titulo__icontains=q) | Q(contenido__icontains=q))

    entradas = list(entradas_qs)

    from django.urls import reverse
    import json as _json
    entries_json = _json.dumps([
        {
            'idx': i,
            'pk': e.pk,
            'title': e.titulo or 'Sin titulo',
            'dateShort': e.created_at.strftime('%d/%m/%Y %H:%M'),
            'dateLong': e.created_at.strftime('%A, %d de %B de %Y'),
            'emo': EMOCION_EMOJIS.get(e.emocion_del_dia, 'bi-pencil-square') if e.emocion_del_dia else 'bi-pencil-square',
            'emoColor': EMOCION_COLORES.get(e.emocion_del_dia, '#8884a8') if e.emocion_del_dia else '#8884a8',
            'emoLabel': dict(EMOCION_CHOICES).get(e.emocion_del_dia, '') if e.emocion_del_dia else '',
            'private': e.es_privado,
            'content': e.contenido or '',
            'editUrl': reverse('emotions:diario_editar', args=[e.pk]),
            'delUrl': reverse('emotions:diario_eliminar', args=[e.pk]),
        }
        for i, e in enumerate(entradas)
    ], ensure_ascii=False)

    context = {
        'entradas': entradas,
        'entries_json': entries_json,
        'total': EntradaDiario.objects.filter(estudiante=request.user).count(),
        'emociones': EMOCION_CHOICES,
        'emojis': EMOCION_EMOJIS,
        'filtro_emocion': filtro_emocion,
        'hoy': date.today(),
        'q': q,
    }
    return render(request, 'emotions/diario_lista.html', context)


@login_required
def diario_nueva(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        contenido = request.POST.get('contenido', '').strip()
        emocion = request.POST.get('emocion_del_dia', '')
        es_privado = request.POST.get('es_privado', 'on') == 'on'

        if not contenido:
            messages.error(request, 'El contenido no puede estar vacio.')
        else:
            entrada = EntradaDiario.objects.create(
                estudiante=request.user,
                titulo=titulo or date.today().strftime('%d/%m/%Y'),
                contenido=contenido,
                emocion_del_dia=emocion,
                es_privado=es_privado,
                estado='guardado',
            )
            messages.success(request, 'Entrada guardada en tu diario.')
            return redirect('emotions:diario_detalle', pk=entrada.pk)

    context = {
        'emociones': EMOCION_CHOICES,
        'emojis': EMOCION_EMOJIS,
        'hoy': date.today(),
    }
    return render(request, 'emotions/diario_editar.html', context)


@login_required
def diario_detalle(request, pk):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    entrada = get_object_or_404(EntradaDiario, pk=pk, estudiante=request.user)
    return render(request, 'emotions/diario_detalle.html', {'entrada': entrada})


@login_required
def diario_editar(request, pk):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    entrada = get_object_or_404(EntradaDiario, pk=pk, estudiante=request.user)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        contenido = request.POST.get('contenido', '').strip()
        emocion = request.POST.get('emocion_del_dia', '')
        es_privado = request.POST.get('es_privado', 'on') == 'on'

        if not contenido:
            messages.error(request, 'El contenido no puede estar vacio.')
        else:
            entrada.titulo = titulo or entrada.created_at.strftime('%d/%m/%Y')
            entrada.contenido = contenido
            entrada.emocion_del_dia = emocion
            entrada.es_privado = es_privado
            entrada.estado = 'guardado'
            entrada.save()
            messages.success(request, 'Entrada actualizada.')
            return redirect('emotions:diario_detalle', pk=entrada.pk)

    context = {
        'entrada': entrada,
        'emociones': EMOCION_CHOICES,
        'emojis': EMOCION_EMOJIS,
    }
    return render(request, 'emotions/diario_editar.html', context)


@login_required
def diario_eliminar(request, pk):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    entrada = get_object_or_404(EntradaDiario, pk=pk, estudiante=request.user)
    if request.method == 'POST':
        entrada.delete()
        messages.success(request, 'Entrada eliminada.')
    return redirect('emotions:diario_lista')
