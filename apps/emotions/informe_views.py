# -*- coding: utf-8 -*-
"""
Informe IA para profesores — genera un PDF detallado con analisis emocional
de los estudiantes de un curso, usando la API de Anthropic para el analisis.
"""
import json
import io
import urllib.request
import urllib.error
from datetime import date, timedelta
from collections import Counter

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from .models import RegistroEmocional, Alerta, EMOCION_EMOJIS, EMOCION_COLORES
from apps.accounts.models import User
from apps.courses.models import Curso, Inscripcion
from conectate.settings import ANTHROPIC_API_KEY


# ─── Helpers de analisis ──────────────────────────────────────────────────────

def _stats_estudiante(est, dias=30):
    """
    Calcula estadisticas emocionales de UN estudiante.
    Para cursos grandes usa _stats_bulk_curso() que es mucho más eficiente.
    """
    return _stats_bulk_curso([est], dias).get(est.pk)


def _stats_bulk_curso(estudiantes, dias=30):
    """
    Calcula estadísticas emocionales de una lista de estudiantes en BULK.
    Una sola query de registros + una sola query de alertas.
    Retorna dict {pk: stats_dict}.
    Con 1000 estudiantes: 2 queries en vez de 4000+.
    """
    from django.db.models import Count as _Count
    hoy = date.today()
    inicio = hoy - timedelta(days=dias)
    ids = [e.pk for e in estudiantes]
    est_map = {e.pk: e for e in estudiantes}

    # 1 query: todos los registros del periodo para todos los estudiantes
    todos_regs = list(
        RegistroEmocional.objects
        .filter(estudiante_id__in=ids, fecha__gte=inicio)
        .order_by('estudiante_id', 'fecha')
        .values('estudiante_id', 'puntaje', 'emocion', 'fecha')
    )

    # 1 query: alertas activas por estudiante
    alertas_map = {
        r['estudiante_id']: r['total']
        for r in Alerta.objects
        .filter(estudiante_id__in=ids, resuelta=False)
        .values('estudiante_id')
        .annotate(total=_Count('id'))
    }

    # Agrupar registros por estudiante en memoria
    from collections import defaultdict
    regs_por_est = defaultdict(list)
    for r in todos_regs:
        regs_por_est[r['estudiante_id']].append(r)

    resultado = {}
    for pk, est in est_map.items():
        regs = regs_por_est[pk]  # ya ordenados por fecha
        total = len(regs)
        if total == 0:
            resultado[pk] = None
            continue

        puntajes = [r['puntaje'] for r in regs]
        emociones = [r['emocion'] for r in regs]
        fechas_set = {r['fecha'] for r in regs}
        conteo = Counter(emociones)
        emocion_dom = conteo.most_common(1)[0][0] if conteo else None

        # Tendencia: primera vs segunda mitad
        mitad = total // 2
        if mitad > 0:
            prom_inicio = sum(puntajes[:mitad]) / mitad
            prom_fin    = sum(puntajes[mitad:]) / (total - mitad)
            tendencia   = round(prom_fin - prom_inicio, 2)
        else:
            tendencia = 0

        # Racha: días consecutivos hasta hoy (calculada sobre fechas en memoria)
        racha = 0
        dia = hoy
        while dia in fechas_set:
            racha += 1
            dia -= timedelta(days=1)
            if racha > 60:
                break

        dias_bajos = sum(1 for p in puntajes if p <= 2)

        resultado[pk] = {
            'pk': pk,
            'nombre': est.get_full_name(),
            'username': est.username,
            'total_registros': total,
            'promedio': round(sum(puntajes) / total, 2),
            'puntaje_max': max(puntajes),
            'puntaje_min': min(puntajes),
            'emocion_dominante': emocion_dom,
            'conteo_emociones': dict(conteo),
            'tendencia': tendencia,
            'racha': racha,
            'dias_bajos': dias_bajos,
            'alertas_activas': alertas_map.get(pk, 0),
            'puntajes_serie': puntajes,
        }

    return resultado


