#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup_datos.py — Carga datos de demostración para Conéctate.

Crea:
  • 1 superusuario administrador
  • 3 profesores
  • 12 estudiantes (4 por grado, cada uno en UN solo grado)
  • 6 padres de familia vinculados a estudiantes
  • 3 cursos (un grado por curso)
  • Registros emocionales, diarios, actividades, notas, mensajes, logros

REGLA: Cada estudiante solo puede estar inscrito en UN grado.
"""

import os
import sys
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conectate.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from apps.accounts.models import User, VinculoPadreHijo
from apps.courses.models import Curso, Inscripcion
from apps.activities.models import Actividad, RespuestaActividad
from apps.emotions.models import (
    RegistroEmocional, EntradaDiario, Logro,
    NotaProfesor, MensajeDirecto,
)


def ok(msg):    print(f"  \u2705 {msg}")
def info(msg):  print(f"  \U0001f4cc {msg}")
def titulo(msg): print(f"\n{'='*55}\n  {msg}\n{'='*55}")


def inscribir_en_un_solo_curso(estudiante, curso):
    """
    Inscribe al estudiante en `curso` y desactiva cualquier otra
    inscripcion activa. Garantiza que solo exista UNA activa.
    """
    Inscripcion.objects.filter(
        estudiante=estudiante, activa=True
    ).exclude(curso=curso).update(activa=False)

    insc, created = Inscripcion.objects.get_or_create(
        estudiante=estudiante,
        curso=curso,
        defaults={'activa': True},
    )
    if not insc.activa:
        insc.activa = True
        insc.save(update_fields=['activa'])
    return insc, created


titulo("CONECTATE - Cargando datos de demostracion")

PASS_DEFAULT = "Conectate2024"

# 1. SUPERUSUARIO
titulo("1 . Superusuario administrador")
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin', email='admin@conectate.edu.co',
        password=PASS_DEFAULT, first_name='Super', last_name='Admin',
        rol=User.ROL_PROFESOR,
    )
    ok(f"admin creado  ->  usuario: admin  |  clave: {PASS_DEFAULT}")
else:
    info("admin ya existe, se omite")

# 2. PROFESORES
titulo("2 . Profesores")
profesores_data = [
    dict(username='prof_garcia', first_name='Carlos',  last_name='Garcia', email='c.garcia@conectate.edu.co'),
    dict(username='prof_lopez',  first_name='Maria',   last_name='Lopez',  email='m.lopez@conectate.edu.co'),
    dict(username='prof_torres', first_name='Andres',  last_name='Torres', email='a.torres@conectate.edu.co'),
]
profesores = []
for d in profesores_data:
    u, created = User.objects.get_or_create(username=d['username'], defaults={
        **d,
        'rol': User.ROL_PROFESOR,
        'password': make_password(PASS_DEFAULT),
        'telefono': '310' + str(random.randint(1_000_000, 9_999_999)),
        'bio': 'Docente comprometido/a con el bienestar de sus estudiantes.',
    })
    profesores.append(u)
    ok(f"Profesor: {u.get_full_name()}  ->  @{u.username}") if created else info(f"@{u.username} ya existe")

# 3. CURSOS
titulo("3 . Cursos / Grupos")
cursos_data = [
    dict(grado='8',  seccion='A', profesor=profesores[0], descripcion='Octavo grado seccion A'),
    dict(grado='9',  seccion='B', profesor=profesores[1], descripcion='Noveno grado seccion B'),
    dict(grado='11', seccion='A', profesor=profesores[2], descripcion='Undecimo grado seccion A'),
]
cursos = []
for d in cursos_data:
    c, created = Curso.objects.get_or_create(
        grado=d['grado'], seccion=d['seccion'],
        defaults={'profesor': d['profesor'], 'descripcion': d['descripcion']},
    )
    cursos.append(c)
    ok(f"Curso: Grado {c.grado}{c.seccion}  ->  Prof. {c.profesor.get_full_name()}") if created else info(f"Curso {c.nombre} ya existe")

# 4. ESTUDIANTES (un solo grado por estudiante)
titulo("4 . Estudiantes  (maximo un grado cada uno)")
estudiantes_data = [
    # Grado 8A
    dict(username='est_sofia',     first_name='Sofia',     last_name='Ramirez',  email='sofia@est.edu.co',     curso=cursos[0]),
    dict(username='est_julian',    first_name='Julian',    last_name='Moreno',   email='julian@est.edu.co',    curso=cursos[0]),
    dict(username='est_valeria',   first_name='Valeria',   last_name='Castro',   email='valeria@est.edu.co',   curso=cursos[0]),
    dict(username='est_miguel',    first_name='Miguel',    last_name='Herrera',  email='miguel@est.edu.co',    curso=cursos[0]),
    # Grado 9B
    dict(username='est_camila',    first_name='Camila',    last_name='Vargas',   email='camila@est.edu.co',    curso=cursos[1]),
    dict(username='est_daniel',    first_name='Daniel',    last_name='Perez',    email='daniel@est.edu.co',    curso=cursos[1]),
    dict(username='est_sara',      first_name='Sara',      last_name='Jimenez',  email='sara@est.edu.co',      curso=cursos[1]),
    dict(username='est_mateo',     first_name='Mateo',     last_name='Rojas',    email='mateo@est.edu.co',     curso=cursos[1]),
    # Grado 11A
    dict(username='est_isabella',  first_name='Isabella',  last_name='Mendoza',  email='isabella@est.edu.co',  curso=cursos[2]),
    dict(username='est_sebastian', first_name='Sebastian', last_name='Ortiz',    email='sebastian@est.edu.co', curso=cursos[2]),
    dict(username='est_valentina', first_name='Valentina', last_name='Silva',    email='valentina@est.edu.co', curso=cursos[2]),
    dict(username='est_samuel',    first_name='Samuel',    last_name='Diaz',     email='samuel@est.edu.co',    curso=cursos[2]),
]
estudiantes = []
for d in estudiantes_data:
    curso_asignado = d.pop('curso')
    u, created = User.objects.get_or_create(username=d['username'], defaults={
        **d,
        'rol': User.ROL_ESTUDIANTE,
        'password': make_password(PASS_DEFAULT),
        'bio': 'Estudiante de Conectate.',
    })
    estudiantes.append(u)

    # Garantizar UNA sola inscripcion activa
    inscribir_en_un_solo_curso(u, curso_asignado)

    # Validacion: no puede haber mas de una inscripcion activa
    total_activas = Inscripcion.objects.filter(estudiante=u, activa=True).count()
    if total_activas != 1:
        print(f"  ERROR: {u.username} tiene {total_activas} inscripciones activas. Se esperaba 1.")
        sys.exit(1)

    if created:
        ok(f"Estudiante: {u.get_full_name()}  ->  @{u.username}  ({curso_asignado.nombre})")
    else:
        info(f"@{u.username} ya existe  ->  inscripcion verificada en {curso_asignado.nombre}")

# 5. PADRES DE FAMILIA
titulo("5 . Padres de familia")
padres_data = [
    dict(username='padre_ramirez', first_name='Jorge',    last_name='Ramirez', email='jorge.r@gmail.com',    hijos=[estudiantes[0]]),
    dict(username='madre_moreno',  first_name='Lucia',    last_name='Moreno',  email='lucia.m@gmail.com',    hijos=[estudiantes[1]]),
    dict(username='padre_vargas',  first_name='Roberto',  last_name='Vargas',  email='roberto.v@gmail.com',  hijos=[estudiantes[4], estudiantes[5]]),
    dict(username='madre_castro',  first_name='Patricia', last_name='Castro',  email='patricia.c@gmail.com', hijos=[estudiantes[2]]),
    dict(username='padre_mendoza', first_name='Eduardo',  last_name='Mendoza', email='eduardo.m@gmail.com',  hijos=[estudiantes[8]]),
    dict(username='madre_ortiz',   first_name='Carmen',   last_name='Ortiz',   email='carmen.o@gmail.com',   hijos=[estudiantes[9]]),
]
padres = []
for d in padres_data:
    hijos = d.pop('hijos')
    u, created = User.objects.get_or_create(username=d['username'], defaults={
        **d,
        'rol': User.ROL_PADRE,
        'password': make_password(PASS_DEFAULT),
        'bio': 'Padre/Madre de familia vinculado a Conectate.',
        'telefono': '315' + str(random.randint(1_000_000, 9_999_999)),
    })
    padres.append(u)
    for hijo in hijos:
        VinculoPadreHijo.objects.get_or_create(
            padre=u, estudiante=hijo,
            defaults={'relacion': 'padre', 'activo': True},
        )
    if created:
        ok(f"Padre: {u.get_full_name()}  ->  @{u.username}  (hijos: {', '.join(h.first_name for h in hijos)})")
    else:
        info(f"@{u.username} ya existe")

# 6. REGISTROS EMOCIONALES (30 dias)
titulo("6 . Registros emocionales (ultimos 30 dias)")
EMOCIONES = ['feliz', 'tranquilo', 'estresado', 'triste', 'enojado']
PUNTAJES  = {'feliz': 5, 'tranquilo': 4, 'estresado': 2, 'triste': 2, 'enojado': 1}
COMENTARIOS = {
    'feliz':     ["Hoy fue un gran dia", "Me siento muy bien", "Excelente jornada escolar"],
    'tranquilo': ["Todo esta bien", "Un dia tranquilo", "Me siento equilibrado"],
    'estresado': ["Tengo muchas tareas", "El examen me preocupa", "Demasiadas cosas a la vez"],
    'triste':    ["Extrano a mis amigos", "No tuve un buen dia", "Me siento solo/a"],
    'enojado':   ["Algo me molesto hoy", "No fue un buen dia", "Hubo un problema"],
}
hoy = date.today()
total_regs = 0
for est in estudiantes:
    for i in range(30):
        dia = hoy - timedelta(days=i)
        if random.random() < 0.85:
            emocion = random.choices(EMOCIONES, weights=[30, 25, 20, 15, 10])[0]
            try:
                _, created = RegistroEmocional.objects.get_or_create(
                    estudiante=est, fecha=dia,
                    defaults={
                        'emocion': emocion,
                        'puntaje': PUNTAJES[emocion],
                        'comentario': random.choice(COMENTARIOS[emocion]),
                    },
                )
                if created:
                    total_regs += 1
            except Exception:
                pass
ok(f"{total_regs} registros emocionales creados para {len(estudiantes)} estudiantes")

# 7. ENTRADAS DE DIARIO
titulo("7 . Entradas de diario personal")
TITULOS_DIARIO = [
    "Reflexion del dia", "Como me senti hoy", "Mis pensamientos",
    "Un dia especial", "Lo que aprendi hoy", "Mis emociones",
    "Hoy quiero escribir", "Diario del alma", "Mis metas",
]
CONTENIDOS_DIARIO = [
    "Hoy fue un dia muy especial. Aprendi cosas nuevas en clase y me senti acompanado por mis companeros.",
    "A veces la vida escolar es dificil, pero se que con esfuerzo puedo superar los retos que se presentan.",
    "Me siento agradecido/a por tener un buen profesor que se preocupa por nosotros.",
    "Hoy tuve un pequeno conflicto con un companero pero lo resolvimos hablando. Me siento mejor.",
    "Estoy emocionado/a por el proyecto que presentamos. Fue mucho trabajo pero valio la pena.",
    "Necesito descansar mas. El estres de los examenes me tiene agotado/a.",
    "Hoy practique la respiracion que nos ensenaron y me ayudo mucho a calmarme.",
    "Manana tengo examen de matematicas. Estudie bastante, espero que me vaya bien.",
]
total_diario = 0
for est in estudiantes:
    for j in range(random.randint(3, 8)):
        emocion = random.choice(EMOCIONES)
        _, created = EntradaDiario.objects.get_or_create(
            estudiante=est,
            titulo=random.choice(TITULOS_DIARIO) + f" #{j + 1}",
            defaults={
                'contenido': random.choice(CONTENIDOS_DIARIO),
                'emocion_del_dia': emocion,
                'estado': 'guardado',
                'es_privado': True,
            },
        )
        if created:
            total_diario += 1
ok(f"{total_diario} entradas de diario creadas")

# 8. ACTIVIDADES POR CURSO
titulo("8 . Actividades por curso")
actividades_base = [
    dict(titulo="Respiracion consciente", tipo="respiracion",
         descripcion="Practica 5 respiraciones profundas: inhala 4 segundos, manten 4, exhala 4."),
    dict(titulo="Como estoy hoy?", tipo="bienestar",
         descripcion="Describe en 3 palabras como amaneciste hoy y que esperas de la jornada escolar."),
    dict(titulo="Gratitud del dia", tipo="gratitud",
         descripcion="Escribe 3 cosas por las que estes agradecido/a hoy. Pueden ser grandes o pequenas."),
    dict(titulo="Meditacion de 5 minutos", tipo="meditacion",
         descripcion="Cierra los ojos, enfocate en tu respiracion durante 5 minutos. Luego escribe como te sentiste."),
    dict(titulo="Reflexion semanal", tipo="reflexion",
         descripcion="Piensa en esta semana: que fue lo mejor? que fue lo mas dificil? que aprendiste de ti mismo/a?"),
]
respuestas_tipo = {
    'respiracion': ["Me senti mas calmado/a despues", "Fue dificil concentrarme al principio", "Me relaje bastante"],
    'bienestar':   ["Tranquilo, esperanzado, listo", "Cansado, ansioso, curioso", "Feliz, agradecido, motivado"],
    'gratitud':    ["Mi familia, mis amigos, mi salud", "El desayuno, el sol, mis companeros", "La musica, el deporte, mi mascota"],
    'meditacion':  ["Al principio me costo pero luego fue bien", "Me quede dormido/a pero me relaje", "Fue una experiencia nueva y positiva"],
    'reflexion':   ["Lo mejor fue el trabajo en equipo.", "Aprendi que debo organizarme mejor.", "Esta semana me senti mas seguro/a."],
}
total_act = 0
total_resp = 0
for curso in cursos:
    profesor = curso.profesor
    est_ids = list(
        Inscripcion.objects.filter(curso=curso, activa=True).values_list('estudiante_id', flat=True)
    )
    for j, act_data in enumerate(actividades_base):
        act, created = Actividad.objects.get_or_create(
            titulo=act_data['titulo'],
            curso=curso,
            defaults={**act_data, 'creada_por': profesor, 'semana': j + 1, 'activa': True},
        )
        if created:
            total_act += 1
        for est_id in est_ids:
            if random.random() < 0.75:
                _, created_r = RespuestaActividad.objects.get_or_create(
                    actividad=act, estudiante_id=est_id,
                    defaults={'respuesta': random.choice(respuestas_tipo.get(act.tipo, ["Participe en la actividad."]))},
                )
                if created_r:
                    total_resp += 1
ok(f"{total_act} actividades y {total_resp} respuestas creadas")

# 9. NOTAS DE PROFESORES
titulo("9 . Notas de profesores sobre estudiantes")
NOTAS_CONTENIDO = [
    "El estudiante muestra buena disposicion en clase. Ha mejorado notablemente en las ultimas semanas.",
    "Se ha notado cierta tristeza en las ultimas sesiones. Requiere seguimiento cercano.",
    "Excelente desempeno academico y emocional. Es un ejemplo para sus companeros.",
    "Ha faltado a varias clases. Pendiente contactar a los padres para verificar situacion.",
    "Se integra bien al grupo. Sus registros emocionales muestran tendencia positiva.",
    "Pendiente hablar con el estudiante sobre su bienestar. Sus registros son inconsistentes.",
]
total_notas = 0
for est in estudiantes:
    insc = Inscripcion.objects.filter(estudiante=est, activa=True).select_related('curso__profesor').first()
    if insc and insc.curso.profesor:
        _, created = NotaProfesor.objects.get_or_create(
            profesor=insc.curso.profesor, estudiante=est,
            defaults={'contenido': random.choice(NOTAS_CONTENIDO)},
        )
        if created:
            total_notas += 1
ok(f"{total_notas} notas de seguimiento creadas")

# 10. MENSAJES DIRECTOS
titulo("10 . Mensajes directos")
mensajes_prof_est = [
    "Hola {nombre}, queria recordarte entregar la actividad de esta semana. Mucho animo!",
    "Hola {nombre}, he notado que esta semana has registrado emociones dificiles. Estas bien?",
    "Felicitaciones {nombre}! Tu progreso emocional esta semana fue excelente. Sigue asi!",
]
mensajes_padre_prof = [
    "Buenas tardes profe, queria preguntar como ha estado mi hijo/a en clases esta semana.",
    "Profesor/a, podriamos coordinar una reunion para hablar sobre el avance de mi hijo/a?",
    "Gracias por el seguimiento que le hace a mi hijo/a. Notamos mejoras en casa tambien.",
]
total_msgs = 0
for est in estudiantes[:6]:
    insc = Inscripcion.objects.filter(estudiante=est, activa=True).select_related('curso__profesor').first()
    if insc and insc.curso.profesor:
        prof = insc.curso.profesor
        _, created = MensajeDirecto.objects.get_or_create(
            remitente=prof, destinatario=est,
            defaults={
                'contenido': random.choice(mensajes_prof_est).format(nombre=est.first_name),
                'leido': random.choice([True, False]),
            },
        )
        if created:
            total_msgs += 1
for padre in padres[:4]:
    vinculos = VinculoPadreHijo.objects.filter(padre=padre, activo=True).select_related('estudiante')
    for v in vinculos:
        insc = Inscripcion.objects.filter(estudiante=v.estudiante, activa=True).select_related('curso__profesor').first()
        if insc and insc.curso.profesor:
            prof = insc.curso.profesor
            _, created = MensajeDirecto.objects.get_or_create(
                remitente=padre, destinatario=prof,
                defaults={
                    'contenido': random.choice(mensajes_padre_prof),
                    'leido': random.choice([True, False]),
                },
            )
            if created:
                total_msgs += 1
ok(f"{total_msgs} mensajes directos creados")

# 11. LOGROS
titulo("11 . Logros")
LOGROS_BASICOS = ['primer_registro', 'racha_3', 'explorador', 'diario_5']
total_logros = 0
for est in estudiantes:
    for clave in random.sample(LOGROS_BASICOS, k=random.randint(1, 4)):
        _, created = Logro.objects.get_or_create(estudiante=est, clave=clave)
        if created:
            total_logros += 1
ok(f"{total_logros} logros desbloqueados")

# RESUMEN
titulo("DATOS CARGADOS EXITOSAMENTE")
print(f"""
  Todos los usuarios tienen la misma contrasena: {PASS_DEFAULT}

  USUARIOS CREADOS
  ─────────────────────────────────────────────
  Administrador  ->  admin
  Profesores     ->  prof_garcia, prof_lopez, prof_torres
  Estudiantes    ->  est_sofia, est_julian, est_valeria, est_miguel,
                     est_camila, est_daniel, est_sara, est_mateo,
                     est_isabella, est_sebastian, est_valentina, est_samuel
  Padres         ->  padre_ramirez, madre_moreno, padre_vargas,
                     madre_castro, padre_mendoza, madre_ortiz

  REGLA APLICADA:
  ─────────────────────────────────────────────
  Cada estudiante esta inscrito en exactamente UN grado.
  El sistema valida esto y falla si se detecta duplicado.

  PARA INICIAR EL SERVIDOR:
  ─────────────────────────────────────────────
  python manage.py runserver

  Luego abre:  http://127.0.0.1:8000/
""")
