from django.db import models
import os


class Cliente(models.Model):
    nombre    = models.CharField(max_length=150, unique=True, help_text='Nombre del cliente o institución')
    ruc       = models.CharField(max_length=20, blank=True, null=True, help_text='RUC o identificación fiscal')
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono  = models.CharField(max_length=30, blank=True, null=True)
    contacto  = models.CharField(max_length=100, blank=True, null=True, help_text='Persona de contacto')
    email     = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


class Equipo(models.Model):

    TIPO_CHOICES = [
        # ── Diagnóstico por imagen ──────────────────────────
        ('rayos_x',          'Rayos X'),
        ('tomografo',        'Tomógrafo (CT)'),
        ('resonancia',       'Resonancia Magnética (RM)'),
        ('ultrasonido',      'Ultrasonido / Ecógrafo'),
        ('mamografo',        'Mamógrafo'),
        ('fluoroscopio',     'Fluoroscopio'),
        ('densitometro',     'Densitómetro óseo'),
        ('arco_c',           'Arco en C'),
        ('angiografo',       'Angiógrafo'),
        ('pet_scan',         'PET / PET-CT'),
        # ── Monitoreo y soporte vital ────────────────────────
        ('monitor',          'Monitor de signos vitales'),
        ('ventilador',       'Ventilador mecánico'),
        ('desfibrilador',    'Desfibrilador / DEA'),
        ('electrocardiografo','Electrocardiógraf (ECG)'),
        ('oximetro',         'Oxímetro de pulso'),
        ('bomba_infusion',   'Bomba de infusión'),
        ('incubadora',       'Incubadora neonatal'),
        # ── Quirúrgico y electrocirugía ──────────────────────
        ('electrobisturi',   'Electrobisturí'),
        ('laser_medico',     'Láser médico'),
        ('arco_quirurgico',  'Arco quirúrgico'),
        # ── Laboratorio ──────────────────────────────────────
        ('analizador',       'Analizador / Autoanalizador'),
        ('centrifuga',       'Centrífuga'),
        ('microscopio',      'Microscopio'),
        ('espectrofotometro','Espectrofotómetro'),
        ('autoclave',        'Autoclave / Esterilizador'),
        # ── Rehabilitación ───────────────────────────────────
        ('ultrasonido_rehab','Ultrasonido terapéutico'),
        ('electroterapia',   'Electroterapia / TENS'),
        ('laser_rehab',      'Láser terapéutico'),
        # ── Odontología ──────────────────────────────────────
        ('rayos_x_dental',   'Rayos X dental'),
        ('unidad_dental',    'Unidad odontológica'),
        # ── Otro ─────────────────────────────────────────────
        ('otro',             'Otro'),
    ]

    codigo            = models.CharField(max_length=50, unique=True)
    nombre            = models.CharField(max_length=100)
    tipo              = models.CharField(
                            max_length=50,
                            choices=TIPO_CHOICES,
                            default='otro',
                            help_text='Categoría del equipo biomédico'
                        )
    tipo_otro         = models.CharField(
                            max_length=100,
                            blank=True,
                            null=True,
                            help_text='Especificar si el tipo es "Otro"'
                        )
    marca             = models.CharField(max_length=50)
    modelo            = models.CharField(max_length=50)
    serie             = models.CharField(max_length=50)
    ubicacion         = models.CharField(max_length=100)
    estado            = models.CharField(max_length=50)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    criticidad        = models.CharField(max_length=20)
    usos_mas          = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Número de usos o mAs acumulados del equipo'
    )
    cliente           = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipos',
        help_text='Cliente o institución propietaria del equipo'
    )
    # ── Tubo de rayos X (opcional) ──────────────────────────
    tubo_modelo       = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Modelo del tubo de rayos X (dejar vacío si no aplica)'
    )
    tubo_serie        = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Número de serie del tubo de rayos X (dejar vacío si no aplica)'
    )

    class Meta:
        verbose_name        = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering            = ['codigo']

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    def tipo_display(self):
        """Devuelve el tipo legible, usando tipo_otro cuando aplica."""
        if self.tipo == 'otro':
            return self.tipo_otro or 'Otro'
        return self.get_tipo_display() or self.tipo


