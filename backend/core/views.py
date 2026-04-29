import pandas as pd
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from .models import Cliente, Equipo, Mantenimiento, Tecnico, Documento
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
    equipo = get_object_or_404(Equipo, id=id)
    mantenimientos = (
        Mantenimiento.objects
        .filter(equipo=equipo)
        .select_related('tecnico')
        .prefetch_related('documentos')
        .order_by('-fecha')
    )
    return render(request, 'detalle.html', {
        'equipo':         equipo,
        'mantenimientos': mantenimientos,
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
        mantenimiento.costo         = float(request.POST.get('costo') or mantenimiento.costo)

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

    tipos_raw = Equipo.objects.values('tipo').annotate(total=Count('tipo'))
    # Convertir el código interno al nombre legible usando TIPO_CHOICES
    tipo_map = dict(Equipo.TIPO_CHOICES)
    tipos = [
        {
            'tipo':  tipo_map.get(t['tipo'], t['tipo']),   # label o raw si no existe
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
        'tipos':                tipos,
        'labels':               labels,
        'data':                 data,
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
    
    context = {
        'tecnicos': Tecnico.objects.all(),
        'equipos':  Equipo.objects.all(),
        'TIPO_CHOICES': Mantenimiento.TIPO_CHOICES,
        'ATENCION_CHOICES': Mantenimiento.ATENCION_CHOICES,
    }

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
        costo         = request.POST.get('costo')
        usos_mas      = request.POST.get('usos_mas', '').strip()

        # Guardar valores del formulario para mantenerlos en caso de error
        context['form_data'] = {
            'codigo_equipo': codigo,
            'tipo': tipo,
            'tipo_otro': tipo_otro,
            'fecha': fecha,
            'tipo_atencion': tipo_atencion,
            'problema': problema,
            'solucion': solucion,
            'descripcion': descripcion,
            'tecnico': tecnico_id,
            'estado': estado,
            'costo': costo,
            'usos_mas': usos_mas,
        }

        # Validar que tipo no esté vacío
        if not tipo:
            context['mensaje'] = '❌ Debes seleccionar un tipo de mantenimiento'
            return render(request, 'subir_mantenimientos.html', context)

        # Validar fecha según estado
        from datetime import datetime, timedelta
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
        hoy = datetime.now().date()
        
        if estado == 'pendiente':
            # Pendiente → fecha debe ser hoy o futura
            if fecha_dt < hoy:
                context['mensaje'] = '❌ Un mantenimiento pendiente no puede tener fecha pasada'
                return render(request, 'subir_mantenimientos.html', context)
        elif estado == 'completado':
            # Completado → fecha debe ser anterior a hoy (máx 10 años atrás)
            fecha_min = hoy - timedelta(days=365*10)
            if fecha_dt >= hoy:
                context['mensaje'] = '❌ Un mantenimiento completado debe tener fecha anterior a hoy'
                return render(request, 'subir_mantenimientos.html', context)
            if fecha_dt < fecha_min:
                context['mensaje'] = '❌ La fecha no puede ser más de 10 años en el pasado'
                return render(request, 'subir_mantenimientos.html', context)

        equipo  = Equipo.objects.filter(codigo=codigo).first()
        tecnico = Tecnico.objects.filter(id=tecnico_id).first()

        if not equipo:
            context['mensaje'] = '❌ Equipo no encontrado'
            return render(request, 'subir_mantenimientos.html', context)

        if Mantenimiento.objects.filter(equipo=equipo, fecha=fecha, tipo=tipo).exists():
            context['mensaje'] = '⚠️ Mantenimiento duplicado'
            return render(request, 'subir_mantenimientos.html', context)

        try:
            nuevo = Mantenimiento.objects.create(
                equipo=equipo, tipo=tipo, tipo_otro=tipo_otro,
                fecha=fecha, tipo_atencion=tipo_atencion,
                problema=problema, solucion=solucion,
                descripcion=descripcion, tecnico=tecnico,
                estado=estado, costo=float(costo or 0),
            )
            # Actualizar usos/mAs del equipo si se proporcionó
            if usos_mas:
                equipo.usos_mas = int(usos_mas)
                equipo.save(update_fields=['usos_mas'])
            context['mensaje'] = '✔ Mantenimiento registrado correctamente'
            # Limpiar formulario después de éxito
            if 'form_data' in context:
                del context['form_data']
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