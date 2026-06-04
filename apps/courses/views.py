# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Curso, Inscripcion, GRADO_CHOICES, SECCION_CHOICES
from apps.accounts.models import User


@login_required
def lista_cursos(request):
    # Profesores (y admins) ven TODOS los cursos
    if request.user.es_admin or request.user.es_profesor:
        cursos = Curso.objects.all().order_by('grado', 'seccion')
        return render(request, 'courses/lista.html', {'cursos': cursos})

    # Estudiante: redirigir directo al curso más reciente (activo)
    insc = Inscripcion.objects.filter(
        estudiante=request.user, activa=True
    ).order_by('-fecha_inscripcion').first()

    if insc:
        return redirect('courses:detalle', pk=insc.curso.pk)

    # Sin cursos inscritos: mostrar pantalla vacía con botón de unirse
    return render(request, 'courses/lista.html', {'cursos': []})


@login_required
def crear_curso(request):
    if not (request.user.es_admin or request.user.es_profesor):
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        grado       = request.POST.get('grado', '').strip()
        seccion     = request.POST.get('seccion', 'A').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        profesor_id = request.POST.get('profesor')

        errores = []
        if not grado:
            errores.append('Selecciona un grado.')
        if Curso.objects.filter(grado=grado, seccion=seccion).exists():
            errores.append(f'Ya existe el Grado {grado}{seccion}.')

        if not errores:
            curso = Curso(grado=grado, seccion=seccion, descripcion=descripcion)
            if request.user.es_admin and profesor_id:
                try:
                    curso.profesor = User.objects.get(pk=profesor_id, rol=User.ROL_PROFESOR)
                except User.DoesNotExist:
                    pass
            elif request.user.es_profesor:
                curso.profesor = request.user
            curso.save()
            messages.success(request, f'Grupo "{curso.nombre}" creado. Código: {curso.codigo}')
            return redirect('courses:detalle', pk=curso.pk)
        else:
            for e in errores:
                messages.error(request, e)

    profesores = User.objects.filter(rol=User.ROL_PROFESOR, activo=True)
    return render(request, 'courses/crear.html', {
        'profesores': profesores,
        'grado_choices': GRADO_CHOICES,
        'seccion_choices': SECCION_CHOICES,
    })


@login_required
def detalle_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)

    # Verificar acceso
    if not (request.user.es_profesor or
            Inscripcion.objects.filter(estudiante=request.user, curso=curso, activa=True).exists()):
        return HttpResponseForbidden()

    from datetime import date
    from apps.emotions.models import RegistroEmocional, Alerta
    from apps.activities.models import Actividad, RespuestaActividad
    import json

    hoy = date.today()
    inscripciones = Inscripcion.objects.filter(curso=curso, activa=True).select_related('estudiante')

    # ── VISTA ESTUDIANTE (Moodle) ────────────────────────────────────────────
    if request.user.es_estudiante:
        actividades = Actividad.objects.filter(
            curso=curso, activa=True
        ).order_by('semana', 'created_at')

        # Actividades respondidas por este estudiante
        ids_respondidas = set(
            RespuestaActividad.objects.filter(
                estudiante=request.user, actividad__in=actividades
            ).values_list('actividad_id', flat=True)
        )

        # Agrupar actividades por semana
        semanas = {}
        for act in actividades:
            s = act.semana
            if s not in semanas:
                semanas[s] = []
            semanas[s].append(act)

        # Semanas ordenadas
        semanas_list = [
            {
                'numero': num,
                'actividades': acts,
                'total': len(acts),
                'respondidas': sum(1 for a in acts if a.id in ids_respondidas),
            }
            for num, acts in sorted(semanas.items())
        ]

        # Solo el promedio del propio estudiante (NO de compañeros)
        mis_registros = RegistroEmocional.objects.filter(
            estudiante=request.user
        ).order_by('-fecha')[:7]

        context = {
            'curso': curso,
            'semanas_list': semanas_list,
            'ids_respondidas': ids_respondidas,
            'mis_registros': mis_registros,
            'total_companeros': inscripciones.count() - 1,  # sin contarse a sí mismo
        }
        return render(request, 'courses/detalle_estudiante.html', context)

    # ── VISTA PROFESOR ────────────────────────────────────────────────────────
    estudiantes_data = []
    for insc in inscripciones:
        est = insc.estudiante
        registro_hoy = RegistroEmocional.objects.filter(estudiante=est, fecha=hoy).first()
        alertas_activas = Alerta.objects.filter(estudiante=est, resuelta=False).count()
        estudiantes_data.append({
            'estudiante': est,
            'registro_hoy': registro_hoy,
            'alertas': alertas_activas,
        })

    EMOCIONES = ['feliz', 'tranquilo', 'estresado', 'triste', 'enojado']
    ids_estudiantes = [i.estudiante_id for i in inscripciones]
    registros_hoy = RegistroEmocional.objects.filter(estudiante_id__in=ids_estudiantes, fecha=hoy)
    conteo_emociones = {e: registros_hoy.filter(emocion=e).count() for e in EMOCIONES}

    # Actividades agrupadas por semana para el profesor
    actividades = Actividad.objects.filter(curso=curso, activa=True).order_by('semana', 'created_at')
    semanas_prof = {}
    for act in actividades:
        s = act.semana
        if s not in semanas_prof:
            semanas_prof[s] = []
        semanas_prof[s].append(act)
    semanas_list_prof = [
        {'numero': num, 'actividades': acts}
        for num, acts in sorted(semanas_prof.items())
    ]

    context = {
        'curso': curso,
        'estudiantes_data': estudiantes_data,
        'conteo_emociones': json.dumps(conteo_emociones),
        'promedio_hoy': curso.get_promedio_emocional_hoy(),
        'actividades': actividades,
        'semanas_list': semanas_list_prof,
        'max_semana': max(semanas_prof.keys()) if semanas_prof else 1,
    }
    return render(request, 'courses/detalle.html', context)


