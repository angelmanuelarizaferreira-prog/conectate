# -*- coding: utf-8 -*-
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROL_PROFESOR   = 'profesor'
    ROL_ESTUDIANTE = 'estudiante'
    ROL_PADRE      = 'padre'

    ROL_CHOICES = [
        (ROL_PROFESOR,   'Profesor'),
        (ROL_ESTUDIANTE, 'Estudiante'),
        (ROL_PADRE,      'Padre / Acudiente'),
    ]

    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_ESTUDIANTE)
    foto = models.ImageField(upload_to='fotos_perfil/', blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True, verbose_name='Descripcion')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    @property
    def es_admin(self):
        """Todos los profesores tienen acceso completo de administrador."""
        return self.rol == self.ROL_PROFESOR or self.is_superuser

    @property
    def es_profesor(self):
        return self.rol == self.ROL_PROFESOR

    @property
    def es_estudiante(self):
        return self.rol == self.ROL_ESTUDIANTE

    @property
    def es_padre(self):
        return self.rol == self.ROL_PADRE

    def get_foto_url(self):
        if self.foto:
            return self.foto.url
        return '/static/img/avatar_default.svg'


class VinculoPadreHijo(models.Model):
    """Vincula un padre/acudiente con uno o más estudiantes."""
    padre      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='hijos_vinculados',
        limit_choices_to={'rol': 'padre'},
    )
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='padres_vinculados',
        limit_choices_to={'rol': 'estudiante'},
    )
    relacion   = models.CharField(
        max_length=30, default='padre',
        choices=[
            ('padre',    'Padre'),
            ('madre',    'Madre'),
            ('acudiente','Acudiente'),
            ('tutor',    'Tutor legal'),
        ],
        verbose_name='Relación',
    )
    activo     = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Vínculo Padre-Hijo'
        verbose_name_plural = 'Vínculos Padre-Hijo'
        unique_together     = ('padre', 'estudiante')
        ordering            = ['estudiante__first_name']

    def __str__(self):
        return f"{self.padre.get_full_name()} → {self.estudiante.get_full_name()} ({self.get_relacion_display()})"
