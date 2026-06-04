# -*- coding: utf-8 -*-
from django.db import models
from apps.accounts.models import User
from apps.courses.models import Curso


TIPO_ACTIVIDAD = [
    ('respiracion', 'Ejercicio de Respiracion'),
    ('reflexion', 'Reflexion'),
    ('bienestar', 'Pregunta de Bienestar'),
    ('meditacion', 'Meditacion'),
    ('gratitud', 'Gratitud'),
]

# Iconos Bootstrap Icons en vez de emojis
TIPO_ICONOS = {
    'respiracion': 'bi-wind',
    'reflexion': 'bi-chat-quote-fill',
    'bienestar': 'bi-heart-fill',
    'meditacion': 'bi-person-arms-up',
    'gratitud': 'bi-stars',
}


class Actividad(models.Model):
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_ACTIVIDAD)
    descripcion = models.TextField(verbose_name='Descripcion / Instrucciones')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='actividades', null=True, blank=True)
    creada_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actividades_creadas')
    fecha_limite = models.DateField(null=True, blank=True, verbose_name='Fecha limite (opcional)')
    activa = models.BooleanField(default=True)
    semana = models.PositiveIntegerField(default=1, verbose_name='Semana del curso')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"

    def total_respuestas(self):
        return self.respuestas.count()

    def get_tipo_icono(self):
        return TIPO_ICONOS.get(self.tipo, 'bi-clipboard-check')

    # Mantener compatibilidad con templates que usen get_tipo_emoji
    def get_tipo_emoji(self):
        return self.get_tipo_icono()


class RespuestaActividad(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='respuestas')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='respuestas_actividades')
    respuesta = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Respuesta de Actividad'
        verbose_name_plural = 'Respuestas de Actividades'
        unique_together = ['actividad', 'estudiante']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.estudiante} -> {self.actividad}"
