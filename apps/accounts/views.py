# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .forms import LoginForm, RegistroEstudianteForm, EditarPerfilForm
from .models import User, VinculoPadreHijo


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:inicio')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido/a, {user.first_name or user.username}.')
            return redirect(request.GET.get('next', 'dashboard:inicio'))
        else:
            messages.error(request, 'Usuario o contrasena incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesion correctamente.')
    return redirect('landing:inicio')


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:inicio')
    if request.method == 'POST':
        form = RegistroEstudianteForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada! Bienvenido/a, {user.first_name}!')
            return redirect('dashboard:inicio')
    else:
        form = RegistroEstudianteForm()
    return render(request, 'accounts/registro.html', {'form': form})


@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            # Si no se subió foto nueva, conservar la foto existente
            if not request.FILES.get('foto'):
                user.foto = request.user.__class__.objects.get(pk=request.user.pk).foto
            nueva_password = request.POST.get('password', '').strip()
            if nueva_password:
                user.set_password(nueva_password)
            user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('accounts:perfil')
    else:
        form = EditarPerfilForm(instance=request.user)
    return render(request, 'accounts/perfil.html', {'form': form})


@login_required
def ver_perfil_estudiante(request, pk):
    if not (request.user.es_profesor or request.user.es_admin):
        return HttpResponseForbidden()

    estudiante = get_object_or_404(User, pk=pk, rol=User.ROL_ESTUDIANTE)
    from apps.emotions.models import RegistroEmocional, Alerta, NotaProfesor
    from apps.courses.models import Inscripcion

    registros_qs = RegistroEmocional.objects.filter(estudiante=estudiante).order_by('-fecha')
    alertas = Alerta.objects.filter(estudiante=estudiante, resuelta=False)
    cursos = Inscripcion.objects.filter(estudiante=estudiante).select_related('curso')
    notas = NotaProfesor.objects.filter(estudiante=estudiante).select_related('profesor')

    # Guardar / editar nota
    if request.method == 'POST':
        if 'eliminar_nota' in request.POST:
            nota_id = request.POST.get('eliminar_nota')
            nota_obj = get_object_or_404(NotaProfesor, pk=nota_id, profesor=request.user)
            nota_obj.delete()
            messages.success(request, 'Nota eliminada.')
            return redirect('accounts:perfil_estudiante', pk=pk)

        if 'nota_contenido' in request.POST:
            contenido = request.POST.get('nota_contenido', '').strip()
            nota_id = request.POST.get('nota_id', '').strip()
            if contenido:
                if nota_id:
                    nota_obj = get_object_or_404(NotaProfesor, pk=nota_id, profesor=request.user)
                    nota_obj.contenido = contenido
                    nota_obj.save()
                    messages.success(request, 'Nota actualizada.')
                else:
                    NotaProfesor.objects.create(profesor=request.user, estudiante=estudiante, contenido=contenido)
                    messages.success(request, 'Nota guardada.')
            return redirect('accounts:perfil_estudiante', pk=pk)

    import json
    from datetime import date, timedelta
    hoy = date.today()
    fechas, puntajes = [], []
    for i in range(29, -1, -1):
        dia = hoy - timedelta(days=i)
        reg = registros_qs.filter(fecha=dia).first()
        fechas.append(dia.strftime('%d/%m'))
        puntajes.append(reg.puntaje if reg else None)

    total_registros = registros_qs.count()
    sample = list(registros_qs[:60])
    promedio_general = round(sum(r.puntaje for r in sample) / len(sample), 1) if sample else None

    racha = 0
    dia = hoy
    while registros_qs.filter(fecha=dia).exists():
        racha += 1
        dia -= timedelta(days=1)
        if racha > 60:
            break

    context = {
        'estudiante': estudiante,
        'registros': registros_qs[:30],
        'alertas': alertas,
        'cursos': cursos,
        'notas': notas,
        'fechas_json': json.dumps(fechas),
        'puntajes_json': json.dumps(puntajes),
        'total_registros': total_registros,
        'promedio_general': promedio_general,
        'racha': racha,
    }
    return render(request, 'accounts/perfil_estudiante.html', context)


# ─── PANEL PADRE ──────────────────────────────────────────────────────────────

