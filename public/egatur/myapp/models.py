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
        ('PRACTICANTE', 'Practicante'),
    ]

class RolesUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='roles')
    rol = models.CharField(max_length=10, choices=ROLES_USUARIO, default='USUARIO')
    sede = models.CharField(max_length=6, choices=SEDE_OPCIONES, default='EGATUR')  # Nueva columna 'sede'
    area = models.CharField(max_length=20, choices=AREAS_OPCIONES, default='SISTEMAS')  # Nuevo campo 'area'
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES_OPCIONES, default='BAJA')  # Nuevo campo 'prioridad'
    es_jefe_area = models.BooleanField(default=False)  # Nuevo campo booleano

    def __str__(self):
        return f'{self.user.username} - {self.get_rol_display()}'



# Tipos de documentos
class Documento(models.Model):
    TIPOS_DOCUMENTO = [
        ('FUT', 'FUT'),
        ('REQ', 'Requerimientos'),
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
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=9, choices=ESTADOS_DOCUMENTO, default='PENDIENTE')
    observacion = models.TextField(null=True, blank=True)
    pagado = models.BooleanField(default=False)  # Campo para indicar si el documento ha sido pagado
    visado = models.BooleanField(default=False)  # Nuevo campo para indicar si el documento ha sido visado
    def __str__(self):
        return f'{self.get_tipo_display()} - {self.usuario.username}'

    def denegar(self, observacion=''):
        self.estado = 'DENEGADO'
        self.fecha_recepcion = datetime.now()
        self.observacion = observacion
        self.save()
    def subsanar(self, archivo_nuevo):
        self.archivo = archivo_nuevo
        self.estado = 'PENDIENTE'  # Cambiar el estado si es necesario
        self.save()
