from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.emotions import extra_views as _ev

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/widget/contactos/',         _ev.chat_widget_contactos,   name='chat_widget_contactos'),
    path('chat/widget/conversacion/<int:pk>/', _ev.chat_widget_conversacion, name='chat_widget_conversacion'),
    path('chat/widget/enviar/<int:pk>/',   _ev.chat_widget_enviar,      name='chat_widget_enviar'),
    path('', include('apps.dashboard.landing_urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('emotions/', include('apps.emotions.urls')),
    path('activities/', include('apps.activities.urls')),
    path('courses/', include('apps.courses.urls')),
    path('gestion/', include('apps.dashboard.gestion_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
