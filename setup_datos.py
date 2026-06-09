#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup_datos.py — Carga datos de demostración para Conéctate.

Crea:
  • 1 superusuario administrador
  • 1 profesor: Alejandro Calero
  • 3 cursos: Grado 9A, 9B, 10A
  • 10 estudiantes por curso (30 en total)
    – Incluye est_valeria, est_isabella, est_jose en 9A
  • Padre Y Madre para cada estudiante (60 padres en total)
  • Registros emocionales de los últimos 30 días
  • Actividades (~60% hechas, ~40% pendientes), diarios, notas,
    mensajes y logros.
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


def ok(msg):     print(f"  ✅ {msg}")
def info(msg):   print(f"  📌 {msg}")
def titulo(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def inscribir(estudiante, curso):
    Inscripcion.objects.filter(
        estudiante=estudiante, activa=True
    ).exclude(curso=curso).update(activa=False)
    insc, created = Inscripcion.objects.get_or_create(
        estudiante=estudiante, curso=curso,
        defaults={'activa': True},
    )
    if not insc.activa:
        insc.activa = True
        insc.save(update_fields=['activa'])
    return insc, created


titulo("CONECTATE — Cargando datos de demostración")

PASS = "Conectate2024"
random.seed(99)

# ── 1. ADMIN ──────────────────────────────────────────────────────────────────
titulo("1. Superusuario")
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin', email='admin@conectate.edu.co',
        password=PASS, first_name='Super', last_name='Admin',
        rol=User.ROL_PROFESOR,
    )
    ok("admin creado  →  clave: Conectate2024")
else:
    info("admin ya existe")

# ── 2. PROFESOR ───────────────────────────────────────────────────────────────
titulo("2. Profesor Alejandro Calero")
prof, created = User.objects.get_or_create(
    username='prof_calero',
    defaults={
        'first_name': 'Alejandro', 'last_name': 'Calero',
        'email': 'a.calero@conectate.edu.co',
        'rol': User.ROL_PROFESOR,
        'password': make_password(PASS),
        'telefono': '3101234567',
        'bio': 'Docente comprometido con el bienestar emocional.',
    }
)
ok(f"{'Creado' if created else 'Ya existe'}  →  @prof_calero  ({prof.get_full_name()})")

# ── 3. CURSOS ─────────────────────────────────────────────────────────────────
titulo("3. Cursos")
CURSOS_DEF = [
    ('9',  'A', 'Noveno A'),
    ('9',  'B', 'Noveno B'),
    ('10', 'A', 'Décimo A'),
]
cursos = []
for grado, seccion, desc in CURSOS_DEF:
    c, created = Curso.objects.get_or_create(
        grado=grado, seccion=seccion,
        defaults={'profesor': prof, 'descripcion': desc},
    )
    if not created:
        c.profesor = prof
        c.save(update_fields=['profesor'])
    cursos.append(c)
    ok(f"{'Creado' if created else 'Ya existe'}  →  Grado {c.grado}{c.seccion}")
c9a, c9b, c10a = cursos

# ── 4. ESTUDIANTES ────────────────────────────────────────────────────────────
titulo("4. Estudiantes  (10 por curso + 3 especiales en 9A)")

# Estudiantes especiales fijos en 9A
ESPECIALES = [
    dict(username='est_valeria',  first_name='Valeria',  last_name='Torres',   curso=c9a),
    dict(username='est_isabella', first_name='Isabella', last_name='Rios',     curso=c9a),
    dict(username='est_jose',     first_name='Jose',     last_name='Castillo', curso=c9a),
]

NOMBRES_F = ['Sofia','Camila','Valentina','Mariana','Laura',
             'Daniela','Natalia','Sara','Paula','Alejandra']
NOMBRES_M = ['Julian','Mateo','Sebastian','Samuel','Andres',
             'David','Felipe','Nicolas','Diego','Miguel']
APELLIDOS  = ['Ramirez','Moreno','Herrera','Vargas','Perez',
              'Jimenez','Rojas','Mendoza','Ortiz','Silva',
              'Diaz','Torres','Gomez','Reyes','Lopez',
              'Garcia','Martinez','Sanchez','Ruiz','Castro']

todos_estudiantes = []
# map curso -> lista de estudiantes
est_por_curso = {c9a: [], c9b: [], c10a: []}

