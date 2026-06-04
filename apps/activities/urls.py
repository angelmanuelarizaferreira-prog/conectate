from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.lista_actividades, name='lista'),
    path('crear/', views.crear_actividad, name='crear'),
    path('<int:pk>/', views.detalle_actividad, name='detalle'),
]
