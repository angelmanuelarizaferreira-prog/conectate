# -*- coding: utf-8 -*-
from datetime import date
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User


EMOCION_CHOICES = [
    ('feliz', 'Feliz'),
    ('tranquilo', 'Tranquilo'),
    ('estresado', 'Estresado'),
    ('triste', 'Triste'),
    ('enojado', 'Enojado'),
]

EMOCION_EMOJIS = {
    'feliz': 'bi-emoji-smile-fill',
    'tranquilo': 'bi-emoji-neutral-fill',
    'estresado': 'bi-emoji-dizzy-fill',
    'triste': 'bi-emoji-frown-fill',
    'enojado': 'bi-emoji-angry-fill',
}

EMOCION_COLORES = {
    'feliz': '#28a745',
    'tranquilo': '#17a2b8',
    'estresado': '#fd7e14',
    'triste': '#6c757d',
    'enojado': '#dc3545',
}

EMOCION_PUNTAJE_BASE = {
    'feliz': 5,
    'tranquilo': 4,
    'estresado': 2,
    'triste': 2,
    'enojado': 1,
}


class RegistroEmocional(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_emocionales')
    fecha = models.DateField()
    emocion = models.CharField(max_length=20, choices=EMOCION_CHOICES)
    puntaje = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Escala emocional (1-5)'
    )
    comentario = models.TextField(blank=True, verbose_name='¿Como te sientes? (opcional)')
    hora_registro = models.TimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro Emocional'
        verbose_name_plural = 'Registros Emocionales'
        unique_together = ['estudiante', 'fecha']
        ordering = ['-fecha', '-hora_registro']

    def __str__(self):
        return f"{self.estudiante} - {self.get_emocion_display()} - {self.fecha}"

    def get_emoji(self):
        return EMOCION_EMOJIS.get(self.emocion, 'bi-question-circle')

    def get_color(self):
        return EMOCION_COLORES.get(self.emocion, '#6c757d')

    def es_negativo(self):
        return self.emocion in ['triste', 'enojado', 'estresado'] or self.puntaje <= 2

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Verificar y crear alertas automaticamente
        verificar_y_crear_alerta(self.estudiante)


class Alerta(models.Model):
    TIPO_NEGATIVO_CONSECUTIVO = 'negativo_consecutivo'
    TIPO_CAMBIO_BRUSCO = 'cambio_brusco'
    TIPO_PUNTAJE_BAJO = 'puntaje_bajo'

    TIPO_CHOICES = [
        (TIPO_NEGATIVO_CONSECUTIVO, 'Emocion negativa varios dias'),
        (TIPO_CAMBIO_BRUSCO, 'Cambio emocional brusco'),
        (TIPO_PUNTAJE_BAJO, 'Puntaje muy bajo'),
    ]

    PRIORIDAD_ALTA = 'alta'
    PRIORIDAD_MEDIA = 'media'

    PRIORIDAD_CHOICES = [
        (PRIORIDAD_ALTA, 'Alta'),
        (PRIORIDAD_MEDIA, 'Media'),
    ]

    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alertas')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default=PRIORIDAD_MEDIA)
    mensaje = models.TextField()
    resuelta = models.BooleanField(default=False)
    nota_resolucion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas_resueltas'
    )

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Alerta: {self.estudiante} - {self.get_tipo_display()}"


class NotaProfesor(models.Model):
    """Nota privada que un profesor escribe sobre un estudiante, organizada por fecha."""
    TIPO_CHOICES = [
        ('observacion',  'Observacion'),
        ('alerta',       'Alerta'),
        ('logro',        'Logro'),
        ('seguimiento',  'Seguimiento'),
    ]
    profesor   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_escritas',
                                   limit_choices_to={'rol': 'profesor'})
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_recibidas',
                                   limit_choices_to={'rol': 'estudiante'})
    contenido  = models.TextField(verbose_name='Nota')
    fecha      = models.DateField(verbose_name='Fecha de la nota', default=date.today)
    tipo       = models.CharField(max_length=20, choices=TIPO_CHOICES, default='observacion')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name         = 'Nota del Profesor'
        verbose_name_plural  = 'Notas del Profesor'
        ordering             = ['-fecha', '-created_at']
        unique_together      = []   # allow multiple notes per student per day

    def __str__(self):
        return f"Nota de {self.profesor} sobre {self.estudiante} ({self.fecha:%d/%m/%Y})"

    def get_tipo_color(self):
        return {
            'observacion': 'var(--accent)',
            'alerta':      '#e0284f',
            'logro':       '#00b87a',
            'seguimiento': '#f5b800',
        }.get(self.tipo, 'var(--muted)')

    def get_tipo_icon(self):
        return {
            'observacion': 'bi-journal-text',
            'alerta':      'bi-exclamation-triangle-fill',
            'logro':       'bi-trophy-fill',
            'seguimiento': 'bi-eye-fill',
        }.get(self.tipo, 'bi-journal-text')


