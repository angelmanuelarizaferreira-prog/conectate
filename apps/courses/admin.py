from django.contrib import admin
from .models import Curso, Inscripcion

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'grado', 'profesor', 'codigo', 'total_estudiantes', 'activo']
    list_filter = ['activo', 'grado']
    search_fields = ['nombre', 'codigo']

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'curso', 'fecha_inscripcion', 'activa']
    list_filter = ['activa', 'curso']
