import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Equipo, Mantenimiento, Tecnico, Documento
from datetime import date, timedelta
from django.db.models import Count, Q
import json
import os


# ──────────────────────────────────────────
#  HOME
# ──────────────────────────────────────────
def home(request):
    return render(request, 'home.html', {
        'total': Equipo.objects.count(),
        'mantenimientos': Mantenimiento.objects.count(),
    })


# ──────────────────────────────────────────
#  EQUIPOS
# ──────────────────────────────────────────
def lista_equipos(request):
    q = request.GET.get('q', '').strip()
    equipos = Equipo.objects.filter(
        Q(nombre__icontains=q) |
        Q(codigo__icontains=q) |
        Q(tipo__icontains=q) |
        Q(marca__icontains=q) |
        Q(modelo__icontains=q) |
        Q(ubicacion__icontains=q)
    ) if q else Equipo.objects.all()
    return render(request, 'lista.html', {'equipos': equipos})


def detalle_equipo(request, id):
    equipo = get_object_or_404(Equipo, id=id)
    mantenimientos = (
        Mantenimiento.objects
        .filter(equipo=equipo)
        .select_related('tecnico')
        .prefetch_related('documentos')
        .order_by('-fecha')
    )
    return render(request, 'detalle.html', {
        'equipo': equipo,
        'mantenimientos': mantenimientos,
    })


# ──────────────────────────────────────────
#  EDITAR MANTENIMIENTO
# ──────────────────────────────────────────
def editar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)

    if request.method == 'POST':
        mantenimiento.tipo        = request.POST.get('tipo', mantenimiento.tipo)
        mantenimiento.fecha       = request.POST.get('fecha', mantenimiento.fecha)
        mantenimiento.descripcion = request.POST.get('descripcion', mantenimiento.descripcion)
        mantenimiento.estado      = request.POST.get('estado', mantenimiento.estado)
        mantenimiento.costo       = float(request.POST.get('costo') or mantenimiento.costo)

        tecnico_id = request.POST.get('tecnico')
        if tecnico_id:
            mantenimiento.tecnico = get_object_or_404(Tecnico, id=tecnico_id)

        mantenimiento.save()
        messages.success(request, '✔ Mantenimiento actualizado correctamente.')
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    return render(request, 'editar_mantenimiento.html', {
        'm': mantenimiento,
        'tecnicos': Tecnico.objects.all(),
    })


# ──────────────────────────────────────────
#  DOCUMENTOS ADJUNTOS
# ──────────────────────────────────────────
def subir_documento(request, mantenimiento_id):
    mantenimiento = get_object_or_404(Mantenimiento, id=mantenimiento_id)

    if request.method != 'POST':
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    archivo    = request.FILES.get('archivo')
    nombre     = request.POST.get('nombre', '').strip()
    tipo       = request.POST.get('tipo', 'otro')
    subido_por = request.POST.get('subido_por', '').strip()

    if not archivo:
        messages.error(request, '❌ Debes seleccionar un archivo.')
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    if not nombre:
        nombre = archivo.name

    if archivo.size > 10 * 1024 * 1024:
        messages.error(request, '❌ El archivo supera los 10 MB permitidos.')
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    ext = os.path.splitext(archivo.name)[1].lower()
    permitidos = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx', '.xls', '.xlsx']
    if ext not in permitidos:
        messages.error(request, f'❌ Tipo de archivo no permitido ({ext}).')
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    Documento.objects.create(
        mantenimiento=mantenimiento,
        tipo=tipo,
        nombre=nombre,
        archivo=archivo,
        subido_por=subido_por,
    )

    messages.success(request, f'✔ Documento "{nombre}" subido correctamente.')
    return redirect(f'/equipo/{mantenimiento.equipo.id}/')


