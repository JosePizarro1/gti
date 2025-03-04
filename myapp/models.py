from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os
from django.conf import settings
from django.core.files import File

# Roles de usuario
ROLES_USUARIO = [
    ('ADMIN', 'Admin'),
    ('SECRETARIA', 'Secretaria'),
    ('USUARIO', 'Usuario'),
    ('TESORERIA', 'Tesorería')
]
class Formato(models.Model):
    archivo = models.FileField(upload_to='formatos/', verbose_name="Archivo de Formato")
    def __str__(self):
        return self.archivo.name
        
        
class FirmaDigital(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    firma_digital = models.ImageField(upload_to='firmas/', null=True, blank=True)

    def __str__(self):
        return f'Firma de {self.usuario.username}'
    
PRIORIDADES_OPCIONES = [
        ('ALTA', 'Alta'),
        ('MEDIA', 'Media'),
        ('BAJA', 'Baja')
    ]
SEDE_OPCIONES = [
    ('EGATUR', 'Egatur'),
    ('FOCUS', 'Focus'),
    ]
AREAS_OPCIONES = [
    ('SISTEMAS', 'Sistemas'),
    ('MARKETING', 'Marketing'),
    ('VENTAS', 'Ventas'),
    ('IMAGEN_INSTITUCIONAL', 'Imagen Institucional'),
    ('ACADEMICA', 'Académica'),
    ('TESORERIA', 'Tesorería'),
    ('ALMACEN', 'Almacén'),
    ('COORDINACION_GENERAL_FOCUS', 'Coordinación General Focus'),
    ('MARKETING_FOCUS', 'Área Marketing Focus'),
    ('PRACTICANTE', 'Practicante'),
    ('GERENCIA','Gerencia'),
    ('OPERATIVA','Operativa')
]

class RolesUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='roles')
    rol = models.CharField(max_length=10, choices=ROLES_USUARIO, default='USUARIO')
    sede = models.CharField(max_length=6, choices=SEDE_OPCIONES, default='EGATUR')  # Nueva columna 'sede'
    area = models.CharField(max_length=50, choices=AREAS_OPCIONES, default='SISTEMAS')  # Nuevo campo 'area'
    es_jefe_area = models.BooleanField(default=False)  # Nuevo campo booleano

    def nombre_completo(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()

class Memo(models.Model):
    DESTINATARIO_TIPO_CHOICES = [
        ('todos', 'Todos los jefes de área'),
        ('jefe_especifico', 'Jefe específico')
    ]

    asunto = models.CharField(max_length=100)
    contenido = models.TextField()
    archivo_pdf = models.FileField(upload_to='memos/')
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido_por = models.ManyToManyField(User, related_name='memos_leidos', blank=True)
    destinatario_tipo = models.CharField(max_length=20, choices=DESTINATARIO_TIPO_CHOICES)
    area_destino = models.CharField(max_length=50, choices=AREAS_OPCIONES, null=True, blank=True)  # Usado si es un jefe específico

    def marcar_como_leido(self, usuario):
        """Marca el memo como leído por el usuario."""
        self.leido_por.add(usuario)

    def es_leido_por_todos(self):
        """Verifica si todos los destinatarios han leído el memo."""
        if self.destinatario_tipo == 'todos':
            jefes_area = User.objects.filter(roles__es_jefe_area=True)
            return jefes_area.count() == self.leido_por.count()
        elif self.destinatario_tipo == 'jefe_especifico':
            jefe = User.objects.filter(roles__area=self.area_destino, roles__es_jefe_area=True).first()
            return jefe in self.leido_por.all()
        return False

    def __str__(self):
        return f'{self.asunto} - {self.destinatario_tipo}'
        

# Tipos de documentos
class Documento(models.Model):
    TIPOS_DOCUMENTO = [
        ('FUT', 'FUT'),
        ('REQ', 'Requerimientos'),
        ('REQ-PAS', 'Requerimiento-Pasaje'),
        ('INF', 'Informes')
    ]
    # Estados del documento
    ESTADOS_DOCUMENTO = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('DENEGADO', 'Denegado')
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=3, choices=TIPOS_DOCUMENTO)
    archivo = models.FileField(upload_to='documentos/')
    archivo_firmado = models.FileField(upload_to='documentos_firmados/', null=True, blank=True)
    archivo_rendicion = models.FileField(upload_to='documentos_rendicion/', null=True, blank=True)  # Nuevo campo

    
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    fecha_rendicion = models.DateTimeField(null=True, blank=True)  # Nuevo campo


    estado = models.CharField(max_length=9, choices=ESTADOS_DOCUMENTO, default='PENDIENTE')
    observacion = models.TextField(null=True, blank=True)
    pagado = models.BooleanField(default=False)  # Campo para indicar si el documento ha sido pagado
    visado = models.BooleanField(default=False)  # Nuevo campo para indicar si el documento ha sido visado
    prioridad = models.CharField(max_length=50, choices=PRIORIDADES_OPCIONES, default='BAJA')  # Prioridad del documento
    asunto = models.CharField(max_length=100, null=True, blank=True, default='Sin asunto')  # Nuevo campo 'asunto'
    emitido_por_jefe = models.BooleanField(default=False)  # Indica si el documento fue emitido por un jefe
    rendicion = models.BooleanField(null=True, blank=True)  # Nuevo campo
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)  # Nuevo campo para la fecha de aprobación

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.usuario.username}'
    def save(self, *args, **kwargs):
        # Determinar si el usuario es jefe de área y el tipo de documento no es FUT
        if self.usuario.roles.es_jefe_area and self.tipo != 'FUT':
            self.emitido_por_jefe = True
        else:
            self.emitido_por_jefe = False
        super().save(*args, **kwargs)

    def denegar(self, observacion=''):
        self.estado = 'DENEGADO'
        self.fecha_recepcion = datetime.now()
        self.observacion = observacion
        self.save()
    def subsanar(self, archivo_nuevo):
        self.archivo = archivo_nuevo
        self.estado = 'PENDIENTE'  # Cambiar el estado si es necesario
        self.save()
