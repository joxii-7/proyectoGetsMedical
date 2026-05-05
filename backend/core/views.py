import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from .models import Cliente, Equipo, Mantenimiento, Tecnico, Documento
from datetime import date, timedelta
from django.db.models import Count, Q
import json
import os
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta   # pip install python-dateutil
import io
#
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import SubtareaPlantilla, SubtareaEjecucion
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
# ──────────────────────────────────────────────────────────────────
#  CATÁLOGO DE SUBTAREAS POR DEFECTO
#  Se pre-carga si no hay plantillas en la BD para ese tipo de equipo.
#  Puedes editarlas desde el admin de Django.
# ──────────────────────────────────────────────────────────────────
 

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
    q          = request.GET.get('q', '').strip()
    cliente_id = request.GET.get('cliente', '').strip()

    equipos = Equipo.objects.select_related('cliente').all()

    if q:
        equipos = equipos.filter(
            Q(nombre__icontains=q) |
            Q(codigo__icontains=q) |
            Q(tipo__icontains=q) |
            Q(tipo_otro__icontains=q) |
            Q(marca__icontains=q) |
            Q(modelo__icontains=q) |
            Q(ubicacion__icontains=q) |
            Q(cliente__nombre__icontains=q)
        )

    if cliente_id:
        equipos = equipos.filter(cliente__id=cliente_id)

    clientes = Cliente.objects.order_by('nombre')

    return render(request, 'lista.html', {
        'equipos':     equipos,
        'clientes':    clientes,
        'cliente_sel': cliente_id,
    })


def detalle_equipo(request, id):
    import re
    equipo = get_object_or_404(Equipo, id=id)

    # ── Filtros del historial ─────────────────────────────────────────
    filtro_prog  = request.GET.get('programado', '')   # 'true', 'false', ''
    filtro_error = request.GET.get('cod_error', '').strip()

    mantenimientos = (
        Mantenimiento.objects
        .filter(equipo=equipo)
        .select_related('tecnico')
        .prefetch_related('documentos')
        .order_by('-fecha')
    )

    if filtro_prog == 'true':
        mantenimientos = mantenimientos.filter(programado=True)
    elif filtro_prog == 'false':
        mantenimientos = mantenimientos.filter(programado=False)

    if filtro_error:
        term = filtro_error.upper()
        mantenimientos = mantenimientos.filter(
            Q(codigo_error__icontains=filtro_error) |
            Q(problema__icontains=filtro_error) |
            Q(solucion__icontains=filtro_error) |
            Q(descripcion__icontains=filtro_error)
        )

    return render(request, 'detalle.html', {
        'equipo':         equipo,
        'mantenimientos': mantenimientos,
        'programados':    Mantenimiento.objects.filter(equipo=equipo, programado=True).order_by('fecha'),
        'filtro_prog':    filtro_prog,
        'filtro_error':   filtro_error,
    })


# ──────────────────────────────────────────
#  EDITAR MANTENIMIENTO
# ──────────────────────────────────────────
def editar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)

    if request.method == 'POST':
        mantenimiento.tipo          = request.POST.get('tipo', mantenimiento.tipo)
        mantenimiento.tipo_otro     = request.POST.get('tipo_otro', '').strip() or None
        mantenimiento.fecha         = request.POST.get('fecha', mantenimiento.fecha)
        mantenimiento.tipo_atencion = request.POST.get('tipo_atencion', 'presencial')
        mantenimiento.problema      = request.POST.get('problema', '').strip() or None
        mantenimiento.solucion      = request.POST.get('solucion', '').strip() or None
        mantenimiento.descripcion   = request.POST.get('descripcion', '').strip() or None
        mantenimiento.estado        = request.POST.get('estado', mantenimiento.estado)
        mantenimiento.codigo_error  = request.POST.get('codigo_error', '').strip() or None

        # Etiqueta de este mantenimiento
        mantenimiento.etiqueta      = request.POST.get('etiqueta') or None
        mantenimiento.etiqueta_otro = request.POST.get('etiqueta_otro', '').strip() or None

        # Próximo mantenimiento
        fecha_prox = request.POST.get('fecha_proximo', '').strip()
        mantenimiento.fecha_proximo         = fecha_prox or None
        mantenimiento.etiqueta_proximo      = request.POST.get('etiqueta_proximo') or None
        mantenimiento.etiqueta_proximo_otro = request.POST.get('etiqueta_proximo_otro', '').strip() or None

        # usos/mAs del equipo
        usos_mas = request.POST.get('usos_mas', '').strip()
        if usos_mas:
            mantenimiento.equipo.usos_mas = int(usos_mas)
            mantenimiento.equipo.save(update_fields=['usos_mas'])

        tecnico_id = request.POST.get('tecnico')
        if tecnico_id:
            mantenimiento.tecnico = get_object_or_404(Tecnico, id=tecnico_id)

        mantenimiento.save()
        messages.success(request, '✔ Mantenimiento actualizado correctamente.')
        return redirect(f'/equipo/{mantenimiento.equipo.id}/')

    return render(request, 'editar_mantenimiento.html', {
        'm':       mantenimiento,
        'tecnicos': Tecnico.objects.all(),
        'etiqueta_choices': Mantenimiento.ETIQUETA_CHOICES,
        'tipo_choices': Mantenimiento.TIPO_CHOICES,
        'atencion_choices': Mantenimiento.ATENCION_CHOICES,
    })


# ──────────────────────────────────────────
#  DOCUMENTOS
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
        tipo=tipo, nombre=nombre,
        archivo=archivo, subido_por=subido_por,
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

    
    todos_mantenimientos_mes = (
        Mantenimiento.objects
        .select_related('equipo', 'tecnico')
        .order_by('fecha')
    )

    tipos_raw = Equipo.objects.values('tipo').annotate(total=Count('tipo'))
    tipo_map = dict(Equipo.TIPO_CHOICES)

    tipos = [
        {
            'tipo':  tipo_map.get(t['tipo'], t['tipo']),
            'total': t['total'],
        }
        for t in tipos_raw
    ]

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
        'todos_mantenimientos_mes': todos_mantenimientos_mes,

        'tipos':  tipos,
        'labels': labels,
        'data':   data,
    })