def eliminar_documento(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    equipo_id = documento.mantenimiento.equipo.id

    if request.method == 'POST':
        if documento.archivo and os.path.isfile(documento.archivo.path):
            os.remove(documento.archivo.path)
        documento.delete()
        messages.success(request, '🗑️ Documento eliminado.')

    return redirect(f'/equipo/{equipo_id}/')


# ──────────────────────────────────────────
#  DASHBOARD
# ──────────────────────────────────────────
def dashboard(request):
    hoy = date.today()

    total_equipos        = Equipo.objects.count()
    total_mantenimientos = Mantenimiento.objects.count()

    proximos_lista = (
        Mantenimiento.objects
        .filter(estado__in=['pendiente', 'proximo', 'Pendiente', 'Proximo'])
        .select_related('equipo', 'tecnico')
        .order_by('fecha')
    )
    proximos = proximos_lista.count()

    vencidos_lista = (
        Mantenimiento.objects
        .filter(fecha__lt=hoy)
        .exclude(estado__iexact='completado')
        .select_related('equipo', 'tecnico')
        .order_by('-fecha')
    )
    vencidos = vencidos_lista.count()

    realizados_lista = (
        Mantenimiento.objects
        .filter(estado__iexact='completado')
        .select_related('equipo', 'tecnico')
        .order_by('-fecha')
    )
    realizados = realizados_lista.count()

    recientes = (
        Mantenimiento.objects
        .select_related('equipo', 'tecnico')
        .order_by('-fecha')[:5]
    )

    tipos  = Equipo.objects.values('tipo').annotate(total=Count('tipo'))
    labels = json.dumps([t['tipo'] for t in tipos])
    data   = json.dumps([t['total'] for t in tipos])

    return render(request, 'dashboard.html', {
        'total_equipos':        total_equipos,
        'total_mantenimientos': total_mantenimientos,
        'proximos':             proximos,
        'proximos_lista':       proximos_lista,
        'vencidos':             vencidos,
        'vencidos_lista':       vencidos_lista,
        'realizados':           realizados,
        'realizados_lista':     realizados_lista,
        'recientes':            recientes,
        'tipos':                tipos,
        'labels':               labels,
        'data':                 data,
    })


# ──────────────────────────────────────────
#  ALERTAS
# ──────────────────────────────────────────
def alertas(request):
    limite = date.today() - timedelta(days=180)
    equipos_alerta = []
    for equipo in Equipo.objects.all():
        ultimo = (
            Mantenimiento.objects
            .filter(equipo=equipo)
            .order_by('-fecha')
            .first()
        )
        if not ultimo or ultimo.fecha < limite:
            equipos_alerta.append({
                'equipo': equipo,
                'ultimo': ultimo.fecha if ultimo else 'Nunca',
            })
    return render(request, 'alertas.html', {'equipos': equipos_alerta})


# ──────────────────────────────────────────
#  SUBIR EQUIPOS
# ──────────────────────────────────────────
def subir_equipos(request):
    if request.method == 'POST':
        archivo = request.FILES['archivo']
        df = pd.read_excel(archivo)
        for _, row in df.iterrows():
            Equipo.objects.update_or_create(
                codigo=row['codigo_equipo'],
                defaults={
                    'nombre':            row['nombre'],
                    'tipo':              row['tipo'],
                    'marca':             row['marca'],
                    'modelo':            row['modelo'],
                    'serie':             row['serie'],
                    'ubicacion':         row['ubicacion'],
                    'estado':            row['estado'],
                    'fecha_adquisicion': row['fecha_adquisicion'],
                    'criticidad':        row['criticidad'],
                }
            )
    return render(request, 'subir.html')


# ──────────────────────────────────────────
#  SUBIR MANTENIMIENTOS
# ──────────────────────────────────────────
def subir_mantenimientos(request):
    context = {
        'tecnicos': Tecnico.objects.all(),
        'equipos':  Equipo.objects.all(),
    }

    if request.method == 'POST' and request.POST.get('form_manual'):
        codigo      = request.POST.get('codigo_equipo')
        tipo        = request.POST.get('tipo')
        fecha       = request.POST.get('fecha')
        descripcion = request.POST.get('descripcion')
        tecnico_id  = request.POST.get('tecnico')
        estado      = request.POST.get('estado')
        costo       = request.POST.get('costo')

        equipo  = Equipo.objects.filter(codigo=codigo).first()
        tecnico = Tecnico.objects.filter(id=tecnico_id).first()

        if not equipo:
            context['mensaje'] = '❌ Equipo no encontrado'
            return render(request, 'subir_mantenimientos.html', context)

        if Mantenimiento.objects.filter(equipo=equipo, fecha=fecha, tipo=tipo).exists():
            context['mensaje'] = '⚠️ Mantenimiento duplicado'
            return render(request, 'subir_mantenimientos.html', context)

        try:
            Mantenimiento.objects.create(
                equipo=equipo, tipo=tipo, fecha=fecha,
                descripcion=descripcion, tecnico=tecnico,
                estado=estado, costo=float(costo or 0),
            )
            context['mensaje'] = '✔ Mantenimiento registrado correctamente'
        except Exception as e:
            context['mensaje'] = f'❌ Error: {e}'

        return render(request, 'subir_mantenimientos.html', context)

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        accion  = request.POST.get('accion')
        df      = pd.read_excel(archivo)
        df.columns = df.columns.str.strip().str.lower()

        if accion == 'preview':
            context['columnas'] = df.columns
            context['preview']  = df.head(10).values.tolist()
            return render(request, 'subir_mantenimientos.html', context)

        if accion == 'guardar':
            creados = duplicados = no_encontrados = 0
            for _, row in df.iterrows():
                equipo = Equipo.objects.filter(codigo=row.get('codigo_equipo')).first()
                if not equipo:
                    no_encontrados += 1
                    continue

                fecha = row.get('fecha')
                if pd.notna(fecha):
                    fecha = pd.to_datetime(fecha).date()

                tipo_excel = str(row.get('tipo_mantenimiento', '')).strip()

                if Mantenimiento.objects.filter(equipo=equipo, fecha=fecha, tipo=tipo_excel).exists():
                    duplicados += 1
                    continue

                nombre_tecnico = str(row.get('tecnico', '')).strip()
                tecnico = None
                if nombre_tecnico:
                    tecnico, _ = Tecnico.objects.get_or_create(nombre=nombre_tecnico)

                Mantenimiento.objects.create(
                    equipo=equipo, tipo=tipo_excel, fecha=fecha,
                    descripcion=str(row.get('descripcion', '')).strip(),
                    tecnico=tecnico,
                    estado=str(row.get('estado', 'pendiente')).strip(),
                    costo=float(row.get('costo', 0)),
                )
                creados += 1

            context['mensaje'] = (
                f'✔ {creados} creados | '
                f'⚠ {duplicados} duplicados | '
                f'❌ {no_encontrados} sin equipo'
            )

    return render(request, 'subir_mantenimientos.html', context)