# Crear especiales primero
for d in ESPECIALES:
    curso_asig = d.pop('curso')
    u, created = User.objects.get_or_create(
        username=d['username'],
        defaults={**d, 'email': f"{d['username']}@est.edu.co",
                  'rol': User.ROL_ESTUDIANTE, 'password': make_password(PASS),
                  'bio': 'Estudiante de Conectate.'},
    )
    inscribir(u, curso_asig)
    todos_estudiantes.append(u)
    est_por_curso[curso_asig].append(u)
    ok(f"  {'Creado' if created else 'Ya existe'}  @{u.username}  ({u.get_full_name()}) → {curso_asig.nombre}")

# Rellenar hasta 10 por curso
for curso in cursos:
    existentes = len(est_por_curso[curso])
    for i in range(existentes + 1, 11):
        es_m = (i % 2 == 0)
        nombre   = random.choice(NOMBRES_M if es_m else NOMBRES_F)
        apellido = random.choice(APELLIDOS)
        username = f"est_{curso.grado}{curso.seccion.lower()}_{i:02d}"
        u, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': nombre, 'last_name': apellido,
                'email': f"{username}@est.edu.co",
                'rol': User.ROL_ESTUDIANTE, 'password': make_password(PASS),
                'bio': 'Estudiante de Conectate.',
            }
        )
        inscribir(u, curso)
        todos_estudiantes.append(u)
        est_por_curso[curso].append(u)
        ok(f"  {'Creado' if created else 'Ya existe'}  @{username}  ({u.get_full_name()}) → {curso.nombre}")

ok(f"Total: {len(todos_estudiantes)} estudiantes")

# ── 5. PADRES (padre + madre por cada estudiante) ─────────────────────────────
titulo("5. Padres y Madres  (1 padre + 1 madre por estudiante)")

NOMBRES_PADRE = ['Jorge','Carlos','Roberto','Eduardo','Miguel',
                 'Luis','Andres','Fernando','Ricardo','Hernando',
                 'Gustavo','Jairo','Cesar','Mario','Alberto',
                 'Rodrigo','Sergio','Oscar','Ivan','William',
                 'Hector','Ramon','Ernesto','Alfredo','Pedro',
                 'Victor','Raul','Ignacio','Mauricio','Gonzalo']
NOMBRES_MADRE = ['Lucia','Patricia','Carmen','Adriana','Gloria',
                 'Claudia','Monica','Sandra','Martha','Luz',
                 'Maria','Ana','Rosa','Elena','Beatriz',
                 'Cecilia','Diana','Liliana','Pilar','Esperanza',
                 'Amparo','Gladys','Olga','Nora','Stella',
                 'Marta','Isabel','Teresa','Irene','Yolanda']

todos_padres = []
total_vinculos = 0

for idx, est in enumerate(todos_estudiantes):
    apellido_est = est.last_name

    # — PADRE —
    u_padre_name = f"padre_{est.username}"
    nombre_p = NOMBRES_PADRE[idx % len(NOMBRES_PADRE)]
    u_padre, created_p = User.objects.get_or_create(
        username=u_padre_name,
        defaults={
            'first_name': nombre_p, 'last_name': apellido_est,
            'email': f"{u_padre_name}@gmail.com",
            'rol': User.ROL_PADRE, 'password': make_password(PASS),
            'bio': 'Padre de familia vinculado a Conectate.',
            'telefono': '315' + str(random.randint(1_000_000, 9_999_999)),
        }
    )
    VinculoPadreHijo.objects.get_or_create(
        padre=u_padre, estudiante=est,
        defaults={'relacion': 'padre', 'activo': True},
    )
    todos_padres.append(u_padre)
    total_vinculos += 1

    # — MADRE —
    u_madre_name = f"madre_{est.username}"
    nombre_m = NOMBRES_MADRE[idx % len(NOMBRES_MADRE)]
    u_madre, created_m = User.objects.get_or_create(
        username=u_madre_name,
        defaults={
            'first_name': nombre_m, 'last_name': apellido_est,
            'email': f"{u_madre_name}@gmail.com",
            'rol': User.ROL_PADRE, 'password': make_password(PASS),
            'bio': 'Madre de familia vinculada a Conectate.',
            'telefono': '312' + str(random.randint(1_000_000, 9_999_999)),
        }
    )
    VinculoPadreHijo.objects.get_or_create(
        padre=u_madre, estudiante=est,
        defaults={'relacion': 'madre', 'activo': True},
    )
    todos_padres.append(u_madre)
    total_vinculos += 1

    ok(f"  {u_padre.get_full_name():22s} (padre)  +  {u_madre.get_full_name():22s} (madre)  →  {est.get_full_name()}")

ok(f"Total: {len(todos_padres)} padres/madres  |  {total_vinculos} vínculos")

# ── 6. REGISTROS EMOCIONALES (30 días) ────────────────────────────────────────
titulo("6. Registros emocionales — últimos 30 días")

