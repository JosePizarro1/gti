from django.contrib import admin
from django.contrib.auth.models import User
from .models import Documento, RolesUsuario, FirmaDigital, Memo,Formato  # Importamos Memo

class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo', 'estado', 'fecha_emision', 'fecha_recepcion', 
                    'archivo_firmado', 'pagado', 'visado', 'emitido_por_jefe')
    list_filter = ('estado', 'tipo', 'pagado', 'visado', 'emitido_por_jefe')
    search_fields = ('usuario__username', 'tipo', 'estado', 'pagado', 'visado')
    ordering = ('-fecha_emision',)


class RolesUsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'rol', 'sede', 'area', 'es_jefe_area')
    list_filter = ('rol', 'sede', 'area', 'es_jefe_area')
    search_fields = ('user__username', 'sede', 'area')  # Permite buscar por nombre de usuario
    ordering = ('user', 'area')  # Ordenar por usuario y área

class FirmaDigitalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'firma_digital')
    search_fields = ('usuario__username',)  # Permite buscar por nombre de usuario

# Nuevo: Admin para el modelo Memo
class MemoAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'contenido', 'destinatario_tipo', 'area_destino', 'fecha_envio', 'archivo_pdf')
    list_filter = ('destinatario_tipo', 'area_destino', 'fecha_envio')
    search_fields = ('asunto', 'contenido', 'area_destino')
    ordering = ('-fecha_envio',)  # Ordenar por fecha de envío descendente
@admin.register(Formato)
class FormatoAdmin(admin.ModelAdmin):
    list_display = ('id', 'archivo', 'ver_archivo')
    search_fields = ('archivo',)

    def ver_archivo(self, obj):
        if obj.archivo:
            return f'<a href="{obj.archivo.url}" target="_blank">Descargar</a>'
        return "No disponible"
    
    ver_archivo.allow_tags = True
    ver_archivo.short_description = "Archivo"



# Registrar los modelos en el admin
admin.site.register(Documento, DocumentoAdmin)
admin.site.register(RolesUsuario, RolesUsuarioAdmin)
admin.site.register(FirmaDigital, FirmaDigitalAdmin)
admin.site.register(Memo, MemoAdmin)  # Registrar el modelo Memo
