from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from .models import RolesUsuario,Documento
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from .models import FirmaDigital
from django.utils import timezone
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os
from django.conf import settings
from django.core.files import File
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from .models import RolesUsuario, PRIORIDADES_OPCIONES, AREAS_OPCIONES
from django.db.models import Case, When, IntegerField
from django.db import connection
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery, Value, IntegerField
from django.core.paginator import Paginator

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            user_rol = RolesUsuario.objects.filter(user=user).first()
            if user_rol:
                login(request, user)
                if user_rol.rol == 'ADMIN':
                    return redirect('admin_home')
                elif user_rol.rol == 'SECRETARIA':
                    return redirect('secretaria_home')
                elif user_rol.rol == 'USUARIO':
                    return redirect('usuario_home')
                elif user_rol.rol == 'TESORERIA':  # Nueva condición para Tesorería
                    return redirect('tesoreria_home')
            else:
                messages.info(request, 'Espere a que le asignen su rol')
        else:
            messages.error(request, 'Credenciales no válidas')
    return render(request, 'login.html')


def visar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        if not documento_id:
            messages.error(request, 'No se ha especificado un documento para visar.')
            return redirect('usuario_home')

        documento = get_object_or_404(Documento, id=documento_id)

        # Verificar si el documento es de tipo FUT
        if documento.tipo == 'FUT':
            # Leer el documento original
            existing_pdf = PdfReader(open(documento.archivo.path, "rb"))
            output = PdfWriter()

            # Crear el overlay con el texto "Documento Visado por jefe de área"
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)

            # Coordenadas del texto para el documento FUT
            x = 50  # Coordenada X en la esquina inferior izquierda
            y = 200  # Coordenada Y, ajustado un poco arriba de la esquina inferior

            can.setFont("Helvetica", 12)
            can.drawString(x, y, "Documento Visado por jefe de área")
            can.save()

            # Volver al inicio del buffer
            packet.seek(0)
            overlay_pdf = PdfReader(packet)

            # Añadir el overlay a la primera página del documento
            for i in range(len(existing_pdf.pages)):
                page = existing_pdf.pages[i]
                if i == 0:  # Añadir solo en la primera página
                    page.merge_page(overlay_pdf.pages[0])
                output.add_page(page)

            # Guardar el documento visado en la misma ruta del archivo original
            visado_pdf_path = documento.archivo.path
            with open(visado_pdf_path, "wb") as outputStream:
                output.write(outputStream)

        # Marcar el documento como visado
        documento.visado = True
        documento.save()

        messages.success(request, 'Documento visado con éxito.')
    else:
        messages.error(request, 'Error en el visado del documento.')

    return redirect('usuario_home')


def tesoreria_home(request):
    documentos_aprobados = Documento.objects.filter(estado='APROBADO').order_by('-fecha_emision')
    documentos_por_pagar = Documento.objects.filter(estado='APROBADO', pagado=False).order_by('-fecha_emision')
    cantidad_documentos_por_pagar = documentos_por_pagar.count()

    return render(request, 'tesoreria_home.html', {
        'documentos_aprobados': documentos_aprobados,
        'documentos_por_pagar': cantidad_documentos_por_pagar

    })



def registrar_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        sede = request.POST.get('sede')
        area = request.POST.get('area')
        es_jefe_area = request.POST.get('es_jefe_area') == 'on'  # Check if the checkbox is checked

        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'El nombre de usuario ya está en uso')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'El correo electrónico ya está en uso')
            else:
                # Comprobar si ya existe otro rol con el área seleccionada
                existing_role = RolesUsuario.objects.filter(area=area).first()

                # Si existe, usar su prioridad; de lo contrario, usar el valor por defecto
                if existing_role:
                    priority = existing_role.prioridad
                else:
                    priority = 'BAJA'  # Valor por defecto

                # Crear el usuario
                user = User.objects.create_user(username=username, email=email, password=password1, first_name=first_name)

                # Crear el rol del usuario con la sede, el área, la prioridad seleccionada y si es jefe de área
                RolesUsuario.objects.create(user=user, sede=sede, area=area, rol='USUARIO', prioridad=priority, es_jefe_area=es_jefe_area)

                messages.success(request, 'Cuenta creada con éxito')
                return redirect('login')
        else:
            messages.error(request, 'Las contraseñas no coinciden')
    
    return render(request, 'registrar.html')

