# -*- coding: utf-8 -*-
from django.db import models
from apps.accounts.models import User


GRADO_CHOICES = [
    ('6',  'Grado 6'),
    ('7',  'Grado 7'),
    ('8',  'Grado 8'),
    ('9',  'Grado 9'),
    ('10', 'Grado 10'),
    ('11', 'Grado 11'),
]

SECCION_CHOICES = [
    ('A', 'A'), ('B', 'B'), ('C', 'C'),
    ('D', 'D'), ('E', 'E'),
]


class Curso(models.Model):
    grado   = models.CharField(max_length=5, choices=GRADO_CHOICES, verbose_name='Grado')
    seccion = models.CharField(max_length=5, choices=SECCION_CHOICES, default='A', verbose_name='Sección')
    descripcion = models.TextField(blank=True)
    profesor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cursos_asignados', limit_choices_to={'rol': 'profesor'}
    )
    codigo   = models.CharField(max_length=10, unique=True, blank=True)
    activo   = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering            = ['grado', 'seccion']
        unique_together     = ('grado', 'seccion')

    def __str__(self):
        return self.nombre

    @property
    def nombre(self):
        return f"Grado {self.grado}{self.seccion}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            import random, string
            self.codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def total_estudiantes(self):
        return self.inscripciones.filter(activa=True).count()

    def get_promedio_emocional_hoy(self):
        from datetime import date
        from apps.emotions.models import RegistroEmocional
        estudiantes = self.inscripciones.filter(activa=True).values_list('estudiante_id', flat=True)
        registros = RegistroEmocional.objects.filter(
            estudiante_id__in=estudiantes,
            fecha=date.today()
        )
        if registros.exists():
            return round(sum(r.puntaje for r in registros) / registros.count(), 1)
        return None


class Inscripcion(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inscripciones', limit_choices_to={'rol': 'estudiante'})
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='inscripciones')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'
        unique_together = ['estudiante', 'curso']

    def __str__(self):
        return f"{self.estudiante} → {self.curso}"
