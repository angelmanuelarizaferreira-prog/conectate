#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script auxiliar para ejecutar setup_datos.py correctamente.

USO:
    python run_setup.py

Esto evita el error de sintaxis que ocurre al hacer:
    python manage.py shell < setup_datos.py
"""
import os
import sys

# Agregar el directorio actual al path para que Django lo encuentre
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conectate.settings')

with open('setup_datos.py', encoding='utf-8') as f:
    exec(f.read())