@login_required(login_url='/login/')
def admin_view(request):
    if not request.user.roles.rol == 'ADMIN':
        return redirect('home')

    # Crear un diccionario para mapear prioridades a valores enteros
    prioridad_map = {
        'ALTA': 3,
        'MEDIA': 2,
        'BAJA': 1
    }
    # Crear un Case para asignar valores numéricos según la prioridad
    prioridad_order = Case(
        When(usuario__roles__prioridad='ALTA', then=3),
        When(usuario__roles__prioridad='MEDIA', then=2),
        When(usuario__roles__prioridad='BAJA', then=1),
        output_field=IntegerField(),
    )

    # Obtener todos los documentos PENDIENTES y que estén visados
    documentos = Documento.objects.select_related('usuario').annotate(
        prioridad_num=prioridad_order
    ).filter(
        estado='PENDIENTE',  # Solo documentos en estado 'PENDIENTE'
        visado=True  # Solo documentos que estén visados
    ).order_by(
        'prioridad_num',  # Ordenar por prioridad (ALTA -> MEDIA -> BAJA)
        'fecha_emision'  # Luego ordenar por fecha de emisión (del más antiguo al más reciente)
    )

    # Filtrar por tipo de documento si se proporciona
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        documentos = documentos.filter(tipo=tipo_filtro)

    # Filtrar por prioridad si se proporciona
    prioridad_filtro = request.POST.get('prioridad')
    if prioridad_filtro:
        documentos = documentos.filter(usuario__roles__prioridad=prioridad_filtro)

    # Obtener todos los documentos para el conteo
    all_documentos = Documento.objects.all()

    # Categorizar los documentos

    documentos_aprobados = all_documentos.filter(estado='APROBADO', visado=True)
    documentos_denegados = all_documentos.filter(estado='DENEGADO')

    # Contar los documentos en cada categoría
    count_pendientes = documentos.count()
    count_aprobados = documentos_aprobados.count()
    count_denegados = documentos_denegados.count()

    context = {
        'documentos': documentos,

        'documentos_aprobados': documentos_aprobados,
        'documentos_denegados': documentos_denegados,
        'count_pendientes': count_pendientes,
        'count_aprobados': count_aprobados,
        'count_denegados': count_denegados,
        'tipos_documento': Documento.TIPOS_DOCUMENTO,
        'estados_documento': Documento.ESTADOS_DOCUMENTO,
        'prioridad_dict': {v: k for k, v in prioridad_map.items()}
    }
    return render(request, 'admin_home.html', context)

def secretaria_home_view(request):
    documentos_aprobados = Documento.objects.filter(estado='APROBADO').order_by('-fecha_emision')
    documentos_pendientes = Documento.objects.filter(estado='PENDIENTE').order_by('-fecha_emision')

    # Obtener las opciones de prioridades y áreas para el formulario
    prioridades_opciones = dict(PRIORIDADES_OPCIONES)
    areas_opciones = dict(AREAS_OPCIONES)

    return render(request, 'secretaria_home.html', {
        'documentos_aprobados': documentos_aprobados,
        'documentos_pendientes': documentos_pendientes,
        'prioridades_opciones': prioridades_opciones,
        'areas_opciones': areas_opciones
    })