EMOCIONES  = ['feliz', 'tranquilo', 'estresado', 'triste', 'enojado']
PUNTAJES   = {'feliz': 5, 'tranquilo': 4, 'estresado': 2, 'triste': 2, 'enojado': 1}
COMENTARIOS = {
    'feliz':     ["Hoy fue un gran día", "Me siento muy bien", "Excelente jornada escolar"],
    'tranquilo': ["Todo está bien", "Un día tranquilo", "Me siento equilibrado"],
    'estresado': ["Tengo muchas tareas", "El examen me preocupa", "Demasiadas cosas a la vez"],
    'triste':    ["Extraño a mis amigos", "No tuve un buen día", "Me siento solo/a"],
    'enojado':   ["Algo me molestó hoy", "No fue un buen día", "Hubo un problema"],
}

hoy = date.today()
total_regs = 0
for est in todos_estudiantes:
    for dias_atras in range(30):
        dia = hoy - timedelta(days=dias_atras)
        if random.random() < 0.88:   # alta participación
            emocion = random.choices(EMOCIONES, weights=[30, 25, 20, 15, 10])[0]
            _, created = RegistroEmocional.objects.get_or_create(
                estudiante=est, fecha=dia,
                defaults={
                    'emocion':    emocion,
                    'puntaje':    PUNTAJES[emocion],
                    'comentario': random.choice(COMENTARIOS[emocion]),
                },
            )
            if created:
                total_regs += 1
ok(f"{total_regs} registros emocionales creados")

# ── 7. ENTRADAS DE DIARIO ─────────────────────────────────────────────────────
titulo("7. Entradas de diario")
TITULOS_D  = ["Reflexión del día", "Cómo me sentí hoy", "Mis pensamientos",
              "Un día especial", "Lo que aprendí", "Mis emociones", "Mis metas"]
CONTENIDOS_D = [
    "Hoy fue un día muy especial. Aprendí cosas nuevas en clase.",
    "A veces la vida escolar es difícil, pero sé que puedo superar los retos.",
    "Me siento agradecido/a por tener un buen profesor que se preocupa por nosotros.",
    "Hoy tuve un pequeño conflicto con un compañero pero lo resolvimos hablando.",
    "Estoy emocionado/a por el proyecto. Fue mucho trabajo pero valió la pena.",
    "Necesito descansar más. El estrés de los exámenes me tiene agotado/a.",
    "Hoy practiqué la respiración y me ayudó mucho a calmarme.",
    "Mañana tengo examen. Estudié bastante, espero que me vaya bien.",
]
total_diario = 0
for est in todos_estudiantes:
    for j in range(random.randint(3, 8)):
        _, created = EntradaDiario.objects.get_or_create(
            estudiante=est,
            titulo=random.choice(TITULOS_D) + f" #{j+1}",
            defaults={
                'contenido':       random.choice(CONTENIDOS_D),
                'emocion_del_dia': random.choice(EMOCIONES),
                'estado':          'guardado',
                'es_privado':      True,
            },
        )
        if created:
            total_diario += 1
ok(f"{total_diario} entradas de diario creadas")

# ── 8. ACTIVIDADES ────────────────────────────────────────────────────────────
titulo("8. Actividades (~60% hechas, ~40% pendientes)")
ACTIVIDADES_BASE = [
    dict(titulo="Respiración consciente", tipo="respiracion",
         descripcion="Practica 5 respiraciones profundas: inhala 4 s, mantén 4, exhala 4."),
    dict(titulo="¿Cómo estoy hoy?", tipo="bienestar",
         descripcion="Describe en 3 palabras cómo amaneciste y qué esperas de la jornada."),
    dict(titulo="Gratitud del día", tipo="gratitud",
         descripcion="Escribe 3 cosas por las que estés agradecido/a hoy."),
    dict(titulo="Meditación de 5 minutos", tipo="meditacion",
         descripcion="Cierra los ojos, enfócate en tu respiración 5 min."),
    dict(titulo="Reflexión semanal", tipo="reflexion",
         descripcion="¿Qué fue lo mejor y lo más difícil de esta semana?"),
]
RESP_TIPO = {
    'respiracion': ["Me sentí más calmado/a", "Fue difícil concentrarme al inicio", "Me relajé bastante"],
    'bienestar':   ["Tranquilo, esperanzado, listo", "Cansado, ansioso, curioso"],
    'gratitud':    ["Mi familia, mis amigos, mi salud", "El desayuno, el sol, mis compañeros"],
    'meditacion':  ["Al principio me costó, luego fue bien", "Me quedé dormido/a pero me relajé"],
    'reflexion':   ["Lo mejor fue el trabajo en equipo.", "Aprendí que debo organizarme mejor."],
}
total_act = 0
total_resp = 0
for curso in cursos:
    est_ids = [u.pk for u in est_por_curso[curso]]
    for semana, act_data in enumerate(ACTIVIDADES_BASE, start=1):
        act, created = Actividad.objects.get_or_create(
            titulo=act_data['titulo'], curso=curso,
            defaults={**act_data, 'creada_por': prof, 'semana': semana, 'activa': True},
        )
        if created:
            total_act += 1
        respondientes = random.sample(est_ids, k=max(1, int(len(est_ids) * 0.6)))
        for est_id in respondientes:
            _, cr = RespuestaActividad.objects.get_or_create(
                actividad=act, estudiante_id=est_id,
                defaults={'respuesta': random.choice(RESP_TIPO.get(act.tipo, ["Participé."]))},
            )
            if cr:
                total_resp += 1
