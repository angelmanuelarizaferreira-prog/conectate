# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import SesionChat, MensajeChat, RegistroEmocional, EMOCION_EMOJIS
from django.conf import settings


def _get_api_key():
    key = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''
    return key.strip()


# Prompt del sistema — define el caracter y limites de la IA
SYSTEM_PROMPT = """Eres Luna, una asistente de apoyo emocional amigable y empatica que acompana a estudiantes de colegio. Tu rol es escuchar, validar emociones y ayudar a los estudiantes a reflexionar sobre como se sienten.

COMO ERES:
- Carinosa, cercana y paciente, como una amiga mayor de confianza
- Usas un lenguaje sencillo y apropiado para jovenes
- Haces preguntas abiertas para que el estudiante pueda expresarse
- Validas los sentimientos sin juzgar
- Eres positiva pero honesta — no minimizas los problemas reales

LO QUE HACES:
- Escuchas activamente y reflejas lo que el estudiante comparte
- Ayudas a identificar y nombrar emociones
- Sugieres estrategias de afrontamiento simples (respiracion, escribir, hablar con alguien)
- Celebras los logros y el esfuerzo del estudiante
- Recuerdas el contexto de la conversacion para dar respuestas coherentes

LO QUE NO HACES:
- No das diagnosticos medicos ni psicologicos
- No reemplazas la atencion de un profesional de salud mental
- No das consejos sobre drogas, alcohol ni comportamientos peligrosos
- Si el estudiante menciona autolesiones, ideas suicidas o situaciones de abuso, le recuerdas con calor que debe hablar con un adulto de confianza o un profesional, y que no esta solo/a
- No haces tareas academicas ni ayudas con examenes

TONO:
- Respuestas cortas y conversacionales (2-4 oraciones maximo por respuesta)
- Usa emojis ocasionalmente para calidez
- Siempre termina con una pregunta o invitacion a seguir hablando
- Habla en espanol colombiano natural

Recuerda: eres un apoyo emocional, no un terapeuta. Tu objetivo es que el estudiante se sienta escuchado y menos solo."""


def _build_messages(sesion):
    """Construye el historial de mensajes para la API de Anthropic."""
    mensajes = list(sesion.mensajes.order_by('created_at'))
    # Limitar a los ultimos 20 mensajes para no sobrecargar el contexto
    mensajes = mensajes[-20:]
    return [{'role': m.rol, 'content': m.contenido} for m in mensajes]


def _llamar_anthropic(messages_list, sistema=SYSTEM_PROMPT):
    """Llama a la API de Anthropic y retorna el texto de respuesta."""
    ANTHROPIC_API_KEY = _get_api_key()
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'TU_API_KEY_AQUI':
        return None, "API key no configurada. Configura ANTHROPIC_API_KEY en settings.py o como variable de entorno."

    payload = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 400,
        'system': sistema,
        'messages': messages_list,
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            texto = data['content'][0]['text']
            return texto, None
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return None, f"Error HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return None, str(e)


@login_required
def chat_lista(request):
    """Lista de sesiones de chat del estudiante."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    sesiones = SesionChat.objects.filter(estudiante=request.user, activa=True)

    # Crear nueva sesion desde aqui
    if request.method == 'POST':
        sesion = SesionChat.objects.create(estudiante=request.user)
        return redirect('emotions:chat_sesion', pk=sesion.pk)

    context = {'sesiones': sesiones}
    return render(request, 'emotions/chat_lista.html', context)


@login_required
def chat_sesion(request, pk):
    """Vista principal del chat con la IA."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    sesion = get_object_or_404(SesionChat, pk=pk, estudiante=request.user, activa=True)
    mensajes = sesion.mensajes.order_by('created_at')

    # Si es sesion nueva, enviar mensaje de bienvenida
    if not mensajes.exists():
        # Personalizar saludo con registro emocional reciente
        reg_hoy = RegistroEmocional.objects.filter(
            estudiante=request.user, fecha=date.today()
        ).first()

        if reg_hoy:
            emoji = EMOCION_EMOJIS.get(reg_hoy.emocion, '')
            saludo = (
                f"Hola {request.user.first_name or 'amigo/a'}!  Vi que hoy te sientes "
                f"{emoji} {reg_hoy.get_emocion_display().lower()}. "
                f"Estoy aqui para escucharte. "
                f"Cuentame, &iquest;como ha sido tu dia?"
            )
        else:
            saludo = (
                f"Hola {request.user.first_name or 'amigo/a'}!  Soy Luna, tu asistente "
                f"de apoyo emocional. Este es tu espacio seguro para hablar de como te sientes. "
                f"&iquest;Que tienes en mente hoy?"
            )

        MensajeChat.objects.create(
            sesion=sesion, rol='assistant', contenido=saludo
        )
        mensajes = sesion.mensajes.order_by('created_at')

        # Auto-titulo si no tiene
        if not sesion.titulo:
            sesion.titulo = f"Conversacion del {date.today():%d/%m/%Y}"
            sesion.save()

    api_ok = bool(_get_api_key()) and _get_api_key() != 'TU_API_KEY_AQUI'

    context = {
        'sesion': sesion,
        'mensajes': mensajes,
        'api_ok': api_ok,
    }
    return render(request, 'emotions/chat_sesion.html', context)