class MetaSemanal(models.Model):
    """Meta emocional semanal que el estudiante se pone."""
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='metas_semanales')
    semana_inicio = models.DateField()  # Lunes de la semana
    texto = models.CharField(max_length=200, verbose_name='Mi meta esta semana')
    cumplida = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Meta Semanal'
        verbose_name_plural = 'Metas Semanales'
        unique_together = ['estudiante', 'semana_inicio']
        ordering = ['-semana_inicio']

    def __str__(self):
        return f"{self.estudiante} — Semana {self.semana_inicio}"


def verificar_y_crear_alerta(estudiante):
    """Analiza los ultimos registros y genera alertas si es necesario."""
    from datetime import date, timedelta

    hoy = date.today()
    DIAS = 3  # dias consecutivos negativos para alerta

    # Obtener los ultimos DIAS registros
    registros = RegistroEmocional.objects.filter(
        estudiante=estudiante
    ).order_by('-fecha')[:DIAS]

    if len(registros) < DIAS:
        return

    # Alerta por emociones negativas consecutivas
    todos_negativos = all(r.es_negativo() for r in registros)
    if todos_negativos:
        ya_existe = Alerta.objects.filter(
            estudiante=estudiante,
            tipo=Alerta.TIPO_NEGATIVO_CONSECUTIVO,
            resuelta=False
        ).exists()
        if not ya_existe:
            emociones_str = ', '.join([r.get_emocion_display() for r in registros])
            Alerta.objects.create(
                estudiante=estudiante,
                tipo=Alerta.TIPO_NEGATIVO_CONSECUTIVO,
                prioridad=Alerta.PRIORIDAD_ALTA,
                mensaje=f"{estudiante.get_full_name()} ha reportado emociones negativas durante {DIAS} dias consecutivos: {emociones_str}."
            )

    # Alerta por puntaje muy bajo (1)
    ultimo = registros[0]
    if ultimo.puntaje == 1:
        ya_existe = Alerta.objects.filter(
            estudiante=estudiante,
            tipo=Alerta.TIPO_PUNTAJE_BAJO,
            resuelta=False,
            fecha_creacion__date=hoy
        ).exists()
        if not ya_existe:
            Alerta.objects.create(
                estudiante=estudiante,
                tipo=Alerta.TIPO_PUNTAJE_BAJO,
                prioridad=Alerta.PRIORIDAD_ALTA,
                mensaje=f"{estudiante.get_full_name()} reporto un puntaje emocional de 1/5 hoy ({ultimo.get_emocion_display()}). Requiere atencion."
            )

    # Alerta por cambio brusco (diferencia >= 3 puntos entre hoy y ayer)
    if len(registros) >= 2:
        diferencia = abs(registros[0].puntaje - registros[1].puntaje)
        if diferencia >= 3:
            ya_existe = Alerta.objects.filter(
                estudiante=estudiante,
                tipo=Alerta.TIPO_CAMBIO_BRUSCO,
                resuelta=False,
                fecha_creacion__date=hoy
            ).exists()
            if not ya_existe:
                Alerta.objects.create(
                    estudiante=estudiante,
                    tipo=Alerta.TIPO_CAMBIO_BRUSCO,
                    prioridad=Alerta.PRIORIDAD_MEDIA,
                    mensaje=f"{estudiante.get_full_name()} tuvo un cambio emocional brusco: de {registros[1].puntaje}/5 a {registros[0].puntaje}/5."
                )