# ──────────────────────────────────────────
#  ALERTAS  ← BUG CORREGIDO
# ──────────────────────────────────────────
def alertas(request):
    limite = date.today() - timedelta(days=180)
    equipos_alerta = []

    for equipo in Equipo.objects.all():
        # ✅ FIX: solo cuenta mantenimientos COMPLETADOS para calcular cuándo
        # fue el último real. Un mantenimiento pendiente no reinicia el reloj.
        ultimo_completado = (
            Mantenimiento.objects
            .filter(equipo=equipo, estado__iexact='completado')
            .order_by('-fecha')
            .first()
        )

        # El equipo entra en alerta si nunca tuvo un completado,
        # o si el último completado supera los 180 días.
        if not ultimo_completado or ultimo_completado.fecha < limite:

            # Buscar si hay un próximo mantenimiento programado
            proximo_programado = (
                Mantenimiento.objects
                .filter(equipo=equipo, fecha_proximo__isnull=False)
                .order_by('-fecha')
                .first()
            )

            equipos_alerta.append({
                'equipo':            equipo,
                'ultimo':            ultimo_completado.fecha if ultimo_completado else 'Nunca',
                'dias_sin_mant':     (date.today() - ultimo_completado.fecha).days
                                     if ultimo_completado else None,
                'proximo_fecha':     proximo_programado.fecha_proximo
                                     if proximo_programado else None,
                'proximo_etiqueta':  proximo_programado.etiqueta_proximo_display()
                                     if proximo_programado else None,
            })

    # Ordenar: primero los que no tienen próximo programado, luego por último mantenimiento
    equipos_alerta.sort(key=lambda x: (
        x['proximo_fecha'] is not None,   # sin fecha programada primero
        x['ultimo'] if x['ultimo'] != 'Nunca' else date.min
    ))

    return render(request, 'alertas.html', {'equipos': equipos_alerta})


# ──────────────────────────────────────────
#  SUBIR EQUIPOS
# ──────────────────────────────────────────

# Tabla de normalización: texto libre del Excel → valor interno del choice
_TIPO_NORMALIZAR = {
    # Rayos X
    'rx': 'rayos_x', 'r.x': 'rayos_x', 'rayx': 'rayos_x',
    'rayos x': 'rayos_x', 'rayos-x': 'rayos_x', 'radiografia': 'rayos_x',
    'radiografía': 'rayos_x', 'rx general': 'rayos_x',
    # Tomógrafo
    'ct': 'tomografo', 'tc': 'tomografo', 'tomografo': 'tomografo',
    'tomógrafo': 'tomografo', 'tac': 'tomografo', 'scanner': 'tomografo',
    'tomografia': 'tomografo', 'tomografía': 'tomografo',
    # RM
    'rm': 'resonancia', 'mri': 'resonancia', 'resonancia': 'resonancia',
    'resonancia magnetica': 'resonancia', 'resonancia magnética': 'resonancia',
    # Ultrasonido
    'us': 'ultrasonido', 'eco': 'ultrasonido', 'ecografo': 'ultrasonido',
    'ecógrafo': 'ultrasonido', 'ultrasonido': 'ultrasonido',
    'ultrasonografia': 'ultrasonido', 'ultrasonografía': 'ultrasonido',
    # Mamógrafo
    'mamografo': 'mamografo', 'mamógrafo': 'mamografo', 'mamografia': 'mamografo',
    'mamografía': 'mamografo',
    # Fluoroscopio
    'fluoroscopio': 'fluoroscopio', 'fluoroscopia': 'fluoroscopio',
    # Densitómetro
    'densitometro': 'densitometro', 'densitómetro': 'densitometro',
    'densitometria': 'densitometro', 'dexa': 'densitometro',
    # Arco en C
    'arco c': 'arco_c', 'arco en c': 'arco_c', 'arco-c': 'arco_c',
    'c-arm': 'arco_c', 'c arm': 'arco_c',
    # Angiógrafo
    'angiografo': 'angiografo', 'angiógrafo': 'angiografo',
    'angiografia': 'angiografo', 'angiografía': 'angiografo',
    # PET
    'pet': 'pet_scan', 'pet-ct': 'pet_scan', 'pet ct': 'pet_scan',
    # Monitor
    'monitor': 'monitor', 'monitor de signos': 'monitor',
    'monitor multiparametrico': 'monitor', 'monitor multiparamétrico': 'monitor',
    # Ventilador
    'ventilador': 'ventilador', 'respirador': 'ventilador',
    # Desfibrilador
    'desfibrilador': 'desfibrilador', 'dea': 'desfibrilador',
    'cardioversor': 'desfibrilador',
    # ECG
    'ecg': 'electrocardiografo', 'ekg': 'electrocardiografo',
    'electrocardiografo': 'electrocardiografo',
    'electrocardiógraf': 'electrocardiografo',
    # Oxímetro
    'oximetro': 'oximetro', 'oxímetro': 'oximetro', 'pulsioximetro': 'oximetro',
    # Bomba
    'bomba de infusion': 'bomba_infusion', 'bomba de infusión': 'bomba_infusion',
    'bomba infusion': 'bomba_infusion', 'bomba': 'bomba_infusion',
    # Incubadora
    'incubadora': 'incubadora',
    # Electrobisturí
    'electrobisturi': 'electrobisturi', 'electrobisturí': 'electrobisturi',
    'bisturi electrico': 'electrobisturi', 'bisturí eléctrico': 'electrobisturi',
    # Autoclave
    'autoclave': 'autoclave', 'esterilizador': 'autoclave',
    # Analizador
    'analizador': 'analizador', 'autoanalizador': 'analizador',
    # Centrífuga
    'centrifuga': 'centrifuga', 'centrífuga': 'centrifuga',
    # Microscopio
    'microscopio': 'microscopio',
    # Rayos X dental
    'rx dental': 'rayos_x_dental', 'rayos x dental': 'rayos_x_dental',
    'dental rx': 'rayos_x_dental',
    # Unidad dental
    'unidad dental': 'unidad_dental', 'sillon dental': 'unidad_dental',
    'sillón dental': 'unidad_dental',
}

# Valores internos válidos (para cuando el Excel ya trae el código correcto)
_TIPOS_VALIDOS = {v for v, _ in Equipo.TIPO_CHOICES}


def _normalizar_tipo(raw):
    """Convierte texto libre del Excel al valor interno del choice, o 'otro'."""
    clave = str(raw).strip().lower()
    if clave in _TIPOS_VALIDOS:
        return clave, None          # ya venía correcto
    normalizado = _TIPO_NORMALIZAR.get(clave)
    if normalizado:
        return normalizado, None
    return 'otro', str(raw).strip() # desconocido → 'otro' + guardar texto original


