from django.contrib import admin
from .models import RegistroEmocional, Alerta

@admin.register(RegistroEmocional)
class RegistroEmocionalAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'fecha', 'emocion', 'puntaje', 'hora_registro']
    list_filter = ['emocion', 'fecha', 'puntaje']
    search_fields = ['estudiante__username', 'estudiante__first_name']
    date_hierarchy = 'fecha'

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'tipo', 'prioridad', 'resuelta', 'fecha_creacion']
    list_filter = ['tipo', 'prioridad', 'resuelta']
    search_fields = ['estudiante__username', 'estudiante__first_name']