@login_required
@require_POST
def chat_enviar(request, pk):
    """Endpoint AJAX: recibe mensaje del estudiante, guarda y llama a la IA."""
    if not request.user.es_estudiante:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    sesion = get_object_or_404(SesionChat, pk=pk, estudiante=request.user, activa=True)

    try:
        data = json.loads(request.body)
        texto = data.get('mensaje', '').strip()
    except Exception:
        return JsonResponse({'error': 'Datos invalidos'}, status=400)

    if not texto:
        return JsonResponse({'error': 'Mensaje vacio'}, status=400)

    if len(texto) > 1000:
        return JsonResponse({'error': 'Mensaje muy largo (max 1000 caracteres)'}, status=400)

    # Guardar mensaje del estudiante
    MensajeChat.objects.create(sesion=sesion, rol='user', contenido=texto)

    # Construir historial y llamar a la IA
    messages_list = _build_messages(sesion)
    respuesta, error = _llamar_anthropic(messages_list)

    if error:
        return JsonResponse({'error': error}, status=500)

    # Guardar respuesta de la IA
    MensajeChat.objects.create(sesion=sesion, rol='assistant', contenido=respuesta)

    # Actualizar titulo de la sesion si es el primer mensaje del usuario
    conteo = sesion.mensajes.filter(rol='user').count()
    if conteo == 1 and not sesion.titulo:
        sesion.titulo = texto[:60] + ('...' if len(texto) > 60 else '')
        sesion.save()

    return JsonResponse({
        'respuesta': respuesta,
        'ok': True,
    })


@login_required
@require_POST
def chat_nueva_sesion(request):
    """Crea una nueva sesion de chat y redirige a ella."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    sesion = SesionChat.objects.create(estudiante=request.user)
    return redirect('emotions:chat_sesion', pk=sesion.pk)


@login_required
@require_POST
def chat_eliminar(request, pk):
    """Elimina (desactiva) una sesion de chat."""
    if not request.user.es_estudiante:
        return HttpResponseForbidden()

    sesion = get_object_or_404(SesionChat, pk=pk, estudiante=request.user)
    sesion.activa = False
    sesion.save()
    messages.success(request, 'Conversacion eliminada.')
    return redirect('emotions:chat_lista')


# ─── WIDGET FLOTANTE ─────────────────────────────────────────────────────────

@login_required
def chat_widget_session(request):
    """Obtiene o crea la sesion activa para el widget flotante.
    Devuelve: pk de sesion + ultimos 30 mensajes como JSON."""
    if not request.user.es_estudiante:
        return JsonResponse({'error': 'Solo estudiantes'}, status=403)

    # Obtener la sesion mas reciente activa, o crear una nueva
    sesion = SesionChat.objects.filter(
        estudiante=request.user, activa=True
    ).order_by('-updated_at').first()

    if not sesion:
        sesion = SesionChat.objects.create(
            estudiante=request.user,
            titulo=f"Chat del {date.today():%d/%m/%Y}"
        )
        # Mensaje de bienvenida
        reg_hoy = RegistroEmocional.objects.filter(
            estudiante=request.user, fecha=date.today()
        ).first()
        if reg_hoy:
            emoji = EMOCION_EMOJIS.get(reg_hoy.emocion, '')
            saludo = (
                f"Hola {request.user.first_name or 'amigo/a'}!  Vi que hoy te sientes "
                f"{emoji} {reg_hoy.get_emocion_display().lower()}. "
                f"Estoy aqui para escucharte. ¿Como ha sido tu dia?"
            )
        else:
            saludo = (
                f"Hola {request.user.first_name or 'amigo/a'}!  Soy Luna, tu asistente "
                f"de apoyo emocional. ¿Que tienes en mente hoy?"
            )
        MensajeChat.objects.create(sesion=sesion, rol='assistant', contenido=saludo)

    mensajes = list(sesion.mensajes.order_by('-created_at')[:30])[::-1]
    return JsonResponse({
        'session_pk': sesion.pk,
        'mensajes': [
            {
                'rol': m.rol,
                'contenido': m.contenido,
                'hora': m.created_at.strftime('%H:%M'),
            }
            for m in mensajes
        ]
    })