@login_required
def panel_padre(request):
    """Dashboard del padre: ve el estado emocional de sus hijos vinculados."""
    if not request.user.es_padre:
        return HttpResponseForbidden()

    vinculos = VinculoPadreHijo.objects.filter(
        padre=request.user, activo=True
    ).select_related('estudiante')

    from apps.emotions.models import RegistroEmocional, Alerta
    from datetime import date, timedelta
    hoy = date.today()

    hijos_data = []
    for v in vinculos:
        est = v.estudiante
        reg_hoy  = RegistroEmocional.objects.filter(estudiante=est, fecha=hoy).first()
        regs_7d  = list(RegistroEmocional.objects.filter(
            estudiante=est, fecha__gte=hoy - timedelta(days=6)
        ).order_by('fecha'))
        alertas  = Alerta.objects.filter(estudiante=est, resuelta=False).count()
        prom_7d  = None
        if regs_7d:
            prom_7d = round(sum(r.puntaje for r in regs_7d) / len(regs_7d), 1)
        hijos_data.append({
            'vinculo':  v,
            'estudiante': est,
            'reg_hoy':  reg_hoy,
            'regs_7d':  regs_7d,
            'alertas':  alertas,
            'prom_7d':  prom_7d,
        })

    # Citaciones próximas de los hijos
    from apps.emotions.models import Citacion, MensajeDirecto
    ids_hijos = [v.estudiante.pk for v in vinculos]
    citaciones_proximas = Citacion.objects.filter(
        estudiante_id__in=ids_hijos,
        estado__in=['pendiente', 'confirmada'],
    ).select_related('estudiante', 'profesor').order_by('fecha', 'hora')[:5]

    # Mensajes no leídos de profesores
    mensajes_no_leidos = MensajeDirecto.objects.filter(
        destinatario=request.user, leido=False, remitente__rol=User.ROL_PROFESOR
    ).count()

    context = {
        'hijos_data': hijos_data,
        'hoy': hoy,
        'tiene_hijos': len(hijos_data) > 0,
        'citaciones_proximas': citaciones_proximas,
        'mensajes_no_leidos': mensajes_no_leidos,
    }
    return render(request, 'accounts/panel_padre.html', context)


@login_required
def hijo_detalle(request, pk):
    """El padre ve el historial detallado de un hijo vinculado."""
    if not request.user.es_padre:
        return HttpResponseForbidden()

    vinculo = get_object_or_404(
        VinculoPadreHijo, padre=request.user, estudiante__pk=pk, activo=True
    )
    estudiante = vinculo.estudiante

    from apps.emotions.models import RegistroEmocional, EntradaDiario, Logro
    from apps.courses.models import Inscripcion
    from datetime import date, timedelta
    import json

    hoy = date.today()
    registros = RegistroEmocional.objects.filter(estudiante=estudiante).order_by('-fecha')[:60]
    cursos    = Inscripcion.objects.filter(estudiante=estudiante, activa=True).select_related('curso')
    logros    = Logro.objects.filter(estudiante=estudiante).select_related()

    # Gráfica 30 días
    fechas, puntajes = [], []
    for i in range(29, -1, -1):
        dia = hoy - timedelta(days=i)
        reg = RegistroEmocional.objects.filter(estudiante=estudiante, fecha=dia).first()
        fechas.append(dia.strftime('%d/%m'))
        puntajes.append(reg.puntaje if reg else None)

    total    = RegistroEmocional.objects.filter(estudiante=estudiante).count()
    sample   = list(RegistroEmocional.objects.filter(estudiante=estudiante)[:60])
    promedio = round(sum(r.puntaje for r in sample) / len(sample), 1) if sample else None

    racha = 0
    dia   = hoy
    while RegistroEmocional.objects.filter(estudiante=estudiante, fecha=dia).exists():
        racha += 1
        dia   -= timedelta(days=1)
        if racha > 60:
            break

    context = {
        'vinculo':    vinculo,
        'estudiante': estudiante,
        'registros':  registros[:30],
        'cursos':     cursos,
        'logros':     logros,
        'hoy':        hoy,
        'fechas_json':   json.dumps(fechas),
        'puntajes_json': json.dumps(puntajes),
        'total_registros': total,
        'promedio_general': promedio,
        'racha':      racha,
    }
    return render(request, 'accounts/hijo_detalle.html', context)


@login_required
def vincular_hijo(request):
    """
    Profesores: ven todos los vínculos y pueden crear/desactivar cualquiera.
    Padres: solo ven y gestionan sus propios vínculos.
    Estudiantes: acceso denegado.
    """
    if request.user.es_estudiante:
        return HttpResponseForbidden()

    es_profesor = request.user.es_profesor

    estudiantes = User.objects.filter(rol=User.ROL_ESTUDIANTE, is_active=True).order_by('first_name', 'last_name')
    padres      = User.objects.filter(rol=User.ROL_PADRE,      is_active=True).order_by('first_name', 'last_name')

    # Profesores ven todos los vínculos; padres solo los suyos
    if es_profesor:
        vinculos = VinculoPadreHijo.objects.select_related('padre', 'estudiante').order_by('-created_at')
    else:
        vinculos = VinculoPadreHijo.objects.filter(padre=request.user).select_related('padre', 'estudiante').order_by('-created_at')

    if request.method == 'POST':
        accion = request.POST.get('accion', 'crear')

        if accion == 'crear':
            if es_profesor:
                # El profesor elige el padre manualmente
                padre_pk = request.POST.get('padre')
                padre    = get_object_or_404(User, pk=padre_pk, rol=User.ROL_PADRE)
            else:
                # El padre se vincula a sí mismo
                padre = request.user

            est_pk     = request.POST.get('estudiante')
            relacion   = request.POST.get('relacion', 'padre')
            estudiante = get_object_or_404(User, pk=est_pk, rol=User.ROL_ESTUDIANTE)

            vinculo, created = VinculoPadreHijo.objects.get_or_create(
                padre=padre, estudiante=estudiante,
                defaults={'relacion': relacion, 'activo': True}
            )
            if not created:
                vinculo.activo   = True
                vinculo.relacion = relacion
                vinculo.save()
                messages.info(request, 'El vínculo ya existía — fue reactivado.')
            else:
                messages.success(request, f'{padre.get_full_name()} vinculado/a con {estudiante.get_full_name()}.')

        elif accion == 'desactivar':
            vinculo_pk = request.POST.get('vinculo_pk')
            if es_profesor:
                v = get_object_or_404(VinculoPadreHijo, pk=vinculo_pk)
            else:
                # El padre solo puede desactivar sus propios vínculos
                v = get_object_or_404(VinculoPadreHijo, pk=vinculo_pk, padre=request.user)
            v.activo = False
            v.save()
            messages.success(request, 'Vínculo desactivado.')

        return redirect('accounts:vincular_hijo')

    context = {
        'estudiantes': estudiantes,
        'padres':      padres,
        'vinculos':    vinculos,
        'relaciones':  VinculoPadreHijo._meta.get_field('relacion').choices,
        'es_profesor': es_profesor,
    }
    return render(request, 'accounts/vincular_hijo.html', context)


