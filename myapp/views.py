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
from django.http import JsonResponse
from .models import Memo,Formato
import json
import random
import string
from reportlab.lib import colors

def cambiar_contrasena(request):
    if request.method == "POST":
        user_id = request.POST.get("usuario")
        nueva_contrasena = request.POST.get("nueva_contrasena")

        if not user_id or not nueva_contrasena:
            return JsonResponse({"success": False, "message": "Todos los campos son obligatorios."})

        usuario = get_object_or_404(User, id=user_id)
        usuario.set_password(nueva_contrasena)
        usuario.save()

        return JsonResponse({"success": True, "message": f"Contraseña actualizada: {nueva_contrasena}"})

    usuarios = User.objects.all()
    return render(request, "cambiar_contrasena.html", {"usuarios": usuarios})
    
def descargar_formatos(request):
    formatos = get_list_or_404(Formato)

    zip_filename = "formatos_word.zip"
    zip_path = os.path.join("/tmp", zip_filename)  # Directorio temporal

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for formato in formatos:
            if formato.archivo:  # Asegurar que el archivo existe
                file_path = formato.archivo.path
                zipf.write(file_path, os.path.basename(file_path))

    with open(zip_path, "rb") as zip_file:
        response = HttpResponse(zip_file.read(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
        return response
def documentos_view(request):
    sede = request.GET.get('sede', '')
    pagado = request.GET.get('pagado', '')
    tipo = request.GET.get('tipo', '')
    area = request.GET.get('area', '')

    # Consulta base
    documentos = Documento.objects.all()

    # Aplicar filtros si existen
    if sede:
        documentos = documentos.filter(usuario__roles__sede=sede)
    if pagado:
        documentos = documentos.filter(pagado=(pagado == 'pagado'))
    if tipo:
        documentos = documentos.filter(tipo=tipo)
    if area:
        documentos = documentos.filter(usuario__roles__area=area)

    # Pasar datos al template
    context = {
        'documentos_aprobados': documentos,
        'tipos': Documento.objects.values_list('tipo', flat=True).distinct(),
        'areas': Role.objects.values_list('area', flat=True).distinct(),
    }
    return render(request, 'documentos_template.html', context)
    
    
def eliminar_memo(request):
    if request.method == 'POST':
        memo_id = request.POST.get('memo_id')
        memo = get_object_or_404(Memo, id=memo_id)
        memo.delete()  # Eliminar el memo
        return redirect('/memo/')  # Redirigir a la página de memos
    return redirect('/memo/')  # Redirigir a la página de memos
    

def memo_view(request):
    memos = Memo.objects.all().order_by('-fecha_envio')  # Ordenar los memos por fecha de envío (más recientes primero)

    # Obtener el usuario logueado
    usuario_logueado = request.user
    rol_usuario = None
    if request.user.is_authenticated:
        try:
            rol_usuario = request.user.roles.rol  # Acceder al rol desde el modelo relacionado 'RolesUsuario'
        except RolesUsuario.DoesNotExist:
            rol_usuario = 'USUARIO'  # En caso de que el usuario no tenga un rol asignado, asignar 'USUARIO'

    # Si el formulario es enviado (POST)
    if request.method == 'POST':
        asunto = request.POST.get('asunto')
        contenido = request.POST.get('contenido')
        archivo_pdf = request.FILES.get('archivo_pdf')
        destinatario_tipo = request.POST.get('destinatario_tipo')
        area_destino = request.POST.get('area_destino')

        if asunto and contenido and destinatario_tipo:
            memo = Memo(
                asunto=asunto,
                archivo_pdf=archivo_pdf,
                destinatario_tipo=destinatario_tipo,
                area_destino=area_destino
            )
            memo.save()
            messages.success(request, 'El memo se ha enviado correctamente.')
            return redirect('memo_view')
        else:
            messages.error(request, 'Por favor, completa todos los campos obligatorios.')

    # Obtener el jefe de área si se selecciona un área
    jefe_area = None
    if request.method == 'POST' and area_destino:
        jefe_area = User.objects.filter(roles__area=area_destino, roles__es_jefe_area=True).first()

    # Pasar datos a la plantilla
    return render(request, 'memo_form.html', {
        'rol': rol_usuario,
        'jefe_area': jefe_area,
        'memos': memos,

    })



def actualizar_emitido_por_jefe(request):
    try:
        documentos = Documento.objects.all()  # Obtén todos los documentos
        for documento in documentos:
            if documento.usuario.roles.es_jefe_area and documento.tipo != 'FUT':
                documento.emitido_por_jefe = True
            else:
                documento.emitido_por_jefe = False
            documento.save()  # Guarda los cambios

        return JsonResponse({'status': 'success', 'message': 'Documentos actualizados correctamente.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    
    
    
        
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
                elif user_rol.rol == 'GERENTE':
                    return redirect('gerente_home')                    
                elif user_rol.rol == 'USUARIO':
                    return redirect('usuario_home')
                elif user_rol.rol == 'TESORERIA':  # Nueva condición para Tesorería
                    return redirect('tesoreria_home')
            else:
                return redirect('login')
        else:
            return redirect('login')
    return render(request, 'login.html')

from reportlab.lib.colors import blue  # Importa el color azul
def gerente_home(request):
    rol_usuario = request.user.roles.rol  # Acceso directo al rol del usuario
    # Mapa para las prioridades (ALTA, MEDIA, BAJA)
    prioridad_map = {
        'ALTA': 3,
        'MEDIA': 2,
        'BAJA': 1
    }

    # Obtener documentos por prioridad y estado 'PENDIENTE', visados
    documentos_alta = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=True,
        prioridad='ALTA',
        interno=False,
    ).order_by('fecha_emision')  # Ordenar por fecha de emisión (del más antiguo al más reciente)

    documentos_media = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=True,
        prioridad='MEDIA',
        interno=False,
    ).order_by('fecha_emision')

    documentos_baja = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=True,
        prioridad='BAJA',
        interno=False,
    ).order_by('fecha_emision')

    # Unir todas las listas de documentos en el orden de prioridad
    documentos = list(documentos_alta) + list(documentos_media) + list(documentos_baja)

    # Filtrar por tipo de documento si se proporciona
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        documentos = [doc for doc in documentos if doc.tipo == tipo_filtro]

    # Filtrar por prioridad si se proporciona
    prioridad_filtro = request.GET.get('prioridad', '')  # Cambio a GET para consistencia
    if prioridad_filtro:
        documentos = [doc for doc in documentos if doc.prioridad == prioridad_filtro]

    # Obtener todos los documentos para el conteo de estados
    all_documentos = Documento.objects.all()
    # Obtener todos los documentos aprobados, ordenados por fecha de emisión (más reciente primero)
    documentos_aprobados = all_documentos.filter(estado='APROBADO', visado=True,visado_admin=True,interno=False).order_by('-fecha_emision')
    documentos_denegados = all_documentos.filter(estado='DENEGADO')

    # Contar los documentos en cada categoría
    count_pendientes = len(documentos)
    count_aprobados = documentos_aprobados.count()
    count_denegados = documentos_denegados.count()

    # Preparar el contexto para pasar a la plantilla
    context = {
        'documentos': documentos,
        'documentos_aprobados': documentos_aprobados,
        'documentos_denegados': documentos_denegados,
        'count_pendientes': count_pendientes,
        'count_aprobados': count_aprobados,
        'count_denegados': count_denegados,
        'tipos_documento': Documento.TIPOS_DOCUMENTO,
        'estados_documento': Documento.ESTADOS_DOCUMENTO,
        'prioridad_dict': prioridad_map,  
        'rol': rol_usuario
    }
    return render(request, 'gerente_home.html',context)

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
            x = 400  # Coordenada X en la esquina inferior izquierda
            y = 770  # Coordenada Y, ajustado un poco arriba de la esquina inferior
            can.setFillColor(blue)
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

from django.db.models import Q
def tesoreria_home(request):
    # Obtener parámetros de filtrado desde la URL (GET)
    sede = request.GET.get('sede', '')  # Valor por defecto es una cadena vacía
    pagado = request.GET.get('pagado', '')
    tipo = request.GET.get('tipo', '')
    area = request.GET.get('area', '')

    # Consulta base de documentos aprobados
    documentos_aprobados = Documento.objects.filter(estado='APROBADO', interno=False).order_by('-fecha_recepcion')

    # Aplicar filtros si se proporcionan
    if sede:
        documentos_aprobados = documentos_aprobados.filter(usuario__roles__sede=sede)
    if pagado:
        documentos_aprobados = documentos_aprobados.filter(pagado=(pagado == 'pagado'))
    if tipo:
        documentos_aprobados = documentos_aprobados.filter(tipo=tipo)
    if area:
        documentos_aprobados = documentos_aprobados.filter(usuario__roles__area=area)

    # Obtener los documentos por pagar (sin filtro adicional)
    documentos_por_pagar = Documento.objects.filter(estado='APROBADO', pagado=False, interno=False).order_by('-fecha_recepcion')
    cantidad_documentos_por_pagar = documentos_por_pagar.count()

    # Obtener los tipos y áreas disponibles (si son dinámicos)
    tipos = Documento.objects.values_list('tipo', flat=True).distinct()
    areas = RolesUsuario.objects.values_list('area', flat=True).distinct()

    # Obtener el rol del usuario autenticado
    rol_usuario = None
    if request.user.is_authenticated:
        try:
            rol_usuario = request.user.roles.rol  # Acceder al rol desde el modelo relacionado 'RolesUsuario'
        except RolesUsuario.DoesNotExist:
            rol_usuario = 'USUARIO'  # En caso de que el usuario no tenga un rol asignado, asignar 'USUARIO'

    # Pasar datos al template
    context = {
        'documentos_aprobados': documentos_aprobados,
        'documentos_por_pagar': cantidad_documentos_por_pagar,
        'rol': rol_usuario,
        'tipos': tipos,
        'areas': areas,
    }
    return render(request, 'tesoreria_home.html', context)




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
                # Crear el usuario
                user = User.objects.create_user(username=username, email=email, password=password1, first_name=first_name)

                # Crear el rol del usuario con la sede, el área, la prioridad seleccionada y si es jefe de área
                RolesUsuario.objects.create(user=user, sede=sede, area=area, rol='USUARIO', es_jefe_area=es_jefe_area)

                messages.success(request, 'Cuenta creada con éxito')
                return redirect('login')
        else:
            messages.error(request, 'Las contraseñas no coinciden')
    
    return render(request, 'registrar.html')

@login_required(login_url='/login/')
def admin_view(request):
    # Verificar si el usuario es ADMIN
    # Verificar si el usuario tiene un rol antes de acceder a él
    if not hasattr(request.user, 'roles') or request.user.roles is None or request.user.roles.rol != 'ADMIN':
        return redirect('login')

    rol_usuario = request.user.roles.rol  # Acceso directo al rol del usuario

    # Mapa para las prioridades (ALTA, MEDIA, BAJA)
    prioridad_map = {
        'ALTA': 3,
        'MEDIA': 2,
        'BAJA': 1
    }

    # Obtener documentos por prioridad y estado 'PENDIENTE', visados
    documentos_alta = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=False,
        prioridad='ALTA'
    ).order_by('fecha_emision')  # Ordenar por fecha de emisión (del más antiguo al más reciente)

    documentos_media = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=False,
        prioridad='MEDIA'
    ).order_by('fecha_emision')

    documentos_baja = Documento.objects.filter(
        estado='PENDIENTE',
        visado=True,
        visado_admin=False,
        prioridad='BAJA'
    ).order_by('fecha_emision')

    # Unir todas las listas de documentos en el orden de prioridad
    documentos = list(documentos_alta) + list(documentos_media) + list(documentos_baja)

    # Filtrar por tipo de documento si se proporciona
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        documentos = [doc for doc in documentos if doc.tipo == tipo_filtro]

    # Filtrar por prioridad si se proporciona
    prioridad_filtro = request.GET.get('prioridad', '')  # Cambio a GET para consistencia
    if prioridad_filtro:
        documentos = [doc for doc in documentos if doc.prioridad == prioridad_filtro]

    # Obtener todos los documentos para el conteo de estados
    all_documentos = Documento.objects.all()
    # Obtener todos los documentos aprobados, ordenados por fecha de emisión (más reciente primero)
    documentos_aprobados = all_documentos.filter(estado='APROBADO', visado=True).order_by('-fecha_emision')
    documentos_denegados = all_documentos.filter(estado='DENEGADO')

    # Contar los documentos en cada categoría
    count_pendientes = len(documentos)
    count_aprobados = documentos_aprobados.count()
    count_denegados = documentos_denegados.count()

    # Preparar el contexto para pasar a la plantilla
    context = {
        'documentos': documentos,
        'documentos_aprobados': documentos_aprobados,
        'documentos_denegados': documentos_denegados,
        'count_pendientes': count_pendientes,
        'count_aprobados': count_aprobados,
        'count_denegados': count_denegados,
        'tipos_documento': Documento.TIPOS_DOCUMENTO,
        'estados_documento': Documento.ESTADOS_DOCUMENTO,
        'prioridad_dict': prioridad_map,  
        'rol': rol_usuario
    }

    return render(request, 'admin_home.html', context)