def subir_equipos(request):
    resultado = None
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        if archivo:
            df = pd.read_excel(archivo)
            df.columns = df.columns.str.strip().str.lower()
            creados = actualizados = errores = 0
            for _, row in df.iterrows():
                try:
                    tipo_raw = row.get('tipo', '')
                    tipo_val, tipo_otro_val = _normalizar_tipo(tipo_raw)

                    Equipo.objects.update_or_create(
                        codigo=str(row['codigo_equipo']).strip(),
                        defaults={
                            'nombre':            str(row['nombre']).strip(),
                            'tipo':              tipo_val,
                            'tipo_otro':         tipo_otro_val,
                            'marca':             str(row.get('marca', '')).strip(),
                            'modelo':            str(row.get('modelo', '')).strip(),
                            'serie':             str(row.get('serie', '')).strip(),
                            'ubicacion':         str(row.get('ubicacion', '')).strip(),
                            'estado':            str(row.get('estado', '')).strip(),
                            'fecha_adquisicion': row.get('fecha_adquisicion') or None,
                            'criticidad':        str(row.get('criticidad', '')).strip(),
                        }
                    )
                    creados += 1
                except Exception:
                    errores += 1

            resultado = (
                f'✔ {creados} equipo(s) importado(s) correctamente'
                + (f' | ❌ {errores} con error' if errores else '')
            )

    return render(request, 'subir.html', {
        'resultado': resultado,
        'TIPO_CHOICES': Equipo.TIPO_CHOICES,
    })


