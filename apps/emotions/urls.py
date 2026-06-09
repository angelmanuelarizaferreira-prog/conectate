# -*- coding: utf-8 -*-
from django.urls import path
from . import views, informe_views, bienestar_views, extra_views, nueva_views

app_name = 'emotions'

urlpatterns = [
    path('registrar/',                      views.registrar_emocion,            name='registrar'),
    path('historial/',                      views.historial_propio,             name='historial'),
    path('alertas/',                        views.alertas_view,                 name='alertas'),
    path('alertas/<int:pk>/resolver/',      views.resolver_alerta,              name='resolver_alerta'),
    path('resumen/',                        views.resumen_grupo,                name='resumen_grupo'),
    # Diario
    path('diario/',                         views.diario_lista,                 name='diario_lista'),
    path('diario/nueva/',                   views.diario_nueva,                 name='diario_nueva'),
    path('diario/<int:pk>/',                views.diario_detalle,               name='diario_detalle'),
    path('diario/<int:pk>/editar/',         views.diario_editar,                name='diario_editar'),
    path('diario/<int:pk>/eliminar/',       views.diario_eliminar,              name='diario_eliminar'),
    # Chat IA removido - solo se mantienen los informes PDF para profesores
    # Informes
    path('informe/',                        informe_views.informe_selector,     name='informe_selector'),
    path('informe/<int:curso_id>/',         informe_views.informe_preview,      name='informe_preview'),
    path('informe/<int:curso_id>/pdf/',     informe_views.informe_descargar,    name='informe_descargar'),
    path('informe/<int:curso_id>/excel/',   informe_views.informe_excel,        name='informe_excel'),
    # Bienestar
    path('logros/',                         bienestar_views.logros_view,        name='logros'),
    path('mapa/',                           bienestar_views.mapa_calor_view,    name='mapa_calor'),
    path('capsulas/',                       bienestar_views.capsulas_view,      name='capsulas'),
    # Extras
    path('insights/',                       extra_views.insights_view,          name='insights'),
    path('mensajes/',                       extra_views.mensajes_view,          name='mensajes'),
    path('mensajes/enviar/<int:pk>/',       extra_views.enviar_mensaje,         name='enviar_mensaje'),
    path('mensajes/no-leidos/',             extra_views.mensajes_no_leidos,     name='mensajes_no_leidos'),
    path('foro/<int:curso_id>/',            extra_views.foro_curso,             name='foro'),
    path('foro/apoyo/<int:post_id>/',       extra_views.apoyo_post,             name='apoyo_post'),
    path('rutina/',                         extra_views.rutina_cierre,          name='rutina_cierre'),
    path('semaforo/',                       extra_views.semaforo_grupo,         name='semaforo'),
    path('calendario-grupo/',               extra_views.calendario_grupo,       name='calendario_grupo'),
    # Nuevas funciones
    path('encuestas/',                      nueva_views.encuestas_lista,        name='encuestas_lista'),
    path('encuestas/crear/',               nueva_views.encuesta_crear,          name='encuesta_crear'),
    path('encuestas/<int:pk>/',             nueva_views.encuesta_detalle,       name='encuesta_detalle'),
    path('retos/',                          nueva_views.retos_lista,            name='retos_lista'),
    path('retos/crear/',                    nueva_views.reto_crear,             name='reto_crear'),
    path('notificaciones/',                 nueva_views.notificaciones_view,    name='notificaciones'),
    path('notificaciones/count/',           nueva_views.notificaciones_count,   name='notificaciones_count'),
    path('panel-institucional/',            nueva_views.panel_institucional,    name='panel_institucional'),
    path('exportar/',                       nueva_views.exportar_mis_datos,     name='exportar_datos'),
    path('crisis/',                         nueva_views.pagina_crisis,          name='crisis'),
    path('crisis/verificar/',               nueva_views.verificar_crisis,       name='verificar_crisis'),
    # Notas del profesor
    path('notas/<int:estudiante_pk>/',      extra_views.notas_estudiante,       name='notas_estudiante'),
    path('notas/eliminar/<int:pk>/',        extra_views.nota_eliminar,          name='nota_eliminar'),
    # Citaciones
    path('citaciones/',                     extra_views.citaciones_lista,       name='citaciones_lista'),
    path('citaciones/crear/',               extra_views.citacion_crear,         name='citacion_crear'),
    path('citaciones/<int:pk>/estado/',     extra_views.citacion_cambiar_estado,name='citacion_estado'),
    path('citaciones/pendientes/',          extra_views.citaciones_pendientes_count, name='citaciones_pendientes_count'),
]
