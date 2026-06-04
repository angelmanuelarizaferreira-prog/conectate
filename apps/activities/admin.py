from django.contrib import admin
from .models import Actividad, RespuestaActividad

@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'curso', 'creada_por', 'activa', 'created_at']
    list_filter = ['tipo', 'activa']

@admin.register(RespuestaActividad)
class RespuestaActividadAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'actividad', 'created_at']