def marcar_pagado(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    
    if request.method == 'POST':
        observacion = request.POST.get('observacion', '')

        # Limpiar el valor anterior de la observación antes de guardar una nueva
        documento.observacion = ''  
        
        # Actualizar el estado a pagado y guardar la nueva observación (si existe)
        documento.pagado = True
        documento.observacion = observacion  # Guardar la nueva observación, aunque sea una cadena vacía
        documento.save()

        messages.success(request, "Documento marcado como pagado con observación.")
    
    return redirect('tesoreria_home')
from django.db.models import Q

@login_required
def usuario_home_view(request):
    # Filtrar documentos por usuario y ordenarlos por fecha de emisión
    documentos = Documento.objects.filter(usuario=request.user).order_by('-fecha_emision')

    # Calcular los conteos de los diferentes estados de los documentos
    pendientes_count = documentos.filter(estado='PENDIENTE').count()
    aprobados_count = documentos.filter(estado='APROBADO').count()
    denegados_count = documentos.filter(estado='DENEGADO').count()

    # Calcular documentos pagados y visados
    pagados_count = documentos.filter(estado='APROBADO',pagado=False).count()

    try:
        rol_usuario = RolesUsuario.objects.get(user=request.user)
        area_usuario = rol_usuario.area
        es_jefe_area = rol_usuario.es_jefe_area
    except RolesUsuario.DoesNotExist:
        # Manejar el caso si el usuario no tiene un rol asociado
        area_usuario = None
        es_jefe_area = False



    documentos_por_revisar = Documento.objects.filter(
        Q(usuario__roles__area=area_usuario) & ~Q(usuario=request.user) & Q(visado=False)
    ).order_by('-fecha_emision')

    return render(request, 'usuario_home.html', {
        'documentos': documentos,
        'documentos_por_revisar': documentos_por_revisar,
        'es_jefe_area': es_jefe_area,
        'pendientes_count': pendientes_count,
        'aprobados_count': aprobados_count,
        'denegados_count': denegados_count,
        'pagados_count': pagados_count,  # Añadido conteo de documentos pagados
    })



def subir_documento_view(request):
    if request.method == 'POST':
        tipo = request.POST['tipo']
        archivo = request.FILES['archivo']
        
        # Verificar si el usuario es jefe o pertenece al área de Académica
        try:
            rol_usuario = RolesUsuario.objects.get(user=request.user)
            is_jefe = rol_usuario.es_jefe_area
            is_academica = rol_usuario.area == 'ACADEMICA'  # Verificar si el área es 'Academica'
        except RolesUsuario.DoesNotExist:
            is_jefe = False
            is_academica = False
        
        # Crear el documento
        documento = Documento(usuario=request.user, tipo=tipo, archivo=archivo)
        
        # Marcar como visado solo si el usuario es jefe
        if is_jefe:
            documento.visado = True
        
        documento.save()
        messages.success(request, 'Documento subido correctamente.')
        return redirect('usuario_home')

    # Obtener tipos de documento
    tipos_documento = dict(Documento.TIPOS_DOCUMENTO)
    
    # Verificar si el usuario es jefe o pertenece al área de Académica
    try:
        rol_usuario = RolesUsuario.objects.get(user=request.user)
        is_jefe = rol_usuario.es_jefe_area
        is_academica = rol_usuario.area == 'ACADEMICA'  # Verificar si el área es 'Academica'
    except RolesUsuario.DoesNotExist:
        is_jefe = False
        is_academica = False
    
    # Filtrar los tipos de documento según el rol del usuario
    if not is_jefe and not is_academica:
        tipos_documento = {k: v for k, v in tipos_documento.items() if k == 'FUT'}
    
    return render(request, 'subir_documento.html', {
        'tipos_documento': tipos_documento,
        'is_jefe': is_jefe,
        'is_academica': is_academica
    })



@login_required
def rechazar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        documento = get_object_or_404(Documento, pk=documento_id)
        observacion = request.POST.get('motivo_rechazo', '')

        # Rechazar el documento
        documento.estado = 'DENEGADO'
        documento.observacion = observacion
        documento.save()

        # Obtener el rol del usuario
        user_role = getattr(request.user.roles, 'rol', 'USUARIO')

        # Redirigir a la vista adecuada con un mensaje de éxito
        if user_role == 'ADMIN':
            messages.success(request, 'Documento rechazado correctamente.')
            return redirect('admin_home')
        else:
            messages.success(request, 'Documento rechazado correctamente.')
            return redirect('usuario_home')

    return redirect('usuario_home')

def subsanar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        if not documento_id:
            messages.error(request, "El ID del documento no se ha proporcionado.")
            return redirect('usuario_home')  # Redirige si no se proporciona el ID

        documento = get_object_or_404(Documento, id=documento_id)
        
        if 'archivo_nuevo' in request.FILES:
            nuevo_archivo = request.FILES['archivo_nuevo']
            documento.archivo.delete(save=False)  # Elimina el archivo existente
            documento.archivo = nuevo_archivo
            documento.estado = 'PENDIENTE'  # O el estado que consideres adecuado
            documento.fecha_emision = timezone.now()  # Asigna la fecha actual
            documento.save()
            messages.success(request, "Documento subsanado con éxito.")
        else:
            messages.error(request, "Por favor, sube un archivo.")
        
        return redirect('usuario_home')  # Redirige después de procesar
    else:
        messages.error(request, "Método no permitido.")
        return redirect('usuario_home')  # Redirige si no es POST
@login_required
def aprobar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        if not documento_id:
            messages.error(request, 'No se ha especificado un documento para aprobar.')
            return redirect('documentos')  # Redirige a la página de documentos o al origen del formulario

        documento = get_object_or_404(Documento, id=documento_id)

        # Verificar si el usuario tiene el rol adecuado
        try:
            rol_usuario = RolesUsuario.objects.get(user=request.user)
            if rol_usuario.rol == 'ADMIN':
                # Obtener la firma digital del usuario actual
                firma_digital = FirmaDigital.objects.filter(usuario=request.user).first()
                if firma_digital and firma_digital.firma_digital:
                    print(f"Firma digital encontrada: {firma_digital.firma_digital.path}")

                    # Aprobar el documento y firmarlo
                    documento.estado = 'APROBADO'
                    documento.fecha_recepcion = datetime.now()
                    print(f"Estado del documento antes de firmar: {documento.estado}")

                    # Leer el documento original
                    existing_pdf = PdfReader(open(documento.archivo.path, "rb"))
                    output = PdfWriter()

                    # Crear el overlay con la firma
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=letter)

                    # Coordenadas de la firma según el tipo de documento
                    if documento.tipo == 'FUT':
                        x = 450
                        y = 60
                    else:
                        x = 612 - 160  # Ajustar 'x' para que quede cerca del borde derecho (612 es el ancho de la página en puntos)
                        y = 792 - 80   # Ajustar 'y' para que quede cerca del borde superior (792 es la altura de la página en puntos)
                    
                    width = 150    # Ancho de la firma
                    height = 50    # Alto de la firma

                    can.drawImage(firma_digital.firma_digital.path, x, y, width, height)
                    can.save()

                    packet.seek(0)
                    overlay_pdf = PdfReader(packet)

                    # Añadir el overlay al documento original
                    for i in range(len(existing_pdf.pages)):
                        page = existing_pdf.pages[i]
                        if i == 0:  # Añadir la firma solo en la primera página
                            page.merge_page(overlay_pdf.pages[0])
                        output.add_page(page)

                    # Crear el directorio si no existe
                    output_dir = os.path.join(settings.MEDIA_ROOT, 'documentos_firmados')
                    os.makedirs(output_dir, exist_ok=True)

                    # Guardar el documento firmado en un archivo temporal
                    signed_pdf_path = os.path.join(output_dir, os.path.basename(documento.archivo.name))
                    with open(signed_pdf_path, "wb") as outputStream:
                        output.write(outputStream)

                    print(f"Documento firmado guardado en: {signed_pdf_path}")

                    # Asignar el archivo firmado al campo del modelo
                    with open(signed_pdf_path, "rb") as f:
                        documento.archivo_firmado.save(os.path.basename(signed_pdf_path), File(f), save=False)

                    # Eliminar el archivo temporal
                    os.remove(signed_pdf_path)

                    documento.save()

                    messages.success(request, 'Documento aprobado con éxito.')
                else:
                    messages.error(request, 'Falta la firma digital para aprobar el documento.')
            else:
                messages.error(request, 'No tienes permisos para aprobar documentos.')
        except RolesUsuario.DoesNotExist:
            messages.error(request, 'No se pudo encontrar el rol del usuario.')

    return redirect('admin_home')


