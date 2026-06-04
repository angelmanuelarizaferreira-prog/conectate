from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.lista_cursos, name='lista'),
    path('crear/', views.crear_curso, name='crear'),
    path('<int:pk>/', views.detalle_curso, name='detalle'),
    path('<int:pk>/inscribir/', views.inscribir_estudiante, name='inscribir'),
    path('unirse/', views.unirse_con_codigo, name='unirse'),
]
