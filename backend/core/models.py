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
        ('trimestral',    'Trimestral'),
        ('cuatrimestral', 'Cuatrimestral'),
        ('semestral',     'Semestral'),
        ('anual',         'Anual'),
        ('otro',          'Otro'),
    ]

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

    # ── NUEVOS CAMPOS ────────────────────────────────────────
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

    class Meta:
        unique_together = (
            'equipo', 'tipo', 'fecha',
            'tecnico', 'estado', 'costo'
        )

    def __str__(self):
        return f"{self.equipo.codigo} — {self.tipo_display()} ({self.fecha})"

    def tipo_display(self):
        """Devuelve el tipo legible, incluyendo 'otro' personalizado."""
        if self.tipo == 'otro':
            return self.tipo_otro or 'Otro'
        return self.get_tipo_display() or self.tipo

    def etiqueta_display(self):
        """Devuelve la etiqueta legible de este mantenimiento."""
        if self.etiqueta == 'otro':
            return self.etiqueta_otro or 'Otro'
        return self.get_etiqueta_display() or '—'

    def etiqueta_proximo_display(self):
        """Devuelve la etiqueta legible del próximo mantenimiento."""
        if self.etiqueta_proximo == 'otro':
            return self.etiqueta_proximo_otro or 'Otro'
        return self.get_etiqueta_proximo_display() or '—'


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