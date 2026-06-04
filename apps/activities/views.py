# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden

from .models import Actividad, RespuestaActividad, TIPO_ACTIVIDAD
from apps.courses.models import Curso, Inscripcion


@login_required
def lista_actividades(request):
    if request.user.es_estudiante:
        ids_cursos = Inscripcion.objects.filter(
            estudiante=request.user, activa=True
        ).values_list('curso_id', flat=True)
        actividades = Actividad.objects.filter(curso_id__in=ids_cursos, activa=True).order_by('semana', 'created_at')

        ids_respondidas = RespuestaActividad.objects.filter(
            estudiante=request.user
        ).values_list('actividad_id', flat=True)

        context = {
            'actividades': actividades,
            'ids_respondidas': list(ids_respondidas),
        }
    else:
        # Todos los profesores ven todas las actividades
        actividades = Actividad.objects.all().order_by('-created_at')
        context = {'actividades': actividades}

    return render(request, 'activities/lista.html', context)


@login_required
def crear_actividad(request):
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    if request.method == 'POST':
        titulo       = request.POST.get('titulo', '').strip()
        tipo         = request.POST.get('tipo')
        descripcion  = request.POST.get('descripcion', '').strip()
        curso_id     = request.POST.get('curso')
        fecha_limite = request.POST.get('fecha_limite') or None
        semana       = int(request.POST.get('semana', 1) or 1)

        tipos_validos = [t[0] for t in TIPO_ACTIVIDAD]

        if not titulo or tipo not in tipos_validos or not descripcion:
            messages.error(request, 'Todos los campos obligatorios deben completarse.')
        else:
            curso = None
            if curso_id:
                try:
                    curso = Curso.objects.get(pk=curso_id)
                except Curso.DoesNotExist:
                    pass

            Actividad.objects.create(
                titulo=titulo,
                tipo=tipo,
                descripcion=descripcion,
                curso=curso,
                creada_por=request.user,
                fecha_limite=fecha_limite,
                semana=semana,
            )
            messages.success(request, f'Actividad "{titulo}" creada en la Semana {semana}.')
            if curso:
                return redirect('courses:detalle', pk=curso.pk)
            return redirect('activities:lista')

    cursos = Curso.objects.filter(activo=True)
    context = {'tipos': TIPO_ACTIVIDAD, 'cursos': cursos, 'semana_range': range(1, 17)}
    return render(request, 'activities/crear.html', context)


@login_required
def detalle_actividad(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    
    if request.user.es_estudiante:
        # Verificar que el estudiante pertenece al curso
        if actividad.curso and not Inscripcion.objects.filter(
            estudiante=request.user, curso=actividad.curso, activa=True
        ).exists():
            return HttpResponseForbidden()
        
        respuesta_existente = RespuestaActividad.objects.filter(
            actividad=actividad, estudiante=request.user
        ).first()
        
        if request.method == 'POST' and not respuesta_existente:
            texto = request.POST.get('respuesta', '').strip()
            if texto:
                RespuestaActividad.objects.create(
                    actividad=actividad,
                    estudiante=request.user,
                    respuesta=texto,
                )
                messages.success(request, '¡Respuesta enviada! Gracias por participar.')
                return redirect('activities:lista')
            else:
                messages.error(request, 'La respuesta no puede estar vacia.')
        
        context = {'actividad': actividad, 'respuesta_existente': respuesta_existente}
    else:
        respuestas = actividad.respuestas.select_related('estudiante').order_by('-created_at')
        context = {'actividad': actividad, 'respuestas': respuestas}
    
    return render(request, 'activities/detalle.html', context)
