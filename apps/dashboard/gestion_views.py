# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q

from apps.accounts.models import User
from apps.courses.models import Curso, Inscripcion, GRADO_CHOICES, SECCION_CHOICES
from apps.emotions.models import RegistroEmocional, Alerta
from apps.activities.models import Actividad


def es_gestor(user):
    """Admin o Profesor pueden gestionar"""
    return user.es_admin or user.es_profesor


# ─── GESTION DE USUARIOS ──────────────────────────────────────────────

@login_required
def gestionar_usuarios(request):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    q = request.GET.get('q', '')
    rol = request.GET.get('rol', '')

    usuarios = User.objects.all().order_by('rol', 'first_name')

    if not request.user.es_admin:
        # Profesor solo ve sus estudiantes
        ids = Inscripcion.objects.filter(
            curso__profesor=request.user, activa=True
        ).values_list('estudiante_id', flat=True)
        usuarios = User.objects.filter(
            Q(id__in=ids) | Q(id=request.user.id)
        ).order_by('first_name')

    if q:
        usuarios = usuarios.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(username__icontains=q) | Q(email__icontains=q)
        )
    if rol:
        usuarios = usuarios.filter(rol=rol)

    context = {
        'usuarios': usuarios,
        'q': q,
        'rol_filtro': rol,
        'roles': User.ROL_CHOICES,
    }
    return render(request, 'gestion/usuarios.html', context)


@login_required
def crear_usuario(request):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        rol = request.POST.get('rol', User.ROL_ESTUDIANTE)
        password = request.POST.get('password', '').strip()
        curso_id = request.POST.get('curso_id')

        # Todos los profesores pueden crear cualquier tipo de usuario

        errores = []
        if not first_name: errores.append('El nombre es obligatorio.')
        if not username: errores.append('El usuario es obligatorio.')
        if not password or len(password) < 6: errores.append('La contrasena debe tener al menos 6 caracteres.')
        if User.objects.filter(username=username).exists(): errores.append(f'El usuario "{username}" ya existe.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            nuevo = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name, rol=rol
            )
            # Si se especifico curso, inscribir automaticamente
            if curso_id and rol == User.ROL_ESTUDIANTE:
                try:
                    curso = Curso.objects.get(pk=curso_id)
                    Inscripcion.objects.get_or_create(estudiante=nuevo, curso=curso)
                except Curso.DoesNotExist:
                    pass

            messages.success(request, f'Usuario "{nuevo.get_full_name()}" creado exitosamente.')
            return redirect('gestion:usuarios')

    if request.user.es_admin:
        cursos = Curso.objects.filter(activo=True)
    else:
        cursos = Curso.objects.filter(profesor=request.user, activo=True)

    context = {
        'roles': User.ROL_CHOICES,
        'cursos': cursos,
        'es_admin': request.user.es_admin,
    }
    return render(request, 'gestion/crear_usuario.html', context)


@login_required
def editar_usuario(request, pk):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    usuario = get_object_or_404(User, pk=pk)

    # Profesor solo puede editar sus estudiantes
    if not request.user.es_admin:
        ids = Inscripcion.objects.filter(
            curso__profesor=request.user, activa=True
        ).values_list('estudiante_id', flat=True)
        if usuario.pk not in list(ids) and usuario.pk != request.user.pk:
            return HttpResponseForbidden()

    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name', '').strip()
        usuario.last_name = request.POST.get('last_name', '').strip()
        usuario.email = request.POST.get('email', '').strip()
        usuario.telefono = request.POST.get('telefono', '').strip()

        if request.user.es_admin:
            nuevo_rol = request.POST.get('rol', usuario.rol)
            usuario.rol = nuevo_rol

        nueva_pass = request.POST.get('password', '').strip()
        if nueva_pass:
            if len(nueva_pass) < 6:
                messages.error(request, 'La contrasena debe tener al menos 6 caracteres.')
                return redirect('gestion:editar_usuario', pk=pk)
            usuario.set_password(nueva_pass)

        usuario.activo = request.POST.get('activo') == 'on'
        usuario.save()
        messages.success(request, f'Usuario "{usuario.get_full_name()}" actualizado.')
        return redirect('gestion:usuarios')

    context = {
        'usuario': usuario,
        'roles': User.ROL_CHOICES,
        'es_admin': request.user.es_admin,
    }
    return render(request, 'gestion/editar_usuario.html', context)