class Tecnico(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Mantenimiento(models.Model):
    TIPO_CHOICES = [
        ('preventivo',  'Preventivo'),
        ('correctivo',  'Correctivo'),
        ('predictivo',  'Predictivo'),
        ('otro',        'Otro'),
    ]

    ATENCION_CHOICES = [
        ('presencial', 'Presencial'),
        ('virtual',    'Virtual'),
    ]

    ETIQUETA_CHOICES = [
        ('bimestral',     'Bimestral'),
        ('trimestral',    'Trimestral'),
        ('cuatrimestral', 'Cuatrimestral'),
        ('semestral',     'Semestral'),
        ('anual',         'Anual'),
        ('otro',          'Otro'),
    ]

    # ── NUEVO: distingue programado vs no programado ──────────────────
    programado  = models.BooleanField(
        default=False,
        help_text=(
            'True = mantenimiento programado (periódico, generado por el sistema). '
            'False = no programado (imprevisto o correctivo puntual).'
        )
    )
    # Enlace entre instancias de una misma serie periódica
    serie_programada = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='serie_hijos',
        help_text='Primer mantenimiento de la serie (null si es el primero)'
    )

    equipo      = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    tipo        = models.CharField(max_length=50, choices=TIPO_CHOICES, default='preventivo')
    tipo_otro   = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Descripción si tipo es "otro"'
    )
    fecha       = models.DateField()
    tipo_atencion = models.CharField(
        max_length=20,
        choices=ATENCION_CHOICES,
        default='presencial',
        help_text='Modalidad de atención'
    )
    problema    = models.TextField(
        blank=True,
        null=True,
        help_text='Problema o asunto reportado'
    )
    solucion    = models.TextField(
        blank=True,
        null=True,
        help_text='Solución aplicada'
    )
    descripcion = models.TextField(blank=True, null=True)  # Mantenido por compatibilidad
    tecnico     = models.ForeignKey(Tecnico, on_delete=models.SET_NULL, null=True)
    estado      = models.CharField(max_length=50)
    costo       = models.FloatField()

    # ── CAMPOS DE PERIODICIDAD ───────────────────────────────
    etiqueta           = models.CharField(
        max_length=20,
        choices=ETIQUETA_CHOICES,
        blank=True,
        null=True,
        help_text='Periodicidad de este mantenimiento'
    )
    etiqueta_otro      = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Descripción si etiqueta es "otro"'
    )
    fecha_proximo      = models.DateField(
        blank=True,
        null=True,
        help_text='Fecha programada para el próximo mantenimiento'
    )
    etiqueta_proximo   = models.CharField(
        max_length=20,
        choices=ETIQUETA_CHOICES,
        blank=True,
        null=True,
        help_text='Periodicidad del próximo mantenimiento'
    )
    etiqueta_proximo_otro = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Descripción si etiqueta_proximo es "otro"'
    )

    # ── Ciudad / lugar del servicio (para cronograma) ─────────────────
    ciudad = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Ciudad o lugar donde se realiza el mantenimiento'
    )

    # ── Código(s) de error ────────────────────────────────────────────
    codigo_error = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=(
            'Código(s) de error reportados por el equipo. '
            'Puede ingresar varios separados por coma. '
            'También se detectan códigos mencionados en problema/solución.'
        )
    )

    class Meta:
        unique_together = (
            'equipo', 'tipo', 'fecha',
            'tecnico', 'estado', 'costo'
        )

    def __str__(self):
        prefijo = '[P]' if self.programado else '[NP]'
        return f"{prefijo} {self.equipo.codigo} — {self.tipo_display()} ({self.fecha})"

    def tipo_display(self):
        if self.tipo == 'otro':
            return self.tipo_otro or 'Otro'
        return self.get_tipo_display() or self.tipo

    def etiqueta_display(self):
        if self.etiqueta == 'otro':
            return self.etiqueta_otro or 'Otro'
        return self.get_etiqueta_display() or '—'

    def etiqueta_proximo_display(self):
        if self.etiqueta_proximo == 'otro':
            return self.etiqueta_proximo_otro or 'Otro'
        return self.get_etiqueta_proximo_display() or '—'

    def codigos_error_all(self):
        """
        Devuelve lista de códigos de error únicos combinando:
        1. El campo codigo_error (explícito).
        2. Códigos detectados en problema/solución mediante regex.
        Patrón: combinaciones alfanuméricas tipo E01, ERR-404, F-23, 0x8A...
        """
        import re
        patron = re.compile(
            r'\b(?:[A-Za-z]{1,4}[-_]?\d{2,6}|\d{2,6}[-_]?[A-Za-z]{1,4}|0x[0-9A-Fa-f]{2,6}|ERR[:\s]?\w+)\b'
        )
        codigos = set()
        if self.codigo_error:
            for c in re.split(r'[,;\s]+', self.codigo_error):
                c = c.strip()
                if c:
                    codigos.add(c.upper())
        for campo in [self.problema or '', self.solucion or '', self.descripcion or '']:
            for match in patron.finditer(campo):
                codigos.add(match.group(0).upper())
        return sorted(codigos)


