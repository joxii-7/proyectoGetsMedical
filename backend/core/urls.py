from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.home,                  name='home'),
    path('equipos/',                                views.lista_equipos,         name='lista_equipos'),
    path('equipo/<int:id>/',                        views.detalle_equipo,        name='detalle_equipo'),
    path('mantenimiento/<int:id>/editar/',          views.editar_mantenimiento,  name='editar_mantenimiento'),
    path('mantenimiento/<int:mantenimiento_id>/documento/subir/', views.subir_documento,   name='subir_documento'),
    path('documento/<int:documento_id>/eliminar/',  views.eliminar_documento,    name='eliminar_documento'),
    path('subir-equipos/',                          views.subir_equipos,         name='subir_equipos'),
    path('subir-mantenimientos/',                   views.subir_mantenimientos,  name='subir_mantenimientos'),
    path('alertas/',                                views.alertas,               name='alertas'),
    path('dashboard/',                              views.dashboard,             name='dashboard'),

    # ── Subtareas ──────────────────────────────────────────
    path('mantenimiento/<int:mantenimiento_id>/subtareas/',
         views.subtareas_mantenimiento,
         name='subtareas_mantenimiento'),
    path('subtarea/<int:ejecucion_id>/toggle/',
         views.toggle_subtarea,
         name='toggle_subtarea'),
    path('subtarea/<int:ejecucion_id>/nota/',
         views.nota_subtarea,
         name='nota_subtarea'),

    # ── PDF de mantenimiento individual ────────────────────
    path('mantenimiento/<int:mantenimiento_id>/pdf/',
         views.pdf_mantenimiento,
         name='pdf_mantenimiento'),

    # ── PDF Cronograma de mantenimientos programados ────────
    path('equipo/<int:equipo_id>/cronograma/pdf/',
         views.pdf_cronograma,
         name='pdf_cronograma'),

     path('calendario/', views.calendario, name='calendario')
]