@login_required
def eliminar_usuario(request, pk):
    if not request.user.es_admin:
        return HttpResponseForbidden()

    usuario = get_object_or_404(User, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('gestion:usuarios')

    if request.method == 'POST':
        nombre = usuario.get_full_name()
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado.')
    return redirect('gestion:usuarios')


# ─── GESTION DE CURSOS ────────────────────────────────────────────────

@login_required
def gestionar_cursos(request):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    if request.user.es_admin:
        cursos = Curso.objects.all().select_related('profesor').order_by('nombre')
    else:
        cursos = Curso.objects.filter(profesor=request.user).order_by('nombre')

    context = {'cursos': cursos}
    return render(request, 'gestion/cursos.html', context)


@login_required
def editar_curso(request, pk):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    curso = get_object_or_404(Curso, pk=pk)

    if not request.user.es_admin and curso.profesor != request.user:
        return HttpResponseForbidden()

    if request.method == 'POST':
        curso.grado   = request.POST.get('grado', curso.grado).strip()
        curso.seccion = request.POST.get('seccion', curso.seccion).strip()
        curso.descripcion = request.POST.get('descripcion', '').strip()
        curso.activo = request.POST.get('activo') == 'on'

        if request.user.es_admin:
            prof_id = request.POST.get('profesor')
            if prof_id:
                try:
                    curso.profesor = User.objects.get(pk=prof_id, rol=User.ROL_PROFESOR)
                except User.DoesNotExist:
                    pass

        curso.save()
        messages.success(request, f'Curso "{curso.nombre}" actualizado.')
        return redirect('gestion:cursos')

    profesores = User.objects.filter(rol=User.ROL_PROFESOR, activo=True)
    inscripciones = Inscripcion.objects.filter(curso=curso, activa=True).select_related('estudiante')
    # Estudiantes sin curso asignado (para poder agregarlos)
    ids_en_algun_curso = Inscripcion.objects.filter(activa=True).values_list('estudiante_id', flat=True)
    estudiantes_sin_curso = User.objects.filter(
        rol=User.ROL_ESTUDIANTE
    ).exclude(id__in=ids_en_algun_curso).order_by('last_name', 'first_name')

    context = {
        'curso': curso,
        'profesores': profesores,
        'inscripciones': inscripciones,
        'estudiantes_sin_curso': estudiantes_sin_curso,
        'es_admin': request.user.es_admin,
        'grado_choices': GRADO_CHOICES,
        'seccion_choices': SECCION_CHOICES,
    }
    return render(request, 'gestion/editar_curso.html', context)


@login_required
def agregar_inscripcion(request):
    """Inscribir un estudiante a un curso. Garantiza que solo esté en UN curso activo."""
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    if request.method != 'POST':
        return redirect('gestion:cursos')

    estudiante_id = request.POST.get('estudiante_id')
    curso_id      = request.POST.get('curso_id')

    try:
        estudiante = User.objects.get(pk=estudiante_id, rol=User.ROL_ESTUDIANTE)
        curso      = Curso.objects.get(pk=curso_id)
    except (User.DoesNotExist, Curso.DoesNotExist):
        messages.error(request, 'Estudiante o curso no encontrado.')
        return redirect('gestion:cursos')

    # Desactivar cualquier inscripción activa previa (un curso por estudiante)
    inscripciones_previas = Inscripcion.objects.filter(estudiante=estudiante, activa=True).exclude(curso=curso)
    if inscripciones_previas.exists():
        nombres_previos = ', '.join(str(i.curso) for i in inscripciones_previas)
        inscripciones_previas.update(activa=False)
        messages.warning(request, f'{estudiante.get_full_name()} fue removido de: {nombres_previos}.')

    insc, created = Inscripcion.objects.get_or_create(estudiante=estudiante, curso=curso)
    if not insc.activa:
        insc.activa = True
        insc.save()

    if created:
        messages.success(request, f'{estudiante.get_full_name()} inscrito en {curso}.')
    else:
        messages.info(request, f'{estudiante.get_full_name()} ya estaba inscrito en {curso}.')

    return redirect('gestion:editar_curso', pk=curso_id)


@login_required
def eliminar_inscripcion(request, pk):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    insc = get_object_or_404(Inscripcion, pk=pk)
    curso_pk = insc.curso.pk
    nombre = insc.estudiante.get_full_name()
    insc.activa = False
    insc.save()
    messages.success(request, f'{nombre} removido/a del curso.')
    return redirect('gestion:editar_curso', pk=curso_pk)


@login_required
def eliminar_curso(request, pk):
    if not request.user.es_admin:
        return HttpResponseForbidden()

    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        nombre = curso.nombre
        curso.activo = False
        curso.save()
        messages.success(request, f'Curso "{nombre}" desactivado.')
    return redirect('gestion:cursos')


# ─── GESTION DE ACTIVIDADES ───────────────────────────────────────────

@login_required
def gestionar_actividades(request):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    # Todos los profesores ven todas las actividades
    actividades = Actividad.objects.all().select_related('creada_por', 'curso').order_by('-created_at')

    context = {'actividades': actividades}
    return render(request, 'gestion/actividades.html', context)


@login_required
def editar_actividad(request, pk):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    actividad = get_object_or_404(Actividad, pk=pk)

    if not request.user.es_admin and actividad.creada_por != request.user:
        return HttpResponseForbidden()

    from apps.activities.models import TIPO_ACTIVIDAD

    if request.method == 'POST':
        actividad.titulo       = request.POST.get('titulo', '').strip()
        actividad.tipo         = request.POST.get('tipo', actividad.tipo)
        actividad.descripcion  = request.POST.get('descripcion', '').strip()
        actividad.activa       = request.POST.get('activa') == 'on'
        actividad.semana       = int(request.POST.get('semana', actividad.semana) or actividad.semana)
        fecha_limite           = request.POST.get('fecha_limite')
        actividad.fecha_limite = fecha_limite if fecha_limite else None

        curso_id = request.POST.get('curso')
        if curso_id:
            try:
                actividad.curso = Curso.objects.get(pk=curso_id)
            except Curso.DoesNotExist:
                actividad.curso = None
        else:
            actividad.curso = None

        actividad.save()
        messages.success(request, f'Actividad "{actividad.titulo}" actualizada.')
        if actividad.curso:
            return redirect('courses:detalle', pk=actividad.curso.pk)
        return redirect('gestion:actividades')

    cursos = Curso.objects.filter(activo=True)

    context = {
        'actividad': actividad,
        'tipos': TIPO_ACTIVIDAD,
        'cursos': cursos,
        'semana_range': range(1, 17),
    }
    return render(request, 'gestion/editar_actividad.html', context)


@login_required
def eliminar_actividad(request, pk):
    if not es_gestor(request.user):
        return HttpResponseForbidden()

    actividad = get_object_or_404(Actividad, pk=pk)
    if not request.user.es_admin and actividad.creada_por != request.user:
        return HttpResponseForbidden()

    if request.method == 'POST':
        nombre = actividad.titulo
        actividad.delete()
        messages.success(request, f'Actividad "{nombre}" eliminada.')
    return redirect('gestion:actividades')
