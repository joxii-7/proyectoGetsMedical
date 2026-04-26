from django.contrib import admin
from .models import Equipo, Tecnico, Mantenimiento, Documento


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display   = ('equipo', 'tipo', 'fecha', 'tecnico', 'estado', 'costo')
    list_filter    = ('estado', 'tipo')
    search_fields  = ('equipo__nombre', 'equipo__codigo', 'tecnico__nombre')
    list_editable  = ('estado',)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'tipo', 'mantenimiento', 'subido_por', 'fecha_subida')
    list_filter   = ('tipo',)
    search_fields = ('nombre', 'subido_por', 'mantenimiento__equipo__nombre')


admin.site.register(Equipo)
admin.site.register(Tecnico)