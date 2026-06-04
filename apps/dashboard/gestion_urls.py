from django.urls import path
from apps.dashboard import gestion_views as views

app_name = 'gestion'

urlpatterns = [
    # Usuarios
    path('usuarios/', views.gestionar_usuarios, name='usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),

    # Cursos
    path('cursos/', views.gestionar_cursos, name='cursos'),
    path('cursos/<int:pk>/editar/', views.editar_curso, name='editar_curso'),
    path('cursos/<int:pk>/eliminar/', views.eliminar_curso, name='eliminar_curso'),
    path('inscripcion/<int:pk>/eliminar/', views.eliminar_inscripcion, name='eliminar_inscripcion'),
    path('inscripcion/agregar/', views.agregar_inscripcion, name='agregar_inscripcion'),

    # Actividades
    path('actividades/', views.gestionar_actividades, name='actividades'),
    path('actividades/<int:pk>/editar/', views.editar_actividad, name='editar_actividad'),
    path('actividades/<int:pk>/eliminar/', views.eliminar_actividad, name='eliminar_actividad'),
]
