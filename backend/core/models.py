from django.db import models
import os


class Equipo(models.Model):
    codigo            = models.CharField(max_length=50, unique=True)
    nombre            = models.CharField(max_length=100)
    tipo              = models.CharField(max_length=50)
    marca             = models.CharField(max_length=50)
    modelo            = models.CharField(max_length=50)
    serie             = models.CharField(max_length=50)
    ubicacion         = models.CharField(max_length=100)
    estado            = models.CharField(max_length=50)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    criticidad        = models.CharField(max_length=20)

    def __str__(self):
        return self.codigo


class Tecnico(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Mantenimiento(models.Model):
    equipo      = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    tipo        = models.CharField(max_length=50)
    fecha       = models.DateField()
    descripcion = models.TextField()
    tecnico     = models.ForeignKey(Tecnico, on_delete=models.SET_NULL, null=True)
    estado      = models.CharField(max_length=50)
    costo       = models.FloatField()

    class Meta:
        unique_together = (
            'equipo', 'tipo', 'fecha',
            'descripcion', 'tecnico', 'estado', 'costo'
        )

    def __str__(self):
        return f"{self.equipo.codigo} — {self.tipo} ({self.fecha})"


# ─── NUEVO ───────────────────────────────
def ruta_documento(instance, filename):
    """media/documentos/mantenimiento_<id>/<filename>"""
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