def _construir_texto_para_ia(curso, stats_lista, dias):
    """Construye el texto del prompt con los datos del curso para la IA."""
    hoy = date.today()
    lineas = [
        f"Analiza los datos emocionales del curso '{curso.nombre}' ({curso.grado})",
        f"Periodo: ultimos {dias} dias (hasta {hoy.strftime('%d/%m/%Y')})",
        f"Total estudiantes con datos: {len(stats_lista)}",
        "",
        "DATOS POR ESTUDIANTE:",
    ]

    for s in stats_lista:
        emo_str = ', '.join(f"{k}: {v}" for k, v in s['conteo_emociones'].items())
        tend = "↑ mejorando" if s['tendencia'] > 0.3 else ("↓ bajando" if s['tendencia'] < -0.3 else "→ estable")
        lineas.append(
            f"- {s['nombre']}: promedio={s['promedio']}/5, "
            f"registros={s['total_registros']}, tendencia={tend}, "
            f"emociones=[{emo_str}], dias_bajos={s['dias_bajos']}, "
            f"alertas_activas={s['alertas_activas']}, racha={s['racha']} dias"
        )

    # Promedios generales del curso
    todos_promedios = [s['promedio'] for s in stats_lista]
    promedio_curso  = round(sum(todos_promedios) / len(todos_promedios), 2) if todos_promedios else 0
    lineas += [
        "",
        f"RESUMEN DEL CURSO: promedio_general={promedio_curso}/5",
        f"estudiantes_con_alertas={sum(1 for s in stats_lista if s['alertas_activas'] > 0)}",
        f"estudiantes_tendencia_baja={sum(1 for s in stats_lista if s['tendencia'] < -0.3)}",
    ]

    return '\n'.join(lineas)


SYSTEM_INFORME = """Eres un experto en psicologia educativa y bienestar estudiantil.
Recibes datos emocionales numericos de estudiantes de un curso colombiano y debes generar
un informe profesional, claro y util para el profesor.

El informe debe incluir:
1. RESUMEN EJECUTIVO (2-3 parrafos): estado general del grupo, hallazgos mas importantes
2. ESTUDIANTES QUE REQUIEREN ATENCION: lista de los que tienen alertas, tendencia baja o muchos dias bajos, con recomendacion especifica para cada uno
3. FORTALEZAS DEL GRUPO: aspectos positivos detectados
4. RECOMENDACIONES GENERALES (3-5 puntos): acciones concretas que el profesor puede tomar
5. NOTA METODOLOGICA: breve explicacion de como interpretar los datos

Usa lenguaje profesional pero accesible. No uses formato markdown con asteriscos — usa
texto plano con titulos en MAYUSCULAS y vinetas con guion (-).
Se especifico con nombres cuando sea relevante.
Responde en espanol colombiano."""


def _llamar_anthropic_informe(texto_datos):
    """Llama a Claude para generar el analisis del informe."""
    if not ANTHROPIC_API_KEY:
        return None, "API key no configurada en settings.py"

    payload = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 2000,
        'system': SYSTEM_INFORME,
        'messages': [{'role': 'user', 'content': texto_datos}],
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['content'][0]['text'], None
    except urllib.error.HTTPError as e:
        return None, f"Error HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return None, str(e)


# ─── Generacion del PDF con reportlab ─────────────────────────────────────────

