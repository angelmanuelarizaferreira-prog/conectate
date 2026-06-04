# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'rol', 'activo', 'date_joined']
    list_filter = ['rol', 'activo', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informacion Adicional', {'fields': ('rol', 'foto', 'fecha_nacimiento', 'telefono', 'bio', 'activo')}),
    )
