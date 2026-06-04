#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup_masivo.py — Carga masiva para Conéctate.

Crea:
  • 12 cursos: grados 6A, 6B, 7A, 7B, 8A, 8B, 9A, 9B, 10A, 10B, 11A, 11B
  • 30 estudiantes por curso  ->  360 estudiantes en total
  • ~310 padres/acudientes vinculados
  • Registros emocionales (45 dias), diarios, actividades, notas, mensajes, logros

NO crea nuevos profesores. Usa los existentes de forma rotatoria.
"""

import os, sys, random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conectate.settings')

import django
django.setup()

from django.contrib.auth.hashers import make_password
from apps.accounts.models import User, VinculoPadreHijo
from apps.courses.models import Curso, Inscripcion
from apps.activities.models import Actividad, RespuestaActividad
from apps.emotions.models import (
    RegistroEmocional, EntradaDiario, Logro,
    NotaProfesor, MensajeDirecto,
)

def ok(msg):     print(f"  \u2705 {msg}")
def info(msg):   print(f"  \U0001f4cc {msg}")
def titulo(msg): print(f"\n{'='*62}\n  {msg}\n{'='*62}")

PASS = "Conectate2024"

def inscribir(estudiante, curso):
    Inscripcion.objects.filter(
        estudiante=estudiante, activa=True
    ).exclude(curso=curso).update(activa=False)
    insc, _ = Inscripcion.objects.get_or_create(
        estudiante=estudiante, curso=curso,
        defaults={'activa': True},
    )
    if not insc.activa:
        insc.activa = True
        insc.save(update_fields=['activa'])

NF = [
    'Sofia','Valentina','Isabella','Camila','Gabriela','Paula','Natalia',
    'Daniela','Maria','Laura','Mariana','Alejandra','Luisa','Catalina',
    'Sara','Manuela','Angela','Monica','Carolina','Juliana','Paola',
    'Melissa','Viviana','Diana','Claudia','Adriana','Lorena','Sandra',
    'Andrea','Fernanda','Yuliana','Liliana','Tatiana','Marcela','Marta',
    'Veronica','Patricia','Pilar','Elena','Rosa','Ana','Teresa','Cecilia',
    'Beatriz','Silvia','Olga','Consuelo','Esperanza','Gloria','Amparo',
]
NM = [
    'Santiago','Mateo','Juan','Sebastian','Felipe','Andres','David',
    'Daniel','Miguel','Carlos','Alejandro','Nicolas','Sergio','Luis',
    'Esteban','Julian','Diego','Ricardo','Ivan','Jorge','Gabriel',
    'Alberto','Oscar','Mario','Leonardo','Pablo','Antonio','Fernando',
    'Manuel','Eduardo','Rodrigo','Javier','Raul','Hector','Samuel',
    'Gustavo','Alfredo','Ernesto','Cristian','Jonathan','Brian','Kevin',
    'Johan','Fabian','Camilo','Wilmer','Harold','Jefferson','Brayan',
]
APELLIDOS = [
    'Garcia','Rodriguez','Lopez','Martinez','Gonzalez','Perez','Sanchez',
    'Ramirez','Torres','Flores','Vargas','Morales','Jimenez','Castillo',
    'Ramos','Mendoza','Reyes','Cruz','Herrera','Medina','Castro','Ortiz',
    'Ruiz','Aguilar','Romero','Silva','Diaz','Guerrero','Munoz','Alvarado',
    'Rojas','Pineda','Molina','Acosta','Cardenas','Pena','Rios','Mora',
    'Valencia','Serrano','Ospina','Parra','Suarez','Quintero','Salinas',
    'Escobar','Trujillo','Correa','Zapata','Velez','Ochoa','Cano','Arias',
    'Bermudez','Castano','Giraldo','Hoyos','Londono','Montoya','Naranjo',
    'Restrepo','Rincon','Salcedo','Urrego','Velandia','Wilches','Zuluaga',
]
NPF = [
    'Patricia','Carmen','Gloria','Rosa','Ana','Marta','Lucia','Teresa',
    'Cecilia','Beatriz','Elena','Silvia','Olga','Pilar','Consuelo',
    'Esperanza','Amparo','Dolores','Mercedes','Graciela','Nohora','Nubia',
    'Gladys','Marleny','Luz','Alba','Sonia','Fabiola','Mariela','Norma',
]
NPM = [
    'Jorge','Carlos','Roberto','Eduardo','Fernando','Luis','Alberto',
    'Mario','Antonio','Manuel','Pedro','Raul','Gabriel','Hector','Omar',
    'Gustavo','Hernando','Jairo','Nelson','Ernesto','Gilberto','Alvaro',
    'Dario','Bernardo','Rodrigo','Alfredo','Armando','Cesar','Ivan','Henry',
]

_usados_est = set()
_usados_pad = set()

def _uniq(base, pool):
    base = base[:24]
    if base not in pool:
        pool.add(base); return base
    for i in range(1, 9999):
        c = f"{base}{i}"[:30]
        if c not in pool:
            pool.add(c); return c

def nuevo_estudiante():
    f = random.random() < 0.50
    nombre = random.choice(NF if f else NM)
    ap1 = random.choice(APELLIDOS)
    ap2 = random.choice(APELLIDOS)
    username = _uniq(f"est_{nombre[:8].lower()}_{ap1[:8].lower()}", _usados_est)
    return nombre, ap1, ap2, username

def nuevo_padre(apellido_hijo):
    f = random.random() < 0.55
    nombre = random.choice(NPF if f else NPM)
    username = _uniq(f"pad_{nombre[:8].lower()}_{apellido_hijo[:8].lower()}", _usados_pad)
    return nombre, apellido_hijo, username


titulo("1. Profesores existentes")
profesores = list(User.objects.filter(rol=User.ROL_PROFESOR, is_superuser=False))
if not profesores:
    print("  ERROR: no hay profesores. Ejecuta primero setup_datos.py")
    sys.exit(1)
for p in profesores:
    info(f"{p.get_full_name()} (@{p.username})")


titulo("2. Cursos 6A a 11B  (12 cursos)")
CURSOS_DEF = [
    ('6','A'),('6','B'),('7','A'),('7','B'),
    ('8','A'),('8','B'),('9','A'),('9','B'),
    ('10','A'),('10','B'),('11','A'),('11','B'),
]
todos_cursos = []
for i, (grado, seccion) in enumerate(CURSOS_DEF):
    prof = profesores[i % len(profesores)]
    c, created = Curso.objects.get_or_create(
        grado=grado, seccion=seccion,
        defaults={'profesor': prof, 'descripcion': f'Grado {grado} seccion {seccion}'},
    )
    if not c.profesor:
        c.profesor = prof; c.save(update_fields=['profesor'])
    todos_cursos.append(c)
    info(f"Grado {grado}{seccion} ({'creado' if created else 'ya existe'})  ->  {c.profesor.get_full_name()}")
ok(f"{len(todos_cursos)} cursos listos")


titulo("3. Estudiantes  (30 por curso = 360 total)")
todos_estudiantes = []
nuevos_est = 0

for curso in todos_cursos:
    ya = Inscripcion.objects.filter(curso=curso, activa=True).count()
    faltan = max(0, 30 - ya)
    nuevos_en_curso = 0
    for _ in range(faltan):
        nombre, ap1, ap2, username = nuevo_estudiante()
        u, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': nombre,
                'last_name': f"{ap1} {ap2}",
                'email': f"{username}@est.edu.co",
                'rol': User.ROL_ESTUDIANTE,
                'password': make_password(PASS),
                'bio': f'Estudiante de Grado {curso.grado}{curso.seccion}.',
                'telefono': '300' + str(random.randint(1_000_000, 9_999_999)),
            }
        )
        inscribir(u, curso)
        if created:
            nuevos_est += 1
            nuevos_en_curso += 1

    ids = list(Inscripcion.objects.filter(curso=curso, activa=True).values_list('estudiante_id', flat=True))
    for uid in ids:
        try:
            u2 = User.objects.get(pk=uid)
            if u2 not in todos_estudiantes:
                todos_estudiantes.append(u2)
        except User.DoesNotExist:
            pass

    total_ahora = Inscripcion.objects.filter(curso=curso, activa=True).count()
    ok(f"Grado {curso.grado}{curso.seccion}: {total_ahora} estudiantes ({nuevos_en_curso} nuevos)")

ok(f"\nEstudiantes nuevos: {nuevos_est}  |  Total en lista: {len(todos_estudiantes)}")


titulo("4. Padres / Acudientes")
padres_creados = 0
padres_lista = []

for est in todos_estudiantes:
    ap_hijo = est.last_name.split()[0] if est.last_name else 'Familia'
    if random.random() < 0.85:
        nombre, apellido, username = nuevo_padre(ap_hijo)
        p, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': nombre, 'last_name': apellido,
                'email': f"{username}@gmail.com",
                'rol': User.ROL_PADRE,
                'password': make_password(PASS),
                'bio': 'Padre/Madre vinculado a Conectate.',
                'telefono': '315' + str(random.randint(1_000_000, 9_999_999)),
            }
        )
        VinculoPadreHijo.objects.get_or_create(
            padre=p, estudiante=est,
            defaults={'relacion': random.choice(['padre','madre']), 'activo': True},
        )
        padres_lista.append(p)
        if created: padres_creados += 1

    if random.random() < 0.30:
        nombre, apellido, username = nuevo_padre(ap_hijo)
        p2, created2 = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': nombre, 'last_name': apellido,
                'email': f"{username}@gmail.com",
                'rol': User.ROL_PADRE,
                'password': make_password(PASS),
                'bio': 'Acudiente secundario en Conectate.',
                'telefono': '316' + str(random.randint(1_000_000, 9_999_999)),
            }
        )
        VinculoPadreHijo.objects.get_or_create(
            padre=p2, estudiante=est,
            defaults={'relacion': 'acudiente', 'activo': True},
        )
        padres_lista.append(p2)
        if created2: padres_creados += 1

ok(f"Padres/acudientes nuevos: {padres_creados}")


titulo("5. Registros emocionales  (45 dias por estudiante)")
EMOCIONES = ['feliz','tranquilo','estresado','triste','enojado']
PUNTAJES  = {'feliz':5,'tranquilo':4,'estresado':2,'triste':2,'enojado':1}
COMENTARIOS = {
    'feliz':     ["Hoy fue un gran dia","Me siento muy bien","Excelente jornada","Estoy contento/a","Todo salio bien"],
    'tranquilo': ["Todo esta bien","Un dia tranquilo","Me siento equilibrado","Sin novedad hoy","Paz interior"],
    'estresado': ["Tengo muchas tareas","El examen me preocupa","Demasiadas cosas","Mucha presion academica","Me siento agobiado/a"],
    'triste':    ["Extrano a mis amigos","No tuve un buen dia","Me siento solo/a","Algo me entristecio","Dia dificil"],
    'enojado':   ["Algo me molesto","No fue un buen dia","Hubo un problema","Me senti frustrado/a","Conflicto en clase"],
}
hoy = date.today()
total_regs = 0
existentes_regs = set(RegistroEmocional.objects.values_list('estudiante_id','fecha'))
batch = []
for est in todos_estudiantes:
    for i in range(45):
        dia = hoy - timedelta(days=i)
        if (est.pk, dia) in existentes_regs: continue
        if random.random() < 0.83:
            emocion = random.choices(EMOCIONES, weights=[30,25,20,15,10])[0]
            batch.append(RegistroEmocional(
                estudiante=est, fecha=dia,
                emocion=emocion, puntaje=PUNTAJES[emocion],
                comentario=random.choice(COMENTARIOS[emocion]),
            ))
            total_regs += 1
            if len(batch) >= 500:
                RegistroEmocional.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
if batch:
    RegistroEmocional.objects.bulk_create(batch, ignore_conflicts=True)
ok(f"{total_regs} registros emocionales creados")


titulo("6. Entradas de diario")
TITULOS = [
    "Reflexion del dia","Como me senti hoy","Mis pensamientos",
    "Un dia especial","Lo que aprendi hoy","Mis emociones",
    "Hoy quiero escribir","Diario del alma","Mis metas",
    "Lo que me preocupa","Mis logros de hoy","Agradecimiento",
    "Mi semana en resumen","Conversacion conmigo","Mis suenos",
    "Superando retos","Momentos que valoro","Mi estado de animo",
]
CONTENIDOS = [
    "Hoy fue un dia muy especial. Aprendi cosas nuevas y me senti acompanado/a.",
    "A veces la vida escolar es dificil, pero con esfuerzo puedo superar los retos.",
    "Me siento agradecido/a por tener profesores que se preocupan por nosotros.",
    "Hoy tuve un conflicto con un companero pero lo resolvimos hablando.",
    "Estoy emocionado/a por el proyecto que presentamos. Valio la pena.",
    "Necesito descansar mas. El estres de los examenes me tiene agotado/a.",
    "Hoy practique la respiracion consciente y me ayudo a calmarme.",
    "Aprendi que debo ser mas paciente conmigo mismo/a. Las cosas llevan su tiempo.",
    "Me alegra tener amigos que me apoyan cuando tengo dias dificiles.",
    "Pense mucho en mis metas de vida. Quiero ser una mejor version de mi.",
    "Hoy participe en clase mas de lo normal. Me senti seguro/a al hablar.",
    "Fue un dia largo pero productivo. Me siento satisfecho/a con lo que logre.",
    "Hoy ayude a un companero y eso me hizo sentir muy bien.",
    "Quiero mejorar mis habitos de estudio. Empezare poco a poco.",
    "Hoy me di cuenta de lo importante que es cuidar mi salud mental.",
]
total_diario = 0
for est in todos_estudiantes:
    for j in range(random.randint(5, 12)):
        titulo_e = random.choice(TITULOS) + f" #{j+1}"
        _, created = EntradaDiario.objects.get_or_create(
            estudiante=est, titulo=titulo_e,
            defaults={
                'contenido': random.choice(CONTENIDOS),
                'emocion_del_dia': random.choice(EMOCIONES),
                'estado': 'guardado', 'es_privado': True,
            }
        )
        if created: total_diario += 1
ok(f"{total_diario} entradas de diario creadas")


titulo("7. Actividades por curso")
ACTS = [
    dict(titulo="Respiracion consciente", tipo="respiracion",
         descripcion="5 respiraciones profundas: inhala 4s, manten 4s, exhala 4s."),
    dict(titulo="Como estoy hoy?", tipo="bienestar",
         descripcion="Describe en 3 palabras como amaneciste hoy."),
    dict(titulo="Gratitud del dia", tipo="gratitud",
         descripcion="Escribe 3 cosas por las que estes agradecido/a hoy."),
    dict(titulo="Meditacion de 5 minutos", tipo="meditacion",
         descripcion="Cierra los ojos y enfocate en tu respiracion 5 minutos."),
    dict(titulo="Reflexion semanal", tipo="reflexion",
         descripcion="Que fue lo mejor de la semana? Que aprendiste de ti mismo/a?"),
    dict(titulo="Carta a mi yo futuro", tipo="reflexion",
         descripcion="Escribe una carta breve a ti mismo/a en 5 anos."),
    dict(titulo="Mi red de apoyo", tipo="bienestar",
         descripcion="Escribe quienes son las personas en las que mas confias."),
    dict(titulo="Gestion del tiempo", tipo="reflexion",
         descripcion="Planifica las actividades de manana. Como vas a organizarte?"),
]
RESP = {
    'respiracion': ["Me senti mas calmado/a","Fue dificil al principio","Me relaje bastante"],
    'bienestar':   ["Tranquilo, esperanzado, listo","Cansado, ansioso, curioso","Feliz, agradecido, motivado"],
    'gratitud':    ["Mi familia, mis amigos, mi salud","El sol, mis companeros","La musica, el deporte, mi mascota"],
    'meditacion':  ["Al principio me costo pero luego bien","Me relaje completamente","Experiencia nueva y positiva"],
    'reflexion':   ["Lo mejor fue el trabajo en equipo.","Aprendi a organizarme mejor.","Me senti mas seguro/a esta semana."],
}
total_act = 0; total_resp = 0
for curso in todos_cursos:
    if not curso.profesor: continue
    est_ids = list(Inscripcion.objects.filter(curso=curso,activa=True).values_list('estudiante_id',flat=True))
    for j, ad in enumerate(ACTS):
        act, created = Actividad.objects.get_or_create(
            titulo=ad['titulo'], curso=curso,
            defaults={**ad, 'creada_por': curso.profesor, 'semana': j+1, 'activa': True},
        )
        if created: total_act += 1
        existentes_resp = set(RespuestaActividad.objects.filter(actividad=act).values_list('estudiante_id',flat=True))
        resp_batch = []
        for eid in est_ids:
            if eid not in existentes_resp and random.random() < 0.78:
                resp_batch.append(RespuestaActividad(
                    actividad=act, estudiante_id=eid,
                    respuesta=random.choice(RESP.get(act.tipo, ["Participe en la actividad."])),
                ))
                total_resp += 1
        if resp_batch:
            RespuestaActividad.objects.bulk_create(resp_batch, ignore_conflicts=True)
ok(f"{total_act} actividades, {total_resp} respuestas creadas")


titulo("8. Notas del profesor")
NOTAS = [
    "Muestra buena disposicion en clase. Ha mejorado notablemente.",
    "Se ha notado cierta tristeza. Requiere seguimiento cercano.",
    "Excelente desempeno academico y emocional. Ejemplo para sus companeros.",
    "Ha faltado varias clases. Pendiente contactar a los padres.",
    "Se integra bien. Sus registros emocionales muestran tendencia positiva.",
    "Pendiente hablar sobre su bienestar. Registros inconsistentes.",
    "Muestra liderazgo positivo en el aula.",
    "Ha manifestado dificultades en casa. Se brinda acompanamiento.",
    "Participacion activa y propositiva. Muy buenos aportes en grupo.",
    "Se recomienda derivar a orientacion escolar.",
    "Ha superado una situacion dificil con mucha fortaleza.",
    "Buena asistencia y puntualidad. Registros emocionales estables.",
    "Destacado/a por su empatia y solidaridad con los demas.",
    "Necesita refuerzo en habitos de estudio. Se orientara en tutoria.",
]
total_notas = 0
for est in todos_estudiantes:
    insc = Inscripcion.objects.filter(estudiante=est,activa=True).select_related('curso__profesor').first()
    if insc and insc.curso.profesor:
        _, created = NotaProfesor.objects.get_or_create(
            profesor=insc.curso.profesor, estudiante=est,
            defaults={'contenido': random.choice(NOTAS)},
        )
        if created: total_notas += 1
ok(f"{total_notas} notas de seguimiento creadas")


titulo("9. Mensajes directos")
MSG_PE = [
    "Hola {n}, recuerda entregar la actividad de esta semana. Mucho animo!",
    "Hola {n}, he notado emociones dificiles. Estas bien?",
    "Felicitaciones {n}! Tu progreso emocional fue excelente. Sigue asi!",
    "{n}, puedes hablar conmigo cuando necesites apoyo.",
    "{n}, excelente participacion hoy. Se nota tu esfuerzo.",
]
MSG_PAD = [
    "Buenos dias profe, como ha estado mi hijo/a esta semana?",
    "Profesor/a, podriamos coordinar una reunion sobre el avance de mi hijo/a?",
    "Gracias por el seguimiento. Notamos mejoras en casa tambien.",
    "Mi hijo/a ha estado un poco triste en casa. Queria comentarle.",
    "Muchas gracias por todo lo que hace. Los estudiantes la/lo admiran.",
]
total_msgs = 0
for est in todos_estudiantes[:150]:
    insc = Inscripcion.objects.filter(estudiante=est,activa=True).select_related('curso__profesor').first()
    if insc and insc.curso.profesor and random.random() < 0.65:
        _, created = MensajeDirecto.objects.get_or_create(
            remitente=insc.curso.profesor, destinatario=est,
            defaults={
                'contenido': random.choice(MSG_PE).format(n=est.first_name),
                'leido': random.choice([True,False]),
            }
        )
        if created: total_msgs += 1

vistos = set()
for padre in padres_lista:
    if padre.pk in vistos: continue
    vistos.add(padre.pk)
    for v in VinculoPadreHijo.objects.filter(padre=padre,activo=True).select_related('estudiante')[:1]:
        insc = Inscripcion.objects.filter(estudiante=v.estudiante,activa=True).select_related('curso__profesor').first()
        if insc and insc.curso.profesor and random.random() < 0.55:
            _, created = MensajeDirecto.objects.get_or_create(
                remitente=padre, destinatario=insc.curso.profesor,
                defaults={'contenido': random.choice(MSG_PAD),'leido': random.choice([True,False])},
            )
            if created: total_msgs += 1
ok(f"{total_msgs} mensajes directos creados")


titulo("10. Logros")
LOGROS = ['primer_registro','racha_3','explorador','diario_5','racha_7','conectado']
total_logros = 0
existentes_logros = set(Logro.objects.values_list('estudiante_id','clave'))
batch_logros = []
for est in todos_estudiantes:
    for clave in random.sample(LOGROS, k=random.randint(1, len(LOGROS))):
        if (est.pk, clave) not in existentes_logros:
            batch_logros.append(Logro(estudiante=est, clave=clave))
            existentes_logros.add((est.pk, clave))
            total_logros += 1
if batch_logros:
    Logro.objects.bulk_create(batch_logros, ignore_conflicts=True)
ok(f"{total_logros} logros desbloqueados")


titulo("RESUMEN FINAL")
total_est = User.objects.filter(rol=User.ROL_ESTUDIANTE).count()
total_pad = User.objects.filter(rol=User.ROL_PADRE).count()
total_cur = Curso.objects.filter(activo=True).count()
total_ins = Inscripcion.objects.filter(activa=True).count()

print(f"""
  Contrasena de todos los usuarios: {PASS}

  BASE DE DATOS ACTUALIZADA
  ──────────────────────────────────────────────────────
  Cursos activos        : {total_cur}
  Estudiantes totales   : {total_est}
  Padres / Acudientes   : {total_pad}
  Inscripciones activas : {total_ins}

  CURSOS:
  ──────────────────────────────────────────────────────""")
for c in Curso.objects.filter(activo=True).order_by('grado','seccion'):
    n = c.total_estudiantes()
    prof = c.profesor.get_full_name() if c.profesor else 'Sin profesor'
    print(f"    Grado {c.grado:>2}{c.seccion}  |  {n:>3} estudiantes  |  {prof}")
print(f"""
  python manage.py runserver
  http://127.0.0.1:8000/
""")