def salir(request):
    logout(request)
    return redirect('/login/')

@login_required
def subir_firma_digital(request):
    if request.method == 'POST':
        if 'firma_digital' in request.FILES:
            firma_digital = request.FILES['firma_digital']
            if firma_digital.content_type in ['image/png', 'image/jpeg']:
                firma, created = FirmaDigital.objects.get_or_create(usuario=request.user)
                firma.firma_digital = firma_digital
                firma.save()
                messages.success(request, 'Firma digital subida con éxito.')
                return redirect('admin_home')
            else:
                messages.error(request, 'Formato de archivo no válido. Solo se permiten imágenes PNG y JPEG.')
        else:
            messages.error(request, 'No se ha seleccionado ningún archivo.')
    return redirect('admin_home')

def update_priorities(request):
    if request.method == 'POST':
        area = request.POST.get('area')
        priority = request.POST.get('priority')

        if area and priority:
            # Validar que la prioridad esté en las opciones permitidas
            valid_priorities = dict(PRIORIDADES_OPCIONES).keys()
            if priority not in valid_priorities:
                messages.error(request, f'Prioridad inválida: {priority}.')
                return redirect('secretaria_home')

            # Actualizar prioridades para todos los usuarios en el área seleccionada
            count = RolesUsuario.objects.filter(area=area).update(prioridad=priority)

            # Mensaje de éxito
            messages.success(request, f'Prioridades actualizadas para el área {area} a {priority.capitalize()} ({count} usuarios afectados).')

        else:
            messages.error(request, 'Área o prioridad no proporcionadas.')

        return redirect('secretaria_home')

    # Si el método no es POST, redirigir al home
    return redirect('secretaria_home')