@login_required
def inscribir_estudiante(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    # Cualquier profesor puede inscribir estudiantes en cualquier curso
    if not request.user.es_profesor:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        codigo_o_usuario = request.POST.get('buscar', '').strip()
        try:
            estudiante = User.objects.get(
                username=codigo_o_usuario, rol=User.ROL_ESTUDIANTE
            )
            # Un estudiante solo puede pertenecer a un grupo a la vez
            insc_anterior = Inscripcion.objects.filter(estudiante=estudiante, activa=True).exclude(curso=curso).first()
            if insc_anterior:
                insc_anterior.activa = False
                insc_anterior.save()
                messages.info(request, f'{estudiante.get_full_name()} fue removido/a de "{insc_anterior.curso.nombre}" para inscribirse aquí.')

            insc, created = Inscripcion.objects.get_or_create(
                estudiante=estudiante, curso=curso,
                defaults={'activa': True},
            )
            if not insc.activa:
                insc.activa = True
                insc.save(update_fields=['activa'])
                created = True
            if created:
                messages.success(request, f'{estudiante.get_full_name()} inscrito/a correctamente.')
            else:
                messages.info(request, f'{estudiante.get_full_name()} ya estaba inscrito/a.')
        except User.DoesNotExist:
            messages.error(request, f'No se encontro un estudiante con usuario "{codigo_o_usuario}".')
    
    return redirect('courses:detalle', pk=pk)


@login_required
def unirse_con_codigo(request):
    if not request.user.es_estudiante:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()
        try:
            curso = Curso.objects.get(codigo=codigo, activo=True)
            # Verificar si ya tiene una inscripción activa en otro curso
            insc_actual = Inscripcion.objects.filter(estudiante=request.user, activa=True).first()
            if insc_actual and insc_actual.curso.pk != curso.pk:
                messages.error(request, f'Ya estás inscrito/a en "{insc_actual.curso.nombre}". Un estudiante solo puede pertenecer a un grupo a la vez.')
                return redirect("courses:lista")
            insc, created = Inscripcion.objects.get_or_create(estudiante=request.user, curso=curso)
            if not insc.activa:
                insc.activa = True
                insc.save(update_fields=['activa'])
                created = True
            if created:
                messages.success(request, f'¡Te uniste a "{curso.nombre}" exitosamente!')
            else:
                messages.info(request, f'Ya estas inscrito/a en "{curso.nombre}".')
        except Curso.DoesNotExist:
            messages.error(request, f'Codigo "{codigo}" no valido o el curso no existe.')
    
    return redirect('courses:lista')