from django.views.decorators.csrf import csrf_exempt

def secretaria_home_view(request):
    # Inicializar los documentos aprobados y pendientes
    documentos_aprobados = Documento.objects.filter(estado='APROBADO').order_by('-fecha_emision')
    documentos_pendientes = Documento.objects.filter(estado='PENDIENTE').order_by('-fecha_emision')

    # Obtener el área, rol y DNI del usuario autenticado
    rol_usuario = None
    area_usuario = None
    dni_usuario = None
    restringido = False  # Bandera para aplicar restricciones

    if request.user.is_authenticated:
        try:
            # Obtener el rol, área y DNI del usuario
            rol_usuario = request.user.roles.rol
            area_usuario = request.user.roles.area
            dni_usuario = request.user.username  # Suponiendo que el DNI está almacenado en el campo username
        except RolesUsuario.DoesNotExist:
            rol_usuario = 'USUARIO'  # Rol predeterminado
            area_usuario = None

    # Verificar si el usuario tiene el DNI restringido
    if dni_usuario == '60899909':
        restringido = True
        documentos_pendientes = []  # No mostrar documentos pendientes

    # Filtrar documentos si el área es "Académica"
    if area_usuario == 'ACADEMICA':
        documentos_aprobados = documentos_aprobados.filter(usuario__roles__area='ACADEMICA')
        if not restringido:
            documentos_pendientes = documentos_pendientes.filter(usuario__roles__area='ACADEMICA')

    # Obtener opciones de prioridades y áreas para el formulario
    prioridades_opciones = dict(PRIORIDADES_OPCIONES)
    areas_opciones = dict(AREAS_OPCIONES)

    # Renderizar la plantilla
    return render(request, 'secretaria_home.html', {
        'documentos_aprobados': documentos_aprobados,
        'documentos_pendientes': documentos_pendientes,
        'prioridades_opciones': prioridades_opciones,
        'areas_opciones': areas_opciones,
        'rol': rol_usuario,
        'dni': dni_usuario,
        'restringido': restringido,
    })



