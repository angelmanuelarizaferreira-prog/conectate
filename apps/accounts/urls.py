from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('estudiante/<int:pk>/', views.ver_perfil_estudiante, name='perfil_estudiante'),
    # Padre / Acudiente
    path('padre/',                views.panel_padre,           name='panel_padre'),
    path('padre/hijo/<int:pk>/',  views.hijo_detalle,          name='hijo_detalle'),
    path('padre/vincular/',       views.vincular_hijo,         name='vincular_hijo'),
    path('padre/citaciones/',     views.padre_citaciones,      name='padre_citaciones'),
    path('padre/mensajes/',       views.padre_mensajes,         name='padre_mensajes'),
]
