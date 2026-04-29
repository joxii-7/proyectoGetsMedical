from django.contrib import admin
from django.db import models as dj_models
from .models import Cliente, Equipo, Tecnico, Mantenimiento, Documento


# ──────────────────────────────────────────
#  CLIENTE
# ──────────────────────────────────────────
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'ruc', 'contacto', 'telefono', 'email', 'num_equipos')
    search_fields = ('nombre', 'ruc', 'contacto', 'email')
    ordering      = ('nombre',)

    def num_equipos(self, obj):
        return obj.equipos.count()
    num_equipos.short_description = 'Equipos'


# ──────────────────────────────────────────
#  EQUIPO
# ──────────────────────────────────────────
class TuboRXFilter(admin.SimpleListFilter):
    """Filtra equipos que tienen o no tienen datos de tubo de rayos X."""
    title          = 'Tubo de rayos X'
    parameter_name = 'tiene_tubo'

    def lookups(self, request, model_admin):
        return (
            ('si', 'Con tubo RX registrado'),
            ('no', 'Sin tubo RX'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'si':
            return queryset.exclude(tubo_modelo='').exclude(tubo_modelo__isnull=True)
        if self.value() == 'no':
            return queryset.filter(
                dj_models.Q(tubo_modelo='') | dj_models.Q(tubo_modelo__isnull=True)
            )


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display   = ('codigo', 'nombre', 'tipo_legible', 'marca', 'modelo',
                      'ubicacion', 'cliente_nombre', 'estado', 'criticidad',
                      'tubo_modelo', 'usos_mas')
    list_filter    = ('tipo', 'estado', 'criticidad', 'cliente', TuboRXFilter)
    search_fields  = ('codigo', 'nombre', 'tipo', 'tipo_otro', 'marca', 'modelo',
                      'serie', 'ubicacion', 'cliente__nombre',
                      'tubo_modelo', 'tubo_serie')
    ordering       = ('codigo',)

    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', ('tipo', 'tipo_otro'), 'marca', 'modelo', 'serie')
        }),
        ('Ubicación y Estado', {
            'fields': ('ubicacion', 'estado', 'criticidad', 'fecha_adquisicion')
        }),
        ('Cliente', {
            'fields': ('cliente',)
        }),
        ('Métricas de uso', {
            'fields': ('usos_mas',)
        }),
        ('Tubo de Rayos X', {
            'classes': ('collapse',),
            'description': 'Completar solo si el equipo posee un tubo de rayos X '
                           '(rayos X convencional, tomógrafo, arco en C, etc.). '
                           'Dejar vacío si no aplica.',
            'fields': ('tubo_modelo', 'tubo_serie'),
        }),
    )

    class Media:
        js = ('admin/js/tipo_otro_equipo.js',)

    def tipo_legible(self, obj):
        return obj.tipo_display()
    tipo_legible.short_description = 'Tipo'
    tipo_legible.admin_order_field = 'tipo'

    def cliente_nombre(self, obj):
        return obj.cliente.nombre if obj.cliente else '—'
    cliente_nombre.short_description = 'Cliente'
    cliente_nombre.admin_order_field = 'cliente__nombre'


# ──────────────────────────────────────────
#  TÉCNICO
# ──────────────────────────────────────────
@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display  = ('nombre',)
    search_fields = ('nombre',)


# ──────────────────────────────────────────
#  MANTENIMIENTO
# ──────────────────────────────────────────
@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display   = ('equipo', 'tipo', 'fecha', 'tecnico', 'estado',
                      'costo', 'tipo_atencion', 'cliente_equipo')
    list_filter    = ('estado', 'tipo', 'tipo_atencion', 'equipo__cliente')
    search_fields  = ('equipo__nombre', 'equipo__codigo',
                      'tecnico__nombre', 'equipo__cliente__nombre',
                      'problema', 'solucion')
    list_editable  = ('estado',)
    date_hierarchy = 'fecha'

    def cliente_equipo(self, obj):
        return obj.equipo.cliente.nombre if obj.equipo.cliente else '—'
    cliente_equipo.short_description = 'Cliente'
    cliente_equipo.admin_order_field = 'equipo__cliente__nombre'


# ──────────────────────────────────────────
#  DOCUMENTO
# ──────────────────────────────────────────
@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'tipo', 'mantenimiento', 'subido_por', 'fecha_subida')
    list_filter   = ('tipo',)
    search_fields = ('nombre', 'subido_por', 'mantenimiento__equipo__nombre',
                     'mantenimiento__equipo__cliente__nombre')