# ──────────────────────────────────────────────────────────────
#  SUBTAREAS DE MANTENIMIENTO
# ──────────────────────────────────────────────────────────────

class SubtareaPlantilla(models.Model):
    tipo_equipo  = models.CharField(
        max_length=50,
        choices=Equipo.TIPO_CHOICES,
        help_text='Tipo de equipo al que aplica esta subtarea'
    )
    nombre       = models.CharField(max_length=200, help_text='Descripción de la subtarea')
    orden        = models.PositiveSmallIntegerField(default=0, help_text='Orden de aparición')
    activa       = models.BooleanField(default=True, help_text='Desactivar para ocultar sin borrar')

    class Meta:
        verbose_name        = 'Subtarea plantilla'
        verbose_name_plural = 'Subtareas plantilla'
        ordering            = ['tipo_equipo', 'orden', 'nombre']

    def __str__(self):
        tipo_label = dict(Equipo.TIPO_CHOICES).get(self.tipo_equipo, self.tipo_equipo)
        return f"[{tipo_label}] {self.nombre}"


class SubtareaEjecucion(models.Model):
    mantenimiento = models.ForeignKey(
        Mantenimiento,
        on_delete=models.CASCADE,
        related_name='subtareas'
    )
    plantilla     = models.ForeignKey(
        SubtareaPlantilla,
        on_delete=models.CASCADE,
        related_name='ejecuciones'
    )
    completada    = models.BooleanField(default=False)
    nota          = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        help_text='Observación opcional sobre esta subtarea'
    )
    fecha_check   = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Cuándo se marcó como completada'
    )

    class Meta:
        unique_together = ('mantenimiento', 'plantilla')
        ordering        = ['plantilla__orden', 'plantilla__nombre']
        verbose_name        = 'Ejecución de subtarea'
        verbose_name_plural = 'Ejecuciones de subtareas'

    def __str__(self):
        estado = '✔' if self.completada else '○'
        return f"{estado} {self.plantilla.nombre} — Mant. #{self.mantenimiento.id}"


def ruta_documento(instance, filename):
    return f"documentos/mantenimiento_{instance.mantenimiento.id}/{filename}"


class Documento(models.Model):
    TIPO_CHOICES = [
        ('certificado', 'Certificado de calibración'),
        ('orden',       'Orden de trabajo'),
        ('foto',        'Fotografía'),
        ('informe',     'Informe técnico'),
        ('otro',        'Otro'),
    ]

    mantenimiento = models.ForeignKey(
        Mantenimiento,
        on_delete=models.CASCADE,
        related_name='documentos'
    )
    tipo         = models.CharField(max_length=30, choices=TIPO_CHOICES, default='otro')
    nombre       = models.CharField(max_length=150)
    archivo      = models.FileField(upload_to=ruta_documento)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    subido_por   = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def extension(self):
        _, ext = os.path.splitext(self.archivo.name)
        return ext.lower()

    def es_imagen(self):
        return self.extension() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']

    def es_pdf(self):
        return self.extension() == '.pdf'