# ─── NUEVAS FUNCIONES PARA PADRES ─────────────────────────────────────────────

@login_required
def padre_citaciones(request):
    """El padre ve las citaciones de todos sus hijos."""
    if not request.user.es_padre:
        return HttpResponseForbidden()

    from apps.emotions.models import Citacion
    vinculos = VinculoPadreHijo.objects.filter(
        padre=request.user, activo=True
    ).values_list('estudiante_id', flat=True)

    citaciones = Citacion.objects.filter(
        estudiante_id__in=vinculos
    ).select_related('estudiante', 'profesor').order_by('fecha', 'hora')

    pendientes = citaciones.filter(estado__in=['pendiente', 'confirmada']).count()
    urgentes   = citaciones.filter(es_urgente=True).count()

    context = {
        'citaciones': citaciones,
        'pendientes': pendientes,
        'urgentes':   urgentes,
    }
    return render(request, 'accounts/padre_citaciones.html', context)


@login_required
def padre_mensajes(request):
    """El padre puede enviar mensajes al profesor de su hijo y ver respuestas."""
    if not request.user.es_padre:
        return HttpResponseForbidden()

    from apps.emotions.models import MensajeDirecto
    from apps.courses.models import Inscripcion

    # Obtener hijos vinculados
    vinculos = VinculoPadreHijo.objects.filter(padre=request.user, activo=True).select_related('estudiante')
    hijos_ids = [v.estudiante_id for v in vinculos]

    # Profesores de los hijos (via inscripcion → curso → profesor)
    profesores_ids = Inscripcion.objects.filter(
        estudiante_id__in=hijos_ids, activa=True
    ).values_list('curso__profesor_id', flat=True).distinct()
    profesores = User.objects.filter(id__in=profesores_ids, rol=User.ROL_PROFESOR)

    # Mensajes recibidos de profesores
    recibidos_qs = MensajeDirecto.objects.filter(
        destinatario=request.user, remitente__rol=User.ROL_PROFESOR
    ).select_related('remitente').order_by('-created_at')

    enviados = MensajeDirecto.objects.filter(
        remitente=request.user
    ).select_related('destinatario').order_by('-created_at')

    if request.method == 'POST':
        prof_id   = request.POST.get('profesor')
        contenido = request.POST.get('contenido', '').strip()
        hijo_id   = request.POST.get('hijo')
        if prof_id and contenido:
            try:
                profesor = User.objects.get(pk=prof_id, rol=User.ROL_PROFESOR)
                hijo_nombre = ''
                if hijo_id:
                    try:
                        hijo = User.objects.get(pk=hijo_id)
                        hijo_nombre = f'[Sobre: {hijo.get_full_name()}] '
                    except User.DoesNotExist:
                        pass
                MensajeDirecto.objects.create(
                    remitente=request.user,
                    destinatario=profesor,
                    contenido=f'{hijo_nombre}{contenido}',
                )
                messages.success(request, f'Mensaje enviado al Prof. {profesor.get_full_name()}.')
            except User.DoesNotExist:
                messages.error(request, 'Profesor no encontrado.')
        return redirect('accounts:padre_mensajes')

    # Contar no leídos ANTES de marcarlos
    no_leidos = recibidos_qs.filter(leido=False).count()
    recibidos_qs.filter(leido=False).update(leido=True)
    recibidos = list(recibidos_qs)

    context = {
        'profesores': profesores,
        'vinculos': vinculos,
        'recibidos': recibidos,
        'enviados': enviados,
        'no_leidos': no_leidos,
    }
    return render(request, 'accounts/padre_mensajes.html', context)