ok(f"{total_act} actividades  |  {total_resp} respuestas  (≈40% sin completar)")

# ── 9. NOTAS DEL PROFESOR ─────────────────────────────────────────────────────
titulo("9. Notas del profesor")
NOTAS = [
    "El estudiante muestra buena disposición. Ha mejorado en las últimas sesiones.",
    "Se ha notado cierta tristeza. Requiere seguimiento cercano.",
    "Excelente desempeño emocional. Es un ejemplo para el grupo.",
    "Faltó a varias clases. Pendiente contactar acudiente.",
    "Se integra bien al grupo. Sus registros muestran tendencia positiva.",
    "Pendiente hablar sobre su bienestar. Registros inconsistentes.",
]
total_notas = 0
for est in todos_estudiantes:
    _, cr = NotaProfesor.objects.get_or_create(
        profesor=prof, estudiante=est,
        defaults={'contenido': random.choice(NOTAS)},
    )
    if cr:
        total_notas += 1
ok(f"{total_notas} notas de seguimiento creadas")

# ── 10. MENSAJES DIRECTOS ─────────────────────────────────────────────────────
titulo("10. Mensajes directos")
MSGS = [
    "Hola {nombre}, recuerda entregar la actividad de esta semana. ¡Mucho ánimo!",
    "Hola {nombre}, noté emociones difíciles esta semana. ¿Estás bien?",
    "¡Felicitaciones {nombre}! Tu progreso emocional esta semana fue excelente.",
]
total_msgs = 0
for est in random.sample(todos_estudiantes, k=min(18, len(todos_estudiantes))):
    _, cr = MensajeDirecto.objects.get_or_create(
        remitente=prof, destinatario=est,
        defaults={
            'contenido': random.choice(MSGS).format(nombre=est.first_name),
            'leido': random.choice([True, False]),
        },
    )
    if cr:
        total_msgs += 1
ok(f"{total_msgs} mensajes directos creados")

# ── 11. LOGROS ────────────────────────────────────────────────────────────────
titulo("11. Logros")
LOGROS = ['primer_registro', 'racha_3', 'explorador', 'diario_5']
total_logros = 0
for est in todos_estudiantes:
    for clave in random.sample(LOGROS, k=random.randint(1, 4)):
        _, cr = Logro.objects.get_or_create(estudiante=est, clave=clave)
        if cr:
            total_logros += 1
ok(f"{total_logros} logros desbloqueados")

# ── RESUMEN FINAL ──────────────────────────────────────────────────────────────
titulo("✅  DATOS CARGADOS EXITOSAMENTE")
print(f"""
  Contraseña para TODOS los usuarios: {PASS}

  CUENTAS
  ──────────────────────────────────────────────────────
  Admin        →  admin
  Profesor     →  prof_calero          (Alejandro Calero)

  Estudiantes especiales:
    est_valeria   (Valeria Torres)    → Grado 9A
    est_isabella  (Isabella Rios)     → Grado 9A
    est_jose      (Jose Castillo)     → Grado 9A

  Estudiantes generados:
    est_9a_04 … est_9a_10             → Grado 9A
    est_9b_01 … est_9b_10             → Grado 9B
    est_10a_01 … est_10a_10           → Grado 10A

  Padres/madres:
    padre_est_<username>  /  madre_est_<username>
    (1 padre + 1 madre por cada uno de los 30 estudiantes)

  DATOS GENERADOS
  ──────────────────────────────────────────────────────
  • Registros emocionales: 30 días  (alta participación)
  • Actividades: ~60% completadas, ~40% pendientes
  • Diarios, notas del profesor, mensajes y logros incluidos
""")