def _generar_pdf(curso, stats_lista, analisis_ia, dias):
    """Genera el PDF del informe usando reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        return None, "reportlab no instalado. Ejecuta: pip install reportlab"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    # Estilos
    styles = getSampleStyleSheet()
    COLOR_PRIMARY = colors.HexColor('#6c63ff')
    COLOR_DARK    = colors.HexColor('#1e1b4b')
    COLOR_DANGER  = colors.HexColor('#dc3545')
    COLOR_SUCCESS = colors.HexColor('#28a745')
    COLOR_WARN    = colors.HexColor('#fd7e14')
    COLOR_LIGHT   = colors.HexColor('#f8f9fa')
    COLOR_GRAY    = colors.HexColor('#6c757d')

    st_titulo = ParagraphStyle('titulo',
        fontSize=22, textColor=COLOR_DARK, spaceAfter=4,
        fontName='Helvetica-Bold', alignment=TA_CENTER)
    st_sub = ParagraphStyle('sub',
        fontSize=11, textColor=COLOR_GRAY, spaceAfter=2,
        fontName='Helvetica', alignment=TA_CENTER)
    st_h1 = ParagraphStyle('h1',
        fontSize=13, textColor=COLOR_PRIMARY, spaceBefore=14, spaceAfter=6,
        fontName='Helvetica-Bold')
    st_h2 = ParagraphStyle('h2',
        fontSize=11, textColor=COLOR_DARK, spaceBefore=8, spaceAfter=4,
        fontName='Helvetica-Bold')
    st_body = ParagraphStyle('body',
        fontSize=9, textColor=colors.HexColor('#2d2d2d'),
        fontName='Helvetica', spaceAfter=4, leading=14)
    st_small = ParagraphStyle('small',
        fontSize=8, textColor=COLOR_GRAY, fontName='Helvetica', leading=11)

    story = []
    hoy = date.today()

    # ── Encabezado ──
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("CONECTATE — SISTEMA DE EDUCACION EMOCIONAL", st_sub))
    story.append(Paragraph("Informe de Bienestar Emocional Estudiantil", st_titulo))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Curso: {curso.nombre}  |  Grado: {curso.grado}  |  "
        f"Profesor/a: {curso.profesor.get_full_name() if curso.profesor else 'N/A'}",
        st_sub))
    story.append(Paragraph(
        f"Periodo analizado: ultimos {dias} dias  |  Generado el {hoy.strftime('%d/%m/%Y')}",
        st_sub))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width='100%', thickness=2, color=COLOR_PRIMARY))
    story.append(Spacer(1, 0.4*cm))

    # ── Stats del curso ──
    todos_prom = [s['promedio'] for s in stats_lista]
    prom_curso = round(sum(todos_prom)/len(todos_prom), 2) if todos_prom else 0
    n_alertas  = sum(1 for s in stats_lista if s['alertas_activas'] > 0)
    n_baja     = sum(1 for s in stats_lista if s['tendencia'] < -0.3)
    n_buena    = sum(1 for s in stats_lista if s['tendencia'] > 0.3)
    participacion = round(len(stats_lista) / max(
        Inscripcion.objects.filter(curso=curso, activa=True).count(), 1) * 100)

    stat_data = [
        ['Indicador', 'Valor', 'Estado'],
        ['Promedio emocional del curso', f'{prom_curso}/5',
         'Bueno' if prom_curso >= 3.5 else ('Regular' if prom_curso >= 2.5 else 'Critico')],
        ['Estudiantes con datos', f'{len(stats_lista)}', '—'],
        ['Participacion en registros', f'{participacion}%',
         'Alta' if participacion >= 70 else ('Media' if participacion >= 40 else 'Baja')],
        ['Estudiantes con alertas activas', str(n_alertas),
         'Sin alertas' if n_alertas == 0 else f'Atencion requerida'],
        ['Tendencia a la baja', str(n_baja),
         'Sin casos' if n_baja == 0 else 'Monitorear'],
        ['Tendencia positiva', str(n_buena), f'{n_buena} estudiante(s)'],
    ]

    col_w = [8*cm, 3.5*cm, 5*cm]
    tabla_stats = Table(stat_data, colWidths=col_w)
    tabla_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 9),
        ('FONTSIZE',   (0,1), (-1,-1), 8),
        ('FONTNAME',   (0,1), (-1,-1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [COLOR_LIGHT, colors.white]),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (0,-1), 8),
    ]))

    story.append(Paragraph("RESUMEN ESTADISTICO DEL CURSO", st_h1))
    story.append(tabla_stats)
    story.append(Spacer(1, 0.5*cm))

    # ── Tabla detalle por estudiante ──
    story.append(Paragraph("DETALLE POR ESTUDIANTE", st_h1))

    EMO_LABELS = {'feliz':'Feliz','tranquilo':'Tranquilo','estresado':'Estresado','triste':'Triste','enojado':'Enojado'}
    header = ['Estudiante', 'Promedio', 'Registros', 'Emocion\nDominante', 'Tendencia', 'Dias\nBajos', 'Alertas']
    data_est = [header]

    for s in sorted(stats_lista, key=lambda x: x['promedio']):
        tend_str = '↑ Mejorando' if s['tendencia'] > 0.3 else ('↓ Bajando' if s['tendencia'] < -0.3 else '→ Estable')
        emo_label = EMO_LABELS.get(s['emocion_dominante'], s['emocion_dominante'] or '—')
        row = [
            s['nombre'],
            str(s['promedio']),
            str(s['total_registros']),
            emo_label,
            tend_str,
            str(s['dias_bajos']),
            str(s['alertas_activas']) if s['alertas_activas'] == 0 else f"[!] {s['alertas_activas']}",
        ]
        data_est.append(row)

    col_w2 = [5.5*cm, 1.8*cm, 2*cm, 2.8*cm, 2.5*cm, 1.5*cm, 1.5*cm]
    tabla_est = Table(data_est, colWidths=col_w2)

    row_styles = [
        ('BACKGROUND', (0,0), (-1,0), COLOR_DARK),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 8),
        ('FONTSIZE',   (0,1), (-1,-1), 7.5),
        ('FONTNAME',   (0,1), (-1,-1), 'Helvetica'),
        ('GRID',       (0,0), (-1,-1), 0.4, colors.HexColor('#dee2e6')),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (0,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_LIGHT]),
    ]
    # Colorear filas con promedio bajo o alertas
    for i, s in enumerate(sorted(stats_lista, key=lambda x: x['promedio']), start=1):
        if s['promedio'] <= 2.0 or s['alertas_activas'] > 0:
            row_styles.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#fff5f5')))
            row_styles.append(('TEXTCOLOR',  (0,i), (0,i), COLOR_DANGER))
        elif s['promedio'] >= 4.0 and s['tendencia'] > 0:
            row_styles.append(('TEXTCOLOR', (0,i), (0,i), COLOR_SUCCESS))

    tabla_est.setStyle(TableStyle(row_styles))
    story.append(tabla_est)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "* Filas en rojo: estudiantes con promedio critico (<=2) o alertas activas. "
        "Filas en verde: estudiantes con excelente bienestar (>=4 y tendencia positiva).",
        st_small))
    story.append(Spacer(1, 0.5*cm))

    # ── Analisis IA ──
    if analisis_ia:
        story.append(HRFlowable(width='100%', thickness=1, color=COLOR_PRIMARY))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("ANALISIS GENERADO POR INTELIGENCIA ARTIFICIAL", st_h1))
        story.append(Paragraph(
            "El siguiente analisis fue generado automaticamente por Claude (Anthropic) "
            "basandose en los datos emocionales del periodo. Debe complementarse con "
            "la observacion directa del profesor.",
            st_small))
        story.append(Spacer(1, 0.3*cm))

        # Dividir el analisis en parrafos
        for bloque in analisis_ia.split('\n\n'):
            bloque = bloque.strip()
            if not bloque:
                continue
            if bloque.isupper() or bloque.startswith(('1.','2.','3.','4.','5.')):
                story.append(Paragraph(bloque, st_h2))
            else:
                for linea in bloque.split('\n'):
                    linea = linea.strip()
                    if linea:
                        story.append(Paragraph(linea, st_body))
        story.append(Spacer(1, 0.3*cm))
    else:
        story.append(Paragraph(
            "Nota: El analisis de IA no esta disponible (API key no configurada).",
            st_small))

    # ── Pie de pagina ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=COLOR_GRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Informe confidencial generado por el sistema Conectate. "
        f"Fecha de generacion: {hoy.strftime('%d/%m/%Y')}. "
        f"Para uso exclusivo del personal docente.",
        st_small))

    doc.build(story)
    buffer.seek(0)
    return buffer, None


# ─── Vistas ──────────────────────────────────────────────────────────────────

@login_required
def informe_selector(request):
    """Pagina para seleccionar el curso y configurar el informe."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    # Todos los profesores ven todos los cursos
    cursos = Curso.objects.filter(activo=True).select_related('profesor')
    context = {'cursos': cursos}
    return render(request, 'emotions/informe_selector.html', context)