# ──────────────────────────────────────────
#  SUBIR MANTENIMIENTOS
# ──────────────────────────────────────────
def subir_mantenimientos(request):
    from .models import Mantenimiento
    from datetime import datetime
 
    context = {
        'tecnicos':        Tecnico.objects.all(),
        'equipos':         Equipo.objects.all(),
        'TIPO_CHOICES':    Mantenimiento.TIPO_CHOICES,
        'ATENCION_CHOICES':Mantenimiento.ATENCION_CHOICES,
        'ETIQUETA_CHOICES':Mantenimiento.ETIQUETA_CHOICES,
    }
 
    # ── PROGRAMADO ──────────────────────────────────────────
    if request.method == 'POST' and request.POST.get('form_programado'):
        codigo       = request.POST.get('codigo_equipo', '').strip()
        etiqueta     = request.POST.get('etiqueta', '').strip()
        fecha_inicio_str = request.POST.get('fecha_inicio', '').strip()
        tipo         = request.POST.get('tipo', 'preventivo')
        tipo_otro    = request.POST.get('tipo_otro', '').strip() or None
        tipo_atencion = request.POST.get('tipo_atencion', 'presencial')
        tecnico_id   = request.POST.get('tecnico', '')
        ciudad       = request.POST.get('ciudad', '').strip() or None
 
        context['tab_activo'] = 'programado'
        context['form_prog']  = request.POST
 
        if not etiqueta or not fecha_inicio_str or not codigo:
            context['mensaje'] = '❌ Debes indicar equipo, periodicidad y fecha de inicio'
            return render(request, 'subir_mantenimientos.html', context)
 
        equipo = Equipo.objects.filter(codigo=codigo).first()
        if not equipo:
            context['mensaje'] = '❌ Equipo no encontrado'
            return render(request, 'subir_mantenimientos.html', context)
 
        tecnico = Tecnico.objects.filter(id=tecnico_id).first() if tecnico_id else None
 
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            context['mensaje'] = '❌ Fecha de inicio inválida'
            return render(request, 'subir_mantenimientos.html', context)
 
        fechas = _generar_fechas(fecha_inicio, etiqueta)
        if not fechas:
            context['mensaje'] = '❌ Periodicidad no reconocida'
            return render(request, 'subir_mantenimientos.html', context)
 
        creados = omitidos = 0
        primer_mant = None
        for i, f in enumerate(fechas):
            # Evitar duplicados exactos
            if Mantenimiento.objects.filter(equipo=equipo, fecha=f, tipo=tipo, programado=True).exists():
                omitidos += 1
                continue
            try:
                m = Mantenimiento.objects.create(
                    equipo         = equipo,
                    programado     = True,
                    serie_programada = primer_mant,  # None para el primero
                    tipo           = tipo,
                    tipo_otro      = tipo_otro,
                    fecha          = f,
                    tipo_atencion  = tipo_atencion,
                    tecnico        = tecnico,
                    estado         = 'pendiente',
                    costo          = 0,
                    etiqueta       = etiqueta,
                    ciudad         = ciudad,
                )
                if primer_mant is None:
                    primer_mant = m          # los siguientes apuntan al primero
                    m.save()                 # (no cambia nada, ya está guardado)
                creados += 1
            except Exception as e:
                omitidos += 1
 
        if creados:
            context['mensaje'] = (
                f'✔ {creados} mantenimiento(s) programado(s) creado(s)'
                + (f' · {omitidos} omitido(s) por duplicado' if omitidos else '')
            )
        else:
            context['mensaje'] = '⚠️ No se creó ningún mantenimiento (todos duplicados)'
 
        return render(request, 'subir_mantenimientos.html', context)
 
    # ── NO PROGRAMADO (manual) ───────────────────────────────
    if request.method == 'POST' and request.POST.get('form_manual'):
        codigo        = request.POST.get('codigo_equipo')
        tipo          = request.POST.get('tipo')
        tipo_otro     = request.POST.get('tipo_otro', '').strip() or None
        fecha         = request.POST.get('fecha')
        tipo_atencion = request.POST.get('tipo_atencion', 'presencial')
        problema      = request.POST.get('problema', '').strip() or None
        solucion      = request.POST.get('solucion', '').strip() or None
        descripcion   = request.POST.get('descripcion', '').strip() or None
        tecnico_id    = request.POST.get('tecnico')
        estado        = request.POST.get('estado')
        codigo_error  = request.POST.get('codigo_error', '').strip() or None
        usos_mas      = request.POST.get('usos_mas', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip() or None
 
        context['tab_activo'] = 'noprogramado'
        context['form_data']  = request.POST
 
        if not tipo:
            context['mensaje'] = '❌ Debes seleccionar un tipo de mantenimiento'
            return render(request, 'subir_mantenimientos.html', context)
 
        from datetime import datetime, timedelta
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
        hoy_dt   = datetime.now().date()
 
        if estado == 'pendiente' and fecha_dt < hoy_dt:
            context['mensaje'] = '❌ Un mantenimiento pendiente no puede tener fecha pasada'
            return render(request, 'subir_mantenimientos.html', context)
        elif estado == 'completado':
            fecha_min = hoy_dt - timedelta(days=365*10)
            if fecha_dt >= hoy_dt:
                context['mensaje'] = '❌ Un mantenimiento completado debe tener fecha anterior a hoy'
                return render(request, 'subir_mantenimientos.html', context)
            if fecha_dt < fecha_min:
                context['mensaje'] = '❌ La fecha no puede ser más de 10 años en el pasado'
                return render(request, 'subir_mantenimientos.html', context)
 
        equipo  = Equipo.objects.filter(codigo=codigo).first()
        tecnico = Tecnico.objects.filter(id=tecnico_id).first() if tecnico_id else None
 
        if not equipo:
            context['mensaje'] = '❌ Equipo no encontrado'
            return render(request, 'subir_mantenimientos.html', context)
 
        if Mantenimiento.objects.filter(equipo=equipo, fecha=fecha, tipo=tipo).exists():
            context['mensaje'] = '⚠️ Mantenimiento duplicado'
            return render(request, 'subir_mantenimientos.html', context)
 
        try:
            Mantenimiento.objects.create(
                equipo        = equipo,
                programado    = False,
                tipo          = tipo,
                tipo_otro     = tipo_otro,
                fecha         = fecha,
                tipo_atencion = tipo_atencion,
                problema      = problema,
                solucion      = solucion,
                descripcion   = descripcion,
                tecnico       = tecnico,
                estado        = estado,
                costo         = 0,
                codigo_error  = codigo_error,
                ciudad        = ciudad,
            )
            if usos_mas:
                equipo.usos_mas = int(usos_mas)
                equipo.save(update_fields=['usos_mas'])
            context['mensaje'] = '✔ Mantenimiento registrado correctamente'
            context.pop('form_data', None)
        except Exception as e:
            context['mensaje'] = f'❌ Error: {e}'
 
        return render(request, 'subir_mantenimientos.html', context)
 
    # ── EXCEL ────────────────────────────────────────────────
    if request.method == 'POST' and request.FILES.get('archivo'):
        import pandas as pd
        archivo = request.FILES['archivo']
        accion  = request.POST.get('accion')
        df      = pd.read_excel(archivo)
        df.columns = df.columns.str.strip().str.lower()
 
        context['tab_activo'] = 'excel'
 
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




# ──────────────────────────────────────────────────────────────────
#  CATÁLOGO DE SUBTAREAS POR DEFECTO
#  Se pre-carga si no hay plantillas en la BD para ese tipo de equipo.
#  Puedes editarlas desde el admin de Django.
# ──────────────────────────────────────────────────────────────────

SUBTAREAS_DEFAULT = {
    'rayos_x': [
        'Inspección visual general del equipo',
        'Limpieza exterior de consola y tubo',
        'Verificación de integridad de cables y conectores',
        'Control de colimador y obturador',
        'Prueba de disparos en diferentes técnicas (kV / mAs)',
        'Verificación de indicadores de exposición',
        'Control de blindajes de plomo',
        'Comprobación de sistema de posicionamiento',
        'Revisión de frenos mecánicos',
        'Prueba de interlocks de seguridad',
        'Verificación de señalización luminosa de radiación',
        'Calibración de dosis con dosímetro',
        'Revisión del colimador (campo luminoso vs. campo de rayos)',
        'Informe de resultados y firma del técnico',
    ],
    'tomografo': [
        'Inspección visual de gantry, mesa y consola',
        'Limpieza de detectores y sistema de refrigeración',
        'Verificación de calibración de HU (Unidades Hounsfield)',
        'Prueba de ruido, uniformidad y resolución espacial',
        'Control de kV y mAs reales vs. nominales',
        'Revisión del sistema de posicionamiento de mesa',
        'Comprobación de interlocks y paradas de emergencia',
        'Verificación de temperatura del tubo',
        'Revisión de contactor y UPS',
        'Prueba de protocolos clínicos representativos',
        'Control de dosis (CTDIvol)',
        'Revisión de registros de errores del sistema',
        'Informe de resultados y firma del técnico',
    ],
    'resonancia': [
        'Verificación del campo magnético (shimming)',
        'Prueba de homogeneidad y SNR',
        'Inspección de bobinas de radiofrecuencia',
        'Control del sistema de criógeno (helio)',
        'Revisión del sistema de ventilación de sala',
        'Verificación de interlocks magnéticos',
        'Comprobación de sistema de posicionamiento de mesa',
        'Revisión de alarmas de quench',
        'Prueba de secuencias representativas',
        'Control del sistema de RF y gradientes',
        'Informe de resultados y firma del técnico',
    ],
    'ultrasonido': [
        'Inspección visual del equipo y transductores',
        'Limpieza de transductores con producto adecuado',
        'Verificación de imagen con phantom de calidad',
        'Control de profundidad, ganancia y TGC',
        'Prueba de función Doppler (color, pulsado)',
        'Verificación de conectores y sonda',
        'Control de batería o fuente de alimentación',
        'Revisión del software y actualizaciones pendientes',
        'Informe de resultados y firma del técnico',
    ],
    'monitor': [
        'Inspección visual del monitor y accesorios',
        'Verificación de SpO2 con oxímetro de referencia',
        'Calibración de NIBP con manómetro patrón',
        'Verificación de frecuencia cardiaca y ECG',
        'Control de temperatura (si aplica)',
        'Verificación de alarmas sonoras y visuales',
        'Revisión de cables y electrodos',
        'Prueba de batería interna',
        'Actualización de software si procede',
        'Informe de resultados y firma del técnico',
    ],
    'ventilador': [
        'Inspección visual del ventilador y circuito',
        'Limpieza y desinfección de circuito respiratorio',
        'Calibración de sensores de flujo y presión',
        'Verificación de modos ventilatorios (VCV, PCV, CPAP)',
        'Prueba de alarmas (desconexión, presión alta/baja)',
        'Control de válvulas inspiratoria y espiratoria',
        'Revisión de humidificador (si aplica)',
        'Prueba de batería interna',
        'Verificación de fugas en el circuito',
        'Informe de resultados y firma del técnico',
    ],
    'desfibrilador': [
        'Inspección visual del equipo y palas/parches',
        'Prueba de carga y descarga en cada nivel de energía',
        'Verificación de sincronización (modo cardioversión)',
        'Control del marcapasos externo (si aplica)',
        'Revisión de batería y capacitor',
        'Prueba de monitoreo de ECG',
        'Verificación de impresora (si aplica)',
        'Control de accesorios (cables, palas, gel)',
        'Informe de resultados y firma del técnico',
    ],
    'electrocardiografo': [
        'Inspección visual del equipo y cables',
        'Limpieza de electrodos y cables de derivación',
        'Prueba de señal con paciente simulado',
        'Verificación de derivaciones (I, II, III, aVR, aVL, aVF, V1-V6)',
        'Control de velocidad de papel (25 mm/s)',
        'Calibración de amplitud (1 mV = 10 mm)',
        'Prueba de filtros (AC, muscular, línea base)',
        'Revisión de impresora térmica',
        'Prueba de batería',
        'Informe de resultados y firma del técnico',
    ],
    'bomba_infusion': [
        'Inspección visual de la bomba y set de infusión',
        'Verificación de precisión de flujo (ml/h) con bureta',
        'Prueba de alarmas (oclusión, batería baja, fin de infusión)',
        'Control del mecanismo de accionamiento',
        'Prueba de batería interna',
        'Verificación de pantalla y botonera',
        'Revisión del sensor de aire (si aplica)',
        'Informe de resultados y firma del técnico',
    ],
    'autoclave': [
        'Inspección visual de cámara y puerta',
        'Revisión de juntas y sellos de puerta',
        'Verificación de ciclos (temperatura, presión, tiempo)',
        'Prueba con indicadores biológicos o químicos',
        'Control de válvulas de seguridad',
        'Revisión del sistema de vacío (si aplica)',
        'Limpieza de filtros y trampa de vapor',
        'Verificación de registros de ciclos',
        'Informe de resultados y firma del técnico',
    ],
    'electrobisturi': [
        'Inspección visual del generador y accesorios',
        'Verificación de potencia de salida (modo corte y coagulación)',
        'Prueba de alarmas (mal contacto de placa, fallo de salida)',
        'Control de placa neutra y cable de paciente',
        'Revisión de pedal y electrodos',
        'Medición de corriente de fuga',
        'Informe de resultados y firma del técnico',
    ],
    'incubadora': [
        'Inspección visual de la incubadora y accesorios',
        'Calibración de temperatura interior con termómetro patrón',
        'Verificación de humedad relativa',
        'Control de alarmas (temperatura alta/baja, fallo de calefactor)',
        'Revisión del sistema de circulación de aire',
        'Limpieza de filtros HEPA',
        'Prueba de batería de respaldo (si aplica)',
        'Informe de resultados y firma del técnico',
    ],
    'oximetro': [
        'Inspección visual del equipo y sensor',
        'Verificación de SpO2 con simulador o referencia',
        'Control de frecuencia de pulso',
        'Prueba de alarmas',
        'Revisión de pantalla y batería',
        'Informe de resultados y firma del técnico',
    ],
    'mamografo': [
        'Inspección visual de la unidad y compresor',
        'Verificación de compresor (fuerza y espesor)',
        'Control de kV y mAs reales',
        'Prueba de imagen con phantom de mamografía',
        'Verificación de colimación y campo de rayos',
        'Control de dosis de entrada en superficie (ESD)',
        'Revisión del sistema de posicionamiento',
        'Informe de resultados y firma del técnico',
    ],
    'analizador': [
        'Inspección visual del equipo',
        'Calibración con estándares o calibradores certificados',
        'Control de valores de QC (interno y externo)',
        'Verificación de reactivos y fecha de vencimiento',
        'Limpieza de sondas y sistema de fluidos',
        'Revisión de impresora y conectividad LIS',
        'Informe de resultados y firma del técnico',
    ],
    'centrifuga': [
        'Inspección visual del rotor y tapa',
        'Verificación de velocidad (RPM) con tacómetro',
        'Control de temperatura (si es refrigerada)',
        'Prueba de tiempo de ciclo',
        'Revisión de balanceo del rotor',
        'Limpieza de cámara y rotor',
        'Informe de resultados y firma del técnico',
    ],
    'microscopio': [
        'Limpieza de lentes y prismas',
        'Verificación de iluminación (Köhler)',
        'Control de enfoque fino y grueso',
        'Revisión de objetivos y oculares',
        'Prueba con preparación de referencia',
        'Informe de resultados y firma del técnico',
    ],
    'rayos_x_dental': [
        'Inspección visual de la unidad intraoral/panorámica',
        'Verificación de kV y mAs',
        'Control de tiempo de exposición',
        'Prueba de imagen con phantom dental',
        'Revisión de colimador',
        'Control de blindajes de plomo',
        'Informe de resultados y firma del técnico',
    ],
    'unidad_dental': [
        'Inspección visual del sillón y módulo',
        'Verificación de turbinas y micromotores',
        'Control de jeringa triple (aire, agua, spray)',
        'Revisión del sistema de succión',
        'Prueba de lámpara de fotocurado (si aplica)',
        'Control de retracción de fluidos',
        'Limpieza y desinfección de superficies',
        'Informe de resultados y firma del técnico',
    ],
    # Default genérico para equipos de tipo "otro" o sin plantilla específica
    'otro': [
        'Inspección visual general del equipo',
        'Limpieza exterior del equipo',
        'Verificación de cables y conectores',
        'Prueba de funcionamiento básico',
        'Control de accesorios',
        'Verificación de alarmas (si aplica)',
        'Informe de resultados y firma del técnico',
    ],
}


def _obtener_o_crear_subtareas(mantenimiento):
    """
    Devuelve las SubtareaEjecucion del mantenimiento.

    LÓGICA DE MEMORIA PARA MANTENIMIENTOS PROGRAMADOS:
    - Si el mantenimiento es programado y pertenece a una serie,
      copia el estado (completada=True) de las subtareas que YA se
      completaron en mantenimientos anteriores de la misma serie,
      de modo que el técnico sólo vea pendiente lo que falta.
    - Para mantenimientos NO programados, las subtareas son independientes.
    """
    tipo = mantenimiento.equipo.tipo

    # 1. ¿Ya tiene ejecuciones? Devolver directamente.
    ejecuciones = SubtareaEjecucion.objects.filter(
        mantenimiento=mantenimiento
    ).select_related('plantilla').order_by('plantilla__orden', 'plantilla__nombre')

    if ejecuciones.exists():
        return ejecuciones

    # 2. Buscar plantillas activas para este tipo en BD.
    plantillas = SubtareaPlantilla.objects.filter(
        tipo_equipo=tipo, activa=True
    ).order_by('orden', 'nombre')

    # 3. Si no hay en BD, crearlas desde el catálogo default.
    if not plantillas.exists():
        tareas_default = SUBTAREAS_DEFAULT.get(tipo, SUBTAREAS_DEFAULT['otro'])
        for i, nombre in enumerate(tareas_default):
            SubtareaPlantilla.objects.get_or_create(
                tipo_equipo=tipo,
                nombre=nombre,
                defaults={'orden': i, 'activa': True}
            )
        plantillas = SubtareaPlantilla.objects.filter(
            tipo_equipo=tipo, activa=True
        ).order_by('orden', 'nombre')

    # 4. Para mantenimientos PROGRAMADOS: detectar subtareas ya completadas
    #    en mantenimientos anteriores de la misma serie.
    completadas_acumuladas = set()  # IDs de plantillas completadas en toda la serie

    if mantenimiento.programado:
        # Encontrar la raíz de la serie (el primer mantenimiento)
        raiz = mantenimiento.serie_programada or mantenimiento

        # Todos los mantenimientos de esta serie que sean ANTERIORES al actual
        anteriores = Mantenimiento.objects.filter(
            Q(id=raiz.id) | Q(serie_programada=raiz),
            fecha__lt=mantenimiento.fecha,
        ).exclude(id=mantenimiento.id)

        # Recopilar qué plantillas fueron completadas en alguno de ellos
        completadas_acumuladas = set(
            SubtareaEjecucion.objects.filter(
                mantenimiento__in=anteriores,
                completada=True,
            ).values_list('plantilla_id', flat=True)
        )

    # 5. Crear las ejecuciones, heredando estado si corresponde.
    for plantilla in plantillas:
        ya_completada = plantilla.id in completadas_acumuladas
        SubtareaEjecucion.objects.get_or_create(
            mantenimiento=mantenimiento,
            plantilla=plantilla,
            defaults={
                'completada': ya_completada,
                'fecha_check': timezone.now() if ya_completada else None,
                'nota': '↩ Completada en mantenimiento anterior de la serie' if ya_completada else None,
            }
        )

    return SubtareaEjecucion.objects.filter(
        mantenimiento=mantenimiento
    ).select_related('plantilla').order_by('plantilla__orden', 'plantilla__nombre')


# ──────────────────────────────────────────
#  VIEW: SUBTAREAS DEL MANTENIMIENTO (JSON)
# ──────────────────────────────────────────

def subtareas_mantenimiento(request, mantenimiento_id):
    mantenimiento = get_object_or_404(Mantenimiento, id=mantenimiento_id)
    ejecuciones   = _obtener_o_crear_subtareas(mantenimiento)

    data = [
        {
            'id':          e.id,
            'nombre':      e.plantilla.nombre,
            'completada':  e.completada,
            'nota':        e.nota or '',
            'fecha_check': e.fecha_check.strftime('%d/%m/%Y %H:%M') if e.fecha_check else None,
            'heredada':    bool(e.nota and e.nota.startswith('↩')),
        }
        for e in ejecuciones
    ]

    completadas = sum(1 for e in data if e['completada'])
    heredadas   = sum(1 for e in data if e.get('heredada'))
    return JsonResponse({
        'subtareas':   data,
        'total':       len(data),
        'completadas': completadas,
        'heredadas':   heredadas,
        'programado':  mantenimiento.programado,
    })


# ──────────────────────────────────────────
#  VIEW: TOGGLE SUBTAREA
# ──────────────────────────────────────────

def toggle_subtarea(request, ejecucion_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    ejecucion = get_object_or_404(SubtareaEjecucion, id=ejecucion_id)
    ejecucion.completada = not ejecucion.completada
    ejecucion.fecha_check = timezone.now() if ejecucion.completada else None
    ejecucion.save(update_fields=['completada', 'fecha_check'])

    return JsonResponse({
        'id':         ejecucion.id,
        'completada': ejecucion.completada,
        'fecha_check': ejecucion.fecha_check.strftime('%d/%m/%Y %H:%M') if ejecucion.fecha_check else None,
    })


# ──────────────────────────────────────────
#  VIEW: NOTA DE SUBTAREA
# ──────────────────────────────────────────

def nota_subtarea(request, ejecucion_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    ejecucion = get_object_or_404(SubtareaEjecucion, id=ejecucion_id)
    try:
        body = json.loads(request.body)
        nota = body.get('nota', '').strip()
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    ejecucion.nota = nota or None
    ejecucion.save(update_fields=['nota'])
    return JsonResponse({'ok': True, 'nota': ejecucion.nota or ''})


# ──────────────────────────────────────────
#  VIEW: GENERAR PDF DEL MANTENIMIENTO
# ──────────────────────────────────────────

def pdf_mantenimiento(request, mantenimiento_id):
    mantenimiento = get_object_or_404(Mantenimiento, id=mantenimiento_id)
    equipo        = mantenimiento.equipo
    ejecuciones   = _obtener_o_crear_subtareas(mantenimiento)

    # ── Construir el PDF en memoria ──────────────────────────
    from io import BytesIO
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm,  bottomMargin=18*mm,
    )

    W = A4[0] - 36*mm   # ancho útil
    styles = getSampleStyleSheet()

    # ── Estilos personalizados ───────────────────────────────
    VERDE    = colors.HexColor('#2cb681')
    GRIS_OSC = colors.HexColor('#1e293b')
    GRIS_CLR = colors.HexColor('#f1f5f9')
    BORDE    = colors.HexColor('#e2e8f0')

    s_titulo = ParagraphStyle(
        'titulo', parent=styles['Normal'],
        fontSize=20, textColor=GRIS_OSC, fontName='Helvetica-Bold',
        spaceAfter=2,
    )
    s_subtitulo = ParagraphStyle(
        'subtitulo', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#64748b'),
        spaceAfter=12,
    )
    s_section = ParagraphStyle(
        'section', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#94a3b8'),
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6,
        textTransform='uppercase', letterSpacing=1,
    )
    s_body = ParagraphStyle(
        'body', parent=styles['Normal'],
        fontSize=9, textColor=GRIS_OSC, leading=14,
    )
    s_check = ParagraphStyle(
        'check', parent=styles['Normal'],
        fontSize=9, textColor=GRIS_OSC, leading=14, leftIndent=6,
    )
    s_check_ok = ParagraphStyle(
        'check_ok', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#065f46'), leading=14, leftIndent=6,
    )
    s_nota = ParagraphStyle(
        'nota', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748b'), leading=11, leftIndent=18,
    )
    s_footer = ParagraphStyle(
        'footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=1,
    )

    story = []

    # ── ENCABEZADO ───────────────────────────────────────────
    header_data = [[
        Paragraph('GETS MEDICAL S.A.', ParagraphStyle(
            'hdr', parent=styles['Normal'], fontSize=13,
            fontName='Helvetica-Bold', textColor=colors.white,
        )),
        Paragraph(
            f'Informe de Mantenimiento<br/><font size="9" color="#a7f3d0">N° {mantenimiento.id:05d}</font>',
            ParagraphStyle('hdr2', parent=styles['Normal'], fontSize=12,
                           fontName='Helvetica-Bold', textColor=colors.white, alignment=2)
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.6, W*0.4])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), VERDE),
        ('TOPPADDING',  (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',(0,0),(-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING',(0,0), (-1,-1), 14),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', (0,0), (-1,-1), [6, 6, 6, 6]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10*mm))

    # ── DATOS DEL EQUIPO ─────────────────────────────────────
    story.append(Paragraph('INFORMACIÓN DEL EQUIPO', s_section))

    eq_data = [
        ['Nombre',    equipo.nombre,        'Código',    equipo.codigo],
        ['Tipo',      equipo.tipo_display(), 'Marca',     equipo.marca],
        ['Modelo',    equipo.modelo,         'Serie',     equipo.serie],
        ['Ubicación', equipo.ubicacion,      'Estado',    equipo.estado],
    ]
    if equipo.cliente:
        eq_data.append(['Cliente', equipo.cliente.nombre, 'Criticidad', equipo.criticidad])

    eq_tbl = Table(
        [[Paragraph(f'<b>{r[0]}</b>', s_body), Paragraph(str(r[1]), s_body),
          Paragraph(f'<b>{r[2]}</b>', s_body), Paragraph(str(r[3]), s_body)]
         for r in eq_data],
        colWidths=[W*0.14, W*0.36, W*0.14, W*0.36],
    )
    eq_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), GRIS_CLR),
        ('BACKGROUND',  (0,0), (0,-1),  GRIS_CLR),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GRIS_CLR, colors.white]),
        ('BOX',         (0,0), (-1,-1), 0.5, BORDE),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, BORDE),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING',(0,0),(-1,-1), 8),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(eq_tbl)
    story.append(Spacer(1, 6*mm))

    # ── DATOS DEL MANTENIMIENTO ──────────────────────────────
    story.append(Paragraph('DATOS DEL MANTENIMIENTO', s_section))

    tecnico_str  = str(mantenimiento.tecnico) if mantenimiento.tecnico else '—'
    m_data = [
        ['Tipo',       mantenimiento.tipo_display(), 'Fecha',    str(mantenimiento.fecha)],
        ['Estado',     mantenimiento.estado,          'Costo',    f'${mantenimiento.costo:.2f}'],
        ['Técnico',    tecnico_str,                   'Atención', mantenimiento.get_tipo_atencion_display()],
        ['Etiqueta',   mantenimiento.etiqueta_display(), 'Usos/mAs', str(equipo.usos_mas or '—')],
    ]

    m_tbl = Table(
        [[Paragraph(f'<b>{r[0]}</b>', s_body), Paragraph(str(r[1]), s_body),
          Paragraph(f'<b>{r[2]}</b>', s_body), Paragraph(str(r[3]), s_body)]
         for r in m_data],
        colWidths=[W*0.14, W*0.36, W*0.14, W*0.36],
    )
    m_tbl.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GRIS_CLR, colors.white]),
        ('BOX',         (0,0), (-1,-1), 0.5, BORDE),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, BORDE),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING',(0,0),(-1,-1), 8),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(m_tbl)

    # Problema / Solución
    if mantenimiento.problema:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph('PROBLEMA / ASUNTO REPORTADO', s_section))
        story.append(Paragraph(mantenimiento.problema, s_body))

    if mantenimiento.solucion:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph('SOLUCIÓN APLICADA', s_section))
        story.append(Paragraph(mantenimiento.solucion, s_body))

    # ── CHECKLIST DE SUBTAREAS ───────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('CHECKLIST DE ACTIVIDADES', s_section))

    completadas_n = sum(1 for e in ejecuciones if e.completada)
    total_n       = ejecuciones.count()

    # Barra de progreso textual
    pct = int(completadas_n / total_n * 100) if total_n else 0
    story.append(Paragraph(
        f'<b>{completadas_n}</b> de <b>{total_n}</b> actividades completadas ({pct}%)',
        ParagraphStyle('prog', parent=styles['Normal'], fontSize=9,
                       textColor=VERDE if pct == 100 else colors.HexColor('#f59e0b'),
                       spaceAfter=6)
    ))

    check_rows = []
    for e in ejecuciones:
        marca   = '&#x2611;' if e.completada else '&#x2610;'
        estilo  = s_check_ok if e.completada else s_check
        txt     = Paragraph(f'{marca}  {e.plantilla.nombre}', estilo)
        fecha_t = Paragraph(
            e.fecha_check.strftime('%d/%m/%Y') if e.fecha_check else '',
            ParagraphStyle('fch', parent=styles['Normal'], fontSize=8,
                           textColor=colors.HexColor('#94a3b8'), alignment=2)
        )
        check_rows.append([txt, fecha_t])
        if e.nota:
            check_rows.append([
                Paragraph(f'↳ <i>{e.nota}</i>', s_nota), ''
            ])

    if check_rows:
        check_tbl = Table(check_rows, colWidths=[W*0.82, W*0.18])
        check_style = [
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW',     (0,0), (-1,-2), 0.3, BORDE),
        ]
        # Colorear filas completadas
        for i, e in enumerate(ejecuciones):
            if e.completada:
                check_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f0fdf9')))
        check_tbl.setStyle(TableStyle(check_style))
        story.append(check_tbl)

    # ── PRÓXIMO MANTENIMIENTO ────────────────────────────────
    if mantenimiento.fecha_proximo:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph('PRÓXIMO MANTENIMIENTO PROGRAMADO', s_section))
        prox_data = [[
            Paragraph('<b>Fecha</b>', s_body),
            Paragraph(str(mantenimiento.fecha_proximo), s_body),
            Paragraph('<b>Periodicidad</b>', s_body),
            Paragraph(mantenimiento.etiqueta_proximo_display(), s_body),
        ]]
        prox_tbl = Table(prox_data, colWidths=[W*0.14, W*0.36, W*0.14, W*0.36])
        prox_tbl.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
            ('BOX',          (0,0), (-1,-1), 0.5, VERDE),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(prox_tbl)

    # ── FIRMAS ──────────────────────────────────────────────
    story.append(Spacer(1, 12*mm))
    firma_data = [[
        Paragraph('_________________________', s_body),
        Paragraph('_________________________', s_body),
    ], [
        Paragraph('Técnico responsable', s_footer),
        Paragraph('Representante del cliente', s_footer),
    ], [
        Paragraph(tecnico_str, ParagraphStyle('fn', parent=styles['Normal'],
                  fontSize=9, textColor=GRIS_OSC, alignment=1)),
        Paragraph('', s_body),
    ]]
    firma_tbl = Table(firma_data, colWidths=[W*0.5, W*0.5])
    firma_tbl.setStyle(TableStyle([
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(firma_tbl)

    # ── PIE DE PÁGINA ────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDE))
    story.append(Spacer(1, 2*mm))
    from datetime import date
    story.append(Paragraph(
        f'GETS MEDICAL S.A. · Mantenimiento de equipos biomédicos · '
        f'Generado el {date.today().strftime("%d/%m/%Y")}',
        s_footer
    ))

    # ── Build ────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)

    nombre_archivo = (
        f"mant_{mantenimiento.id}_{equipo.codigo}_{mantenimiento.fecha}.pdf"
    ).replace(' ', '_')

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response


def _generar_fechas(fecha_inicio, etiqueta, meses=12):
    """
    Devuelve lista de date con las fechas desde fecha_inicio
    dentro de los próximos `meses` meses según la etiqueta.
    """
    DELTAS = {
        'bimestral':     relativedelta(months=2),
        'trimestral':    relativedelta(months=3),
        'cuatrimestral': relativedelta(months=4),
        'semestral':     relativedelta(months=6),
        'anual':         relativedelta(years=1),
    }
    delta = DELTAS.get(etiqueta)
    if not delta:
        return []
 
    fechas = []
    limite = fecha_inicio + relativedelta(months=meses)
    d = fecha_inicio
    while d <= limite:
        fechas.append(d)
        d = d + delta
    return fechas


def pdf_cronograma(request, equipo_id):
    """
    Genera un PDF con la tabla de mantenimientos PROGRAMADOS del equipo.
    Columnas: N°, Fecha, Hora*, Ciudad/Lugar, Marca, Equipo, Serie, Actividad
    * La hora no se almacena en el modelo; se deja como '—' o se puede añadir
      el campo 'hora' al modelo en el futuro.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
 
    equipo = get_object_or_404(Equipo, id=equipo_id)
 
    mantenimientos = (
        Mantenimiento.objects
        .filter(equipo=equipo, programado=True)
        .order_by('fecha')
    )
 
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
 
    W = landscape(A4)[0] - 30*mm   # ancho útil
 
    VERDE  = colors.HexColor('#2cb681')
    AZUL   = colors.HexColor('#1d4ed8')
    GRIS   = colors.HexColor('#f8fafc')
    BORDE  = colors.HexColor('#e2e8f0')
    BLANCO = colors.white
 
    styles = getSampleStyleSheet()
 
    s_title = ParagraphStyle('title', parent=styles['Normal'],
        fontSize=15, fontName='Helvetica-Bold', textColor=BLANCO,
        spaceAfter=0, alignment=1)
    s_sub = ParagraphStyle('sub', parent=styles['Normal'],
        fontSize=9, textColor=BLANCO, alignment=1)
    s_th = ParagraphStyle('th', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Bold', textColor=BLANCO, alignment=1)
    s_td = ParagraphStyle('td', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#1e293b'), alignment=1)
    s_footer = ParagraphStyle('footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#94a3b8'), alignment=1)
 
    story = []
 
    # ── ENCABEZADO ───────────────────────────────────────────
    cliente_str = equipo.cliente.nombre if equipo.cliente else 'Sin cliente'
    header_data = [[
        Paragraph('GETS MEDICAL S.A.', s_title),
        Paragraph(
            f'CRONOGRAMA DE MANTENIMIENTOS PROGRAMADOS<br/>'
            f'<font size="9">{equipo.nombre} · {cliente_str}</font>',
            s_sub
        ),
        Paragraph(f'Generado: {date.today().strftime("%d/%m/%Y")}', s_sub),
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.22, W*0.56, W*0.22])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,-1), AZUL),
        ('ROUNDEDCORNERS', (0,0), (-1,-1), [8,8,8,8]),
        ('TOPPADDING',     (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 10),
        ('LEFTPADDING',    (0,0), (-1,-1), 14),
        ('RIGHTPADDING',   (0,0), (-1,-1), 14),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))
 
    # ── DATOS DEL EQUIPO ─────────────────────────────────────
    eq_data = [[
        Paragraph('<b>Marca</b>', s_td), Paragraph(equipo.marca, s_td),
        Paragraph('<b>Modelo</b>', s_td), Paragraph(equipo.modelo, s_td),
        Paragraph('<b>Serie</b>', s_td), Paragraph(equipo.serie, s_td),
        Paragraph('<b>Tipo</b>', s_td), Paragraph(equipo.tipo_display(), s_td),
    ]]
    eq_tbl = Table(eq_data, colWidths=[W*0.07, W*0.15, W*0.07, W*0.15,
                                        W*0.07, W*0.17, W*0.07, W*0.25])
    eq_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), GRIS),
        ('BOX',           (0,0), (-1,-1), 0.5, BORDE),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, BORDE),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(eq_tbl)
    story.append(Spacer(1, 5*mm))
 
    # ── TABLA DE MANTENIMIENTOS ───────────────────────────────
    COL_WIDTHS = [
        W*0.05,   # N°
        W*0.12,   # Fecha
        W*0.08,   # Hora
        W*0.18,   # Ciudad / Lugar
        W*0.12,   # Marca equipo
        W*0.20,   # Equipo (nombre)
        W*0.13,   # Serie
        W*0.12,   # Actividad (etiqueta)
    ]
    HEADERS = ['N°', 'Fecha', 'Hora', 'Ciudad / Lugar', 'Marca', 'Equipo', 'Serie', 'Actividad']
 
    rows = [[Paragraph(h, s_th) for h in HEADERS]]
 
    for i, m in enumerate(mantenimientos, start=1):
        etiq = m.etiqueta_display()
        tipo_str = m.tipo_display()
        actividad = f'Mant. {etiq}\n({tipo_str})' if etiq != '—' else f'Mant. {tipo_str}'
        rows.append([
            Paragraph(str(i), s_td),
            Paragraph(m.fecha.strftime('%d/%m/%Y'), s_td),
            Paragraph('—', s_td),
            Paragraph(m.ciudad or '—', s_td),
            Paragraph(equipo.marca, s_td),
            Paragraph(equipo.nombre, s_td),
            Paragraph(equipo.serie, s_td),
            Paragraph(actividad, s_td),
        ])
 
    if not mantenimientos.exists():
        rows.append([
            Paragraph('—', s_td),
            Paragraph('Sin mantenimientos programados', s_td),
            Paragraph('', s_td), Paragraph('', s_td),
            Paragraph('', s_td), Paragraph('', s_td),
            Paragraph('', s_td), Paragraph('', s_td),
        ])
 
    mant_tbl = Table(rows, colWidths=COL_WIDTHS, repeatRows=1)
 
    style_cmds = [
        # Encabezado
        ('BACKGROUND',    (0,0), (-1,0), VERDE),
        ('ROUNDEDCORNERS',(0,0), (-1,0), [4,4,0,0]),
        ('TOPPADDING',    (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        # Cuerpo
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [BLANCO, GRIS]),
        ('BOX',           (0,0), (-1,-1), 0.5, BORDE),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, BORDE),
        ('TOPPADDING',    (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]
    mant_tbl.setStyle(TableStyle(style_cmds))
    story.append(mant_tbl)
 
    # ── PIE ──────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDE))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f'GETS MEDICAL S.A. · Mantenimiento de equipos biomédicos · '
        f'Total: {mantenimientos.count()} mantenimiento(s) programado(s)',
        s_footer
    ))
 
    doc.build(story)
    buffer.seek(0)
 
    nombre_archivo = f"cronograma_{equipo.codigo}_{date.today()}.pdf".replace(' ', '_')
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response

def calendario(request):
    """
    Vista de calendario completo.
    Pasa TODOS los mantenimientos al template para renderizarlos en JS.
    """
    todos = (
        Mantenimiento.objects
        .select_related('equipo', 'tecnico')
        .order_by('fecha')
    )
    return render(request, 'calendario.html', {
        'todos_mantenimientos': todos,
    })