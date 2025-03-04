from django.contrib import admin
from django.contrib.auth.models import User
from .models import Documento, RolesUsuario, FirmaDigital
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'estado', 'fecha_emision', 'fecha_recepcion', 'archivo_firmado', 'pagado', 'visado')
    list_filter = ('estado', 'tipo', 'pagado', 'visado')  # Permite filtrar por estado, tipo, pago y visado
    search_fields = ('usuario__username', 'tipo', 'estado', 'pagado', 'visado')  # Permite buscar por usuario, tipo, estado, pago y visado
    ordering = ('-fecha_emision',)  # Ordena por fecha de emisión descendente

class RolesUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol', 'sede', 'area', 'prioridad', 'es_jefe_area')
    list_filter = ('rol', 'sede', 'area', 'prioridad', 'es_jefe_area')
    search_fields = ('user__username', 'sede', 'area')  # Hacer que estos campos sean buscables
    ordering = ('user', 'area')  # Ordenar por usuario y área por defecto

class FirmaDigitalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'firma_digital')
    search_fields = ('usuario__username',)  # Permite buscar por nombre de usuario

# Registrar los modelos en el admin
admin.site.register(Documento, DocumentoAdmin)
admin.site.register(RolesUsuario, RolesUsuarioAdmin)
admin.site.register(FirmaDigital, FirmaDigitalAdmin)