@login_required
def informe_excel(request, curso_id):
    """Descarga el informe en formato Excel (.xlsx) con diseño profesional."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    curso = get_object_or_404(Curso, pk=curso_id, activo=True)
    dias = int(request.GET.get('dias', 30))
    dias = min(max(dias, 7), 90)

    inscritos = Inscripcion.objects.filter(curso=curso, activa=True).select_related('estudiante')
    stats_lista = [s for insc in inscritos
                   if (s := _stats_estudiante(insc.estudiante, dias)) is not None]

    if not stats_lista:
        return HttpResponse('No hay datos suficientes para generar el informe.', status=400)

    try:
        from .excel_export import generar_excel_profesor
        buffer = generar_excel_profesor(curso, stats_lista, dias)
    except ImportError:
        return HttpResponse('openpyxl no instalado. Ejecuta: pip install openpyxl', status=500)

    nombre = f"informe_{curso.nombre.replace(' ','_')}_{date.today().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


@login_required
def informe_preview(request, curso_id):
    """Vista previa del informe antes de descargar el PDF."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    curso = get_object_or_404(Curso, pk=curso_id, activo=True)
    if not request.user.es_admin and curso.profesor != request.user:
        return HttpResponseForbidden()

    dias = int(request.GET.get('dias', 30))
    dias = min(max(dias, 7), 90)

    # Calcular stats de todos los estudiantes en BULK (2 queries sin importar cuántos sean)
    inscritos = Inscripcion.objects.filter(curso=curso, activa=True).select_related('estudiante')
    estudiantes = [insc.estudiante for insc in inscritos]
    bulk = _stats_bulk_curso(estudiantes, dias)
    stats_lista = []
    sin_datos = []
    for est in estudiantes:
        s = bulk.get(est.pk)
        if s:
            stats_lista.append(s)
        else:
            sin_datos.append(est.get_full_name())

    # Promedios del grupo
    todos_prom = [s['promedio'] for s in stats_lista]
    prom_curso = round(sum(todos_prom)/len(todos_prom), 2) if todos_prom else 0
    n_alertas  = sum(1 for s in stats_lista if s['alertas_activas'] > 0)
    n_baja     = sum(1 for s in stats_lista if s['tendencia'] < -0.3)

    context = {
        'curso': curso,
        'stats_lista': sorted(stats_lista, key=lambda x: x['promedio']),
        'dias_opciones': [7, 14, 30, 60, 90],
        'sin_datos': sin_datos,
        'prom_curso': prom_curso,
        'n_alertas': n_alertas,
        'n_baja': n_baja,
        'dias': dias,
        'api_ok': bool(ANTHROPIC_API_KEY),
    }
    return render(request, 'emotions/informe_preview.html', context)