class EntradaDiario(models.Model):
    """Diario personal del estudiante — entradas privadas."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('guardado', 'Guardado'),
    ]

    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='entradas_diario'
    )
    titulo = models.CharField(max_length=150, verbose_name='Titulo', blank=True)
    contenido = models.TextField(verbose_name='Contenido')
    emocion_del_dia = models.CharField(
        max_length=20, choices=EMOCION_CHOICES, blank=True,
        verbose_name='Como me siento al escribir esto'
    )
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='guardado')
    es_privado = models.BooleanField(default=True, verbose_name='Solo yo puedo verlo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrada de Diario'
        verbose_name_plural = 'Entradas de Diario'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.estudiante} - {self.titulo or 'Sin titulo'} ({self.created_at:%d/%m/%Y})"

    def get_emoji(self):
        return EMOCION_EMOJIS.get(self.emocion_del_dia, 'bi-pencil-square')

    def get_resumen(self):
        """Primeras 120 letras del contenido."""
        return self.contenido[:120] + ('...' if len(self.contenido) > 120 else '')


# ─── CHAT CON IA ──────────────────────────────────────────────────────────────

class SesionChat(models.Model):
    """Una sesion de conversacion entre un estudiante y la IA."""
    estudiante = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='sesiones_chat'
    )
    titulo = models.CharField(max_length=120, blank=True, verbose_name='Titulo de la sesion')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sesion de Chat'
        verbose_name_plural = 'Sesiones de Chat'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat de {self.estudiante} - {self.created_at:%d/%m/%Y}"

    def get_titulo(self):
        return self.titulo or f"Conversacion del {self.created_at:%d/%m/%Y}"

    def ultimo_mensaje(self):
        return self.mensajes.order_by('-created_at').first()


class MensajeChat(models.Model):
    """Un mensaje dentro de una sesion de chat."""
    ROL_USER = 'user'
    ROL_ASSISTANT = 'assistant'
    ROL_CHOICES = [
        (ROL_USER, 'Estudiante'),
        (ROL_ASSISTANT, 'Asistente IA'),
    ]

    sesion = models.ForeignKey(SesionChat, on_delete=models.CASCADE, related_name='mensajes')
    rol = models.CharField(max_length=10, choices=ROL_CHOICES)
    contenido = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de Chat'
        verbose_name_plural = 'Mensajes de Chat'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.rol}] {self.contenido[:60]}"


# ─── LOGROS ───────────────────────────────────────────────────────────────────

LOGROS_CATALOGO = {
    'primer_registro':    {'nombre': 'Primer Paso',       'desc': 'Registraste tu primera emocion',           'emoji': 'bi-flower1', 'xp': 10},
    'racha_3':            {'nombre': 'Tres en Raya',       'desc': '3 dias consecutivos registrando',          'emoji': 'bi-fire', 'xp': 20},
    'racha_7':            {'nombre': 'Semana Completa',    'desc': '7 dias seguidos sin fallar',               'emoji': 'bi-lightning-charge-fill', 'xp': 50},
    'racha_30':           {'nombre': 'Mes de Hierro',      'desc': '30 dias consecutivos registrando',         'emoji': 'bi-gem', 'xp': 200},
    'diario_5':           {'nombre': 'Escritor Novato',    'desc': '5 entradas en tu diario',                  'emoji': 'bi-journal-bookmark-fill', 'xp': 30},
    'diario_20':          {'nombre': 'Escritor Prolijo',   'desc': '20 entradas en tu diario',                 'emoji': 'bi-book-fill', 'xp': 80},
    'meta_cumplida':      {'nombre': 'Promesa Cumplida',   'desc': 'Cumpliste tu primera meta semanal',        'emoji': 'bi-bullseye', 'xp': 40},
    'metas_5':            {'nombre': 'Meta Master',        'desc': '5 metas semanales cumplidas',              'emoji': 'bi-trophy-fill', 'xp': 100},
    'explorador':         {'nombre': 'Explorador',         'desc': 'Registraste las 5 emociones distintas',    'emoji': 'bi-compass-fill', 'xp': 35},
    'actividad_5':        {'nombre': 'Participante',       'desc': 'Completaste 5 actividades',                'emoji': 'bi-star-fill', 'xp': 45},
    'bienestar_alto':     {'nombre': 'En Buena Onda',      'desc': 'Promedio de 4.5 o mas en una semana',      'emoji': 'bi-emoji-smile-fill', 'xp': 60},
    'registros_30':       {'nombre': 'Constante',          'desc': '30 registros en total',                    'emoji': 'bi-calendar3', 'xp': 70},
    'registros_100':      {'nombre': 'Centurion',          'desc': '100 registros en total',                   'emoji': 'bi-star-fill', 'xp': 150},
}


class Logro(models.Model):
    """Logro desbloqueado por un estudiante."""
    estudiante   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logros')
    clave        = models.CharField(max_length=40)
    desbloqueado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['estudiante', 'clave']
        ordering = ['-desbloqueado']

    def info(self):
        return LOGROS_CATALOGO.get(self.clave, {})

    def __str__(self):
        return f"{self.estudiante} — {self.clave}"


def verificar_logros(estudiante):
    """Verifica y otorga logros pendientes a un estudiante. Retorna lista de logros nuevos."""
    from datetime import date, timedelta
    nuevos = []

    def otorgar(clave):
        obj, created = Logro.objects.get_or_create(estudiante=estudiante, clave=clave)
        if created:
            nuevos.append(clave)

    registros = RegistroEmocional.objects.filter(estudiante=estudiante)
    total_regs = registros.count()
    hoy = date.today()

    # Primer registro
    if total_regs >= 1:
        otorgar('primer_registro')

    # Rachas
    racha = 0
    dia = hoy
    while registros.filter(fecha=dia).exists():
        racha += 1
        dia -= timedelta(days=1)
        if racha > 31: break
    if racha >= 3:  otorgar('racha_3')
    if racha >= 7:  otorgar('racha_7')
    if racha >= 30: otorgar('racha_30')

    # Total registros
    if total_regs >= 30:  otorgar('registros_30')
    if total_regs >= 100: otorgar('registros_100')

    # Explorador: las 5 emociones
    emociones_usadas = set(registros.values_list('emocion', flat=True).distinct())
    if len(emociones_usadas) >= 5:
        otorgar('explorador')

    # Bienestar alto: promedio semana >= 4.5
    semana_regs = list(registros.filter(fecha__gte=hoy - timedelta(days=6)).values_list('puntaje', flat=True))
    if semana_regs and sum(semana_regs) / len(semana_regs) >= 4.5:
        otorgar('bienestar_alto')

    # Diario (EntradaDiario está definida en este mismo módulo, no hay que importarla)
    total_diario = EntradaDiario.objects.filter(estudiante=estudiante).count()
    if total_diario >= 5:  otorgar('diario_5')
    if total_diario >= 20: otorgar('diario_20')

    # Metas
    metas_cumplidas = MetaSemanal.objects.filter(estudiante=estudiante, cumplida=True).count()
    if metas_cumplidas >= 1: otorgar('meta_cumplida')
    if metas_cumplidas >= 5: otorgar('metas_5')

    # Actividades
    from apps.activities.models import RespuestaActividad
    total_act = RespuestaActividad.objects.filter(estudiante=estudiante).count()
    if total_act >= 5: otorgar('actividad_5')

    return nuevos


# ─── MENSAJES DIRECTOS PROFESOR → ESTUDIANTE ─────────────────────────────────

class MensajeDirecto(models.Model):
    remitente   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    destinatario= models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    contenido   = models.TextField()
    leido       = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.remitente} -> {self.destinatario}: {self.contenido[:40]}"


# ─── FORO ANONIMO POR CURSO ──────────────────────────────────────────────────

class PostForo(models.Model):
    curso      = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, related_name='posts_foro')
    autor      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts_foro')
    contenido  = models.TextField(max_length=500)
    anonimo    = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    apoyos     = models.ManyToManyField(User, blank=True, related_name='posts_apoyados')

    class Meta:
        ordering = ['-created_at']

    def total_apoyos(self):
        return self.apoyos.count()

    def nombre_mostrar(self):
        if self.anonimo:
            return 'Estudiante anonimo'
        return self.autor.get_full_name()


# ─── RUTINA DE CIERRE DEL DIA ────────────────────────────────────────────────

class RutinaCierre(models.Model):
    estudiante  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rutinas_cierre')
    fecha       = models.DateField()
    salio_bien  = models.TextField(verbose_name='Que salio bien hoy')
    fue_dificil = models.TextField(blank=True, verbose_name='Que fue dificil')
    manana      = models.TextField(blank=True, verbose_name='Que necesito manana')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['estudiante', 'fecha']
        ordering = ['-fecha']

    def __str__(self):
        return f"Cierre {self.estudiante} - {self.fecha}"


# ─── ENCUESTAS DE BIENESTAR ──────────────────────────────────────────────────

class Encuesta(models.Model):
    TIPO_CHOICES = [
        ('escala', 'Escala 1-5'),
        ('opciones', 'Opciones multiple'),
        ('texto', 'Respuesta libre'),
    ]
    titulo      = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    tipo        = models.CharField(max_length=10, choices=TIPO_CHOICES, default='escala')
    opciones    = models.JSONField(blank=True, null=True)  # para tipo opciones
    curso       = models.ForeignKey('courses.Curso', null=True, blank=True, on_delete=models.SET_NULL, related_name='encuestas')
    creada_por  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='encuestas_creadas')
    activa      = models.BooleanField(default=True)
    anonima     = models.BooleanField(default=True)
    fecha_limite= models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.titulo

    def total_respuestas(self):
        return self.respuestas_encuesta.count()


class RespuestaEncuesta(models.Model):
    encuesta    = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='respuestas_encuesta')
    estudiante  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='respuestas_encuesta')
    valor_escala= models.IntegerField(null=True, blank=True)
    valor_opcion= models.CharField(max_length=100, blank=True)
    valor_texto = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['encuesta', 'estudiante']
        ordering = ['-created_at']


# ─── RETOS GRUPALES ──────────────────────────────────────────────────────────

class RetoGrupal(models.Model):
    curso       = models.ForeignKey('courses.Curso', on_delete=models.SET_NULL, null=True, blank=True, related_name='retos')
    titulo      = models.CharField(max_length=120)
    descripcion = models.TextField()
    creado_por  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='retos_creados')
    fecha_inicio= models.DateField()
    fecha_fin   = models.DateField()
    activo      = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.titulo} — {self.curso.nombre if self.curso else 'Todos los grados'}"

    def progreso(self):
        from datetime import date
        if self.curso:
            total = self.curso.inscripciones.filter(activa=True).count()
            if not total:
                return 0, 0, 0
            participantes = RegistroEmocional.objects.filter(
                estudiante__inscripciones__curso=self.curso,
                fecha__range=[self.fecha_inicio, self.fecha_fin],
            ).values('estudiante').distinct().count()
        else:
            from apps.courses.models import Inscripcion
            total = Inscripcion.objects.filter(activa=True).values('estudiante').distinct().count()
            if not total:
                return 0, 0, 0
            participantes = RegistroEmocional.objects.filter(
                fecha__range=[self.fecha_inicio, self.fecha_fin],
            ).values('estudiante').distinct().count()
        pct = round(participantes / total * 100)
        return participantes, total, pct


# ─── NOTIFICACIONES INTERNAS ─────────────────────────────────────────────────

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('logro',       'Logro desbloqueado'),
        ('mensaje',     'Nuevo mensaje'),
        ('encuesta',    'Encuesta pendiente'),
        ('reto',        'Nuevo reto'),
        ('alerta',      'Alerta emocional'),
        ('sistema',     'Sistema'),
        ('citacion',    'Citación'),
    ]
    usuario    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo       = models.CharField(max_length=15, choices=TIPO_CHOICES)
    titulo     = models.CharField(max_length=120)
    cuerpo     = models.TextField(blank=True)
    url        = models.CharField(max_length=200, blank=True)
    leida      = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.tipo}] {self.usuario} — {self.titulo}"


def crear_notificacion(usuario, tipo, titulo, cuerpo='', url=''):
    return Notificacion.objects.create(
        usuario=usuario, tipo=tipo,
        titulo=titulo, cuerpo=cuerpo, url=url,
    )


# ─── CITACIONES ──────────────────────────────────────────────────────────────

class Citacion(models.Model):
    """Convocatoria oficial de un profesor a un estudiante (ej: psicología)."""
    ESTADO_CHOICES = [
        ('pendiente',  'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada',  'Cancelada'),
        ('completada', 'Completada'),
    ]
    LUGAR_CHOICES = [
        ('psicologia',   'Oficina de Psicología'),
        ('coordinacion', 'Coordinación'),
        ('salon',        'Salón del profesor'),
        ('otro',         'Otro lugar'),
    ]

    profesor    = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='citaciones_enviadas',
                                    limit_choices_to={'rol': 'profesor'})
    estudiante  = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='citaciones_recibidas',
                                    limit_choices_to={'rol': 'estudiante'})
    fecha       = models.DateField(verbose_name='Fecha de la cita')
    hora        = models.TimeField(verbose_name='Hora de la cita')
    lugar       = models.CharField(max_length=20, choices=LUGAR_CHOICES, default='psicologia')
    lugar_otro  = models.CharField(max_length=100, blank=True, verbose_name='Especifica el lugar')
    motivo      = models.TextField(verbose_name='Motivo de la citación', max_length=600)
    es_urgente  = models.BooleanField(default=False, verbose_name='Urgente')
    estado      = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='pendiente')
    notas_prof  = models.TextField(blank=True, verbose_name='Notas internas del profesor')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name         = 'Citación'
        verbose_name_plural  = 'Citaciones'
        ordering             = ['fecha', 'hora']

    def __str__(self):
        return f"Cita {self.estudiante.get_full_name()} — {self.fecha} {self.hora:%H:%M}"

    def get_lugar_display_full(self):
        if self.lugar == 'otro' and self.lugar_otro:
            return self.lugar_otro
        return dict(self.LUGAR_CHOICES).get(self.lugar, self.lugar)

    def esta_proxima(self):
        from datetime import datetime as dt
        ahora = dt.now()
        cita_dt = dt.combine(self.fecha, self.hora)
        delta = cita_dt - ahora
        return 0 < delta.total_seconds() < 86400  # próxima en 24h