@csrf_exempt
def marcar_leido(request, memo_id):
    if request.method == 'POST':
        memo = get_object_or_404(Memo, id=memo_id)
        memo.marcar_como_leido(request.user)
        return JsonResponse({'status': 'success', 'redirect': False})  # No redirige
    return JsonResponse({'status': 'error'}, status=400)


def marcar_pagado(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    
    if request.method == 'POST':
        observacion = request.POST.get('observacion', '')

        # Limpiar el valor anterior de la observación antes de guardar una nueva
        documento.observacion = ''  
        if documento.tipo == 'REQ':
            documento.rendicion = False
            
        # Actualizar el estado a pagado y guardar la nueva observación (si existe)
        documento.pagado = True
        documento.observacion = observacion  # Guardar la nueva observación, aunque sea una cadena vacía
        documento.save()

        messages.success(request, "Documento marcado como pagado con observación.")
    
    return redirect('tesoreria_home')
from django.db.models import Q
from django.views.decorators.http import require_POST
import traceback
from django.utils.text import slugify  # Para normalizar nombres de archivos
import unicodedata

@require_POST
@csrf_exempt
def enviar_a_tesoreria(request):
    try:
        documento_id = request.POST.get("documento_id")
        archivo_rendicion = request.FILES.get("archivo_rendicion")

        if not documento_id or not archivo_rendicion:
            return JsonResponse({"error": "Faltan datos"}, status=400)

        documento = Documento.objects.get(id=documento_id)

        # 🛠 **Normalizar el nombre del archivo**
        nombre_original = archivo_rendicion.name
        extension = os.path.splitext(nombre_original)[1]
        nombre_limpio = slugify(os.path.splitext(nombre_original)[0]) + extension

        archivo_rendicion.name = nombre_limpio  # Asigna el nuevo nombre limpio

        # Guardar el archivo en el modelo
        documento.archivo_rendicion = archivo_rendicion
        documento.fecha_rendicion = datetime.now()
        documento.rendicion = True
        documento.save()

        return JsonResponse({"mensaje": "Documento enviado a Tesorería correctamente."}, status=200)

    except Documento.DoesNotExist:
        return JsonResponse({"error": "Documento no encontrado"}, status=404)

    except Exception as e:
        error_msg = str(e).encode("utf-8", "ignore").decode()
        print(f"Error en enviar_a_tesoreria: {error_msg}")
        return JsonResponse({"error": error_msg}, status=500)
        
@login_required
def usuario_home_view(request):
    # Filtrar documentos por usuario y ordenarlos por fecha de emisión
    documentos = Documento.objects.filter(usuario=request.user).order_by('-fecha_emision')
    ultimo_formato = Formato.objects.order_by('-id').first()  # Obtener el más reciente

    # Calcular los conteos de los diferentes estados de los documentos
    pendientes_count = documentos.filter(estado='PENDIENTE').count()
    aprobados_count = documentos.filter(estado='APROBADO').count()
    denegados_count = documentos.filter(estado='DENEGADO').count()

    # Calcular documentos pagados y visados
    pagados_count = documentos.filter(estado='APROBADO', pagado=False).count()

    try:
        rol_usuario = RolesUsuario.objects.get(user=request.user)
        area_usuario = rol_usuario.area
        es_jefe_area = rol_usuario.es_jefe_area
    except RolesUsuario.DoesNotExist:
        # Manejar el caso si el usuario no tiene un rol asociado
        area_usuario = None
        es_jefe_area = False
    if rol_usuario:
        print(f"Rol del usuario: {rol_usuario.rol}")
        
    # Obtener documentos por revisar (pendientes de visado) para el área del usuario
    documentos_por_revisar = Documento.objects.filter(
        Q(usuario__roles__area=area_usuario) & ~Q(usuario=request.user) & Q(visado=False)
    ).order_by('-fecha_emision')

    # Obtener documentos emitidos por jefes del área del usuario
    documentos_historial = Documento.objects.filter(
        emitido_por_jefe=True,
        usuario__roles__area=area_usuario,
        estado__in=['PENDIENTE', 'APROBADO']
    ).exclude(
        usuario=request.user
    ).order_by('-fecha_emision')

    # Obtener memos dirigidos al usuario jefe del área y que no han sido leídos
    memos_para_el_jefe = None
    if es_jefe_area:
        memos_para_el_jefe = Memo.objects.filter(
            Q(destinatario_tipo='todos') |  # Memos para todos los jefes
            Q(destinatario_tipo='jefe_especifico', area_destino=area_usuario)  # Memos específicos para el área del jefe
        ).exclude(leido_por=request.user).order_by('-fecha_envio')  # Excluir memos ya leídos
    # Verificar documentos tipo REQ con rendicion=False
    documentos_por_rendir = documentos.filter(tipo='REQ', rendicion=False)
    if documentos_por_rendir.exists():
        documentos_por_rendir_info = [
            f"ID: {doc.id}, Asunto: {doc.asunto}" for doc in documentos_por_rendir
        ]
    else:
        documentos_por_rendir_info = "Sin documentos por rendir"
    # Renderizar la plantilla con todos los datos
    return render(request, 'usuario_home.html', {
        'documentos': documentos,
        'documentos_por_revisar': documentos_por_revisar,
        'es_jefe_area': es_jefe_area,
        'pendientes_count': pendientes_count,
        'aprobados_count': aprobados_count,
        'denegados_count': denegados_count,
        'pagados_count': pagados_count,
        'rol': rol_usuario.rol if rol_usuario else None,  # Agregar rol en el contexto
        'documentos_historial': documentos_historial,
        'memos_para_el_jefe': memos_para_el_jefe,  # Agregar memos al contexto
        'documentos_por_rendir_info': documentos_por_rendir_info,  # Documentos por rendir
        'ultimo_formato': ultimo_formato
    })
    
    
    
    
    
from django.utils.timezone import now

from django.utils.text import slugify  # Alternativa para generar nombres de archivos limpios
from unidecode import unidecode
def subir_documento_view(request):
    if request.method == 'POST':
        tipo = request.POST['tipo']
        asunto = request.POST['asunto']
        archivo = request.FILES['archivo']
        
        # Renombrar el archivo para eliminar caracteres especiales
        nombre_archivo, extension_archivo = os.path.splitext(archivo.name)
        nombre_archivo_normalizado = unidecode(nombre_archivo)
        nombre_archivo_slug = slugify(nombre_archivo_normalizado)
        nuevo_nombre_archivo = f"{nombre_archivo_slug}{extension_archivo}"
        archivo.name = nuevo_nombre_archivo
        
        # Verificar el rol del usuario
        try:
            rol_usuario = RolesUsuario.objects.get(user=request.user)
            is_jefe = rol_usuario.es_jefe_area
            is_academica = rol_usuario.area == 'ACADEMICA'
            is_operativa = rol_usuario.area == 'OPERATIVA'
            is_ventas = rol_usuario.area == 'VENTAS'  # Nueva verificación
            is_admin_focus = rol_usuario.area == 'ADMINISTRACION_FOCUS'  # Nueva verificación

        except RolesUsuario.DoesNotExist:
            is_jefe = False
            is_academica = False
            is_operativa = False
            is_ventas = False
            is_admin_focus = False

        # Crear el documento
        documento = Documento(usuario=request.user, tipo=tipo, asunto=asunto, archivo=archivo)
        
        # Si es jefe, operativa o ventas, el documento queda visado automáticamente
        if is_jefe or is_operativa or is_ventas:
            documento.visado = True
        # Si pertenece al área ADMINISTRACION_FOCUS, se establece visado_admin y fecha_recepcion
        if is_admin_focus:
            documento.visado = True
            documento.visado_admin = True
            documento.fecha_recepcion = now()
            
        documento.save()
        
        # Comportamiento según el tipo de documento
        if tipo == 'REQ':
            # Redirigir con un mensaje
            messages.info(request, f'Documento subido correctamente. ID del documento para seguimiento: {documento.id}')
        else:
            # Mensaje estándar
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



def actualizar_prioridad(request):
    if request.method == 'POST':
        documentos_ids = request.POST.getlist('documentos[]')
        nueva_prioridad = request.POST.get('prioridad')

        for doc_id in documentos_ids:
            documento = get_object_or_404(Documento, id=doc_id)
            documento.prioridad = nueva_prioridad
            documento.save()

        # Redirigir a la misma página o a una página de éxito
        return redirect('secretaria_home')  # Cambia por la vista a la que quieras redirigir

    return redirect('secretaria_home')  # Redirige si no es un método POST
@login_required
def rechazar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        print(f"Documento ID recibido: {documento_id}")

        documento = get_object_or_404(Documento, pk=documento_id)
        observacion = request.POST.get('motivo_rechazo', '')

        # Rechazar el documento
        documento.estado = 'DENEGADO'
        documento.observacion = observacion
        documento.visado_admin = False
        documento.save()

        # Obtener el rol del usuario
        user_role = getattr(request.user.roles, 'rol', 'USUARIO')

        # Redirigir a la vista adecuada con un mensaje de éxito
        if user_role == 'ADMIN':
            messages.success(request, 'Documento rechazado correctamente.')
            return redirect('admin_home')
        elif user_role == 'GERENTE':
            messages.success(request, 'Documento rechazado correctamente.')
            return redirect('gerente_home')
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
def rendir_documento(request, documento_id):
    if request.method == 'POST':
        documento = get_object_or_404(Documento, id=documento_id)

        # Verificar si el documento tiene rendicion en False
        if not documento.rendicion:
            documento.rendicion = True
            documento.save()

            # Mensaje de éxito
            messages.success(request, 'Documento rendido correctamente.')
        else:
            # Si ya está rendido, mostrar mensaje de error
            messages.error(request, 'Este documento ya ha sido rendido.')

        # Redirigir al home de tesorería
        return redirect('tesoreria_home')

    # Si algo sale mal, devolver un mensaje de error
    messages.error(request, 'Hubo un error al rendir el documento.')
    return redirect('tesoreria_home')

@login_required
def aprobar_documento(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        if not documento_id:
            messages.error(request, 'No se ha especificado un documento para aprobar.')
            return redirect('documentos')  # Redirige a la página de documentos o al origen del formulario

        documento = get_object_or_404(Documento, id=documento_id)
        # Obtener el valor de 'enviarOpcion'
        enviarOpcion = request.POST.get('enviarOpcion')
        print("Valor de enviarOpcion:", enviarOpcion)
        
        try:
            rol_usuario = RolesUsuario.objects.get(user=request.user)
            if rol_usuario.rol == 'ADMIN':
                # Según la opción seleccionada, ajustar valores previos
                if enviarOpcion == 'tesoreria':
                    documento.estado = 'APROBADO'
                    documento.fecha_recepcion = datetime.now()
                elif enviarOpcion == 'gerencia':
                    documento.fecha_recepcion = datetime.now()
                    documento.visado_admin = True
                elif enviarOpcion == 'interna':  # Nueva opción para Aprobación Interna
                    documento.fecha_recepcion = datetime.now()
                    documento.visado_admin = True
                    documento.interno = True
                    documento.estado = 'APROBADO'


                # Obtener la firma digital del usuario actual
                firma_digital = FirmaDigital.objects.filter(usuario=request.user).first()
                if firma_digital and firma_digital.firma_digital:
                    print(f"Firma digital encontrada: {firma_digital.firma_digital.path}")

                    # Proceso de firma: leer el documento original
                    existing_pdf = PdfReader(open(documento.archivo.path, "rb"))
                    output = PdfWriter()

                    # Crear el overlay con la firma
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=letter)
                    
                    # Si el tipo es REQ, marcar rendición en False
                    if documento.tipo == 'REQ' or documento.tipo == 'REQ-PAS':
                        documento.rendicion = False
                        text = f"ID: {documento.id}"
                        can.setFont("Helvetica-Bold", 12)
                        # Medir el ancho del texto
                        text_width = can.stringWidth(text, "Helvetica-Bold", 12)
                        # Dibujar un rectángulo verde detrás del texto
                        # Ajusta las coordenadas según necesites; aquí se deja 2 pts de margen a izquierda y arriba/abajo
                        can.setFillColor(colors.green)
                        can.rect(18, letter[1] - 42, text_width + 4, 16, fill=True, stroke=False)
                        # Dibujar el texto en blanco sobre el rectángulo
                        can.setFillColor(colors.white)
                        can.drawString(20, letter[1] - 40, text)
                        
                    # Coordenadas de la firma según el tipo de documento
                    if documento.tipo == 'FUT':
                        x = 232
                        y = 60
                    else:
                        x = 270  # Coordenada ajustada
                        y = 640      # Coordenada ajustada
                    
                    width = 150    # Ancho de la firma
                    height = 93    # Alto de la firma

                    can.drawImage(firma_digital.firma_digital.path, x, y, width, height, mask='auto')
                    can.save()

                    packet.seek(0)
                    overlay_pdf = PdfReader(packet)

                    # Añadir el overlay a cada página del PDF original (solo en la primera se aplica la firma)
                    for i in range(len(existing_pdf.pages)):
                        page = existing_pdf.pages[i]
                        if i == 0:
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

                    if enviarOpcion == 'tesoreria':
                        messages.success(request, 'Documento aprobado y mandado a tesoreria.')
                    elif enviarOpcion == 'gerencia':
                        messages.success(request, 'Documento mandado a gerencia.')
                else:
                    messages.error(request, 'Falta la firma digital para aprobar el documento.')
            else:
                messages.error(request, 'No tienes permisos para aprobar documentos.')
        except RolesUsuario.DoesNotExist:
            messages.error(request, 'No se pudo encontrar el rol del usuario.')

    return redirect('admin_home')




@login_required
def aprobar_documento_gerente(request):
    if request.method == 'POST':
        documento_id = request.POST.get('documento_id')
        if not documento_id:
            messages.error(request, 'No se ha especificado un documento para aprobar.')
            return redirect('documentos')  # Redirige a la página de documentos o al origen del formulario

        documento = get_object_or_404(Documento, id=documento_id)

        # Verificar si el usuario tiene el rol adecuado
        try:
            rol_usuario = RolesUsuario.objects.get(user=request.user)
            if rol_usuario.rol == 'GERENTE':
                # Obtener la firma digital del usuario actual
                firma_digital = FirmaDigital.objects.filter(usuario=request.user).first()
                if firma_digital and firma_digital.firma_digital:
                    # Aprobar el documento y firmarlo
                    documento.estado = 'APROBADO'
                    documento.fecha_aprobacion = datetime.now()
                    print(f"Estado del documento antes de firmar: {documento.estado}")

                    # Verificar si existe el archivo firmado
                    if documento.archivo_firmado:
                        existing_pdf = PdfReader(open(documento.archivo_firmado.path, "rb"))
                    else:
                        existing_pdf = PdfReader(open(documento.archivo.path, "rb"))

                    output = PdfWriter()

                    # Crear el overlay con la firma
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=letter)
                    
                    # Si el tipo es REQ, marcar rendición en False
                    if documento.tipo == 'REQ' or documento.tipo == 'REQ-PAS':
                        documento.rendicion = False
                        text = f"ID: {documento.id}"
                        can.setFont("Helvetica-Bold", 12)
                        # Medir el ancho del texto
                        text_width = can.stringWidth(text, "Helvetica-Bold", 12)
                        # Dibujar un rectángulo verde detrás del texto
                        # Ajusta las coordenadas según necesites; aquí se deja 2 pts de margen a izquierda y arriba/abajo
                        can.setFillColor(colors.green)
                        can.rect(18, letter[1] - 42, text_width + 4, 16, fill=True, stroke=False)
                        # Dibujar el texto en blanco sobre el rectángulo
                        can.setFillColor(colors.white)
                        can.drawString(20, letter[1] - 40, text)
                        
                    # Coordenadas de la firma según el tipo de documento
                    if documento.tipo == 'FUT':
                        x = 427
                        y = 792 - 80
                    else:
                        x = 427  # Ajustar 'x' para que quede cerca del borde derecho (612 es el ancho de la página en puntos)
                        y = 640   # Ajustar 'y' para que quede cerca del borde superior (792 es la altura de la página en puntos)
                    
                    width = 150    # Ancho de la firma
                    height = 80    # Alto de la firma

                    can.drawImage(firma_digital.firma_digital.path, x, y, width, height, mask='auto')
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
                    output_dir = os.path.join(settings.MEDIA_ROOT, 'documentos_firmados_gerente')
                    os.makedirs(output_dir, exist_ok=True)

                    # Guardar el documento firmado en un archivo temporal
                    # Obtener el nombre base del archivo firmado o del original si no existe firmado
                    archivo_original = documento.archivo_firmado if documento.archivo_firmado and documento.archivo_firmado.name else documento.archivo
                    archivo_nombre = os.path.basename(archivo_original.name)  # Obtener el nombre del archivo sin la ruta
                    
                    # Construir la ruta del archivo firmado
                    signed_pdf_path = os.path.join(output_dir, archivo_nombre)
                    
                    
                    with open(signed_pdf_path, "wb") as outputStream:
                        output.write(outputStream)

                    print(f"Documento firmado guardado en: {signed_pdf_path}")

                    # Asignar el archivo firmado por gerente al campo del modelo
                    with open(signed_pdf_path, "rb") as f:
                        documento.archivo_firmado_gerente.save(os.path.basename(signed_pdf_path), File(f), save=False)

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

    return redirect('gerente_home')

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
                
                # Obtener el rol del usuario
                rol_usuario = request.user.roles.rol  # Accede al rol
                
                # Redirigir según el rol
                if rol_usuario == 'ADMIN':
                    return redirect('admin_home')
                elif rol_usuario == 'GERENTE':
                    return redirect('gerente_home')
                else:
                    return redirect('login')  # Redirección por defecto
                
            else:
                messages.error(request, 'Formato de archivo no válido. Solo se permiten imágenes PNG y JPEG.')
        else:
            messages.error(request, 'No se ha seleccionado ningún archivo.')
    
    return redirect('login')  # Redirección por defecto en caso de error

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