@login_required
def informe_descargar(request, curso_id):
    """Genera y descarga el PDF del informe con analisis IA."""
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    curso = get_object_or_404(Curso, pk=curso_id, activo=True)
    if not request.user.es_admin and curso.profesor != request.user:
        return HttpResponseForbidden()

    dias = int(request.GET.get('dias', 30))
    dias = min(max(dias, 7), 90)

    # Calcular stats en BULK (2 queries sin importar cuántos estudiantes)
    inscritos = Inscripcion.objects.filter(curso=curso, activa=True).select_related('estudiante')
    estudiantes = [insc.estudiante for insc in inscritos]
    bulk = _stats_bulk_curso(estudiantes, dias)
    stats_lista = [s for s in bulk.values() if s is not None]

    if not stats_lista:
        return HttpResponse("No hay datos suficientes para generar el informe.", status=400)

    # Analisis IA
    texto_datos = _construir_texto_para_ia(curso, stats_lista, dias)
    analisis_ia, error_ia = _llamar_anthropic_informe(texto_datos)

    # Generar PDF
    pdf_buffer, error_pdf = _generar_pdf(curso, stats_lista, analisis_ia, dias)

    if error_pdf:
        return HttpResponse(f"Error generando PDF: {error_pdf}", status=500)

    nombre_archivo = (
        f"informe_{curso.nombre.replace(' ','_')}_{date.today().strftime('%Y%m%d')}.pdf"
    )
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response
