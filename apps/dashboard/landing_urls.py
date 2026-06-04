from django.urls import path
from . import landing_views

app_name = 'landing'

urlpatterns = [
    path('', landing_views.inicio_view, name='inicio'),
]
