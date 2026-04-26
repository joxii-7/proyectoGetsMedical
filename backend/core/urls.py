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
]