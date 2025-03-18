
from django.contrib import admin
from django.urls import path
from myapp.views import *
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view),
    path('login/', login_view, name='login'),
    path('register/', registrar_view, name='register'), 
    path('admin_home/', admin_view, name='admin_home'),
    path('secretaria_home/', secretaria_home_view, name='secretaria_home'),
    path('gerente_home/', gerente_home, name='gerente_home'),
    path('usuario_home/', usuario_home_view, name='usuario_home'),
    path('subir_documento/', subir_documento_view, name='subir_documento'),
    path('rechazar_documento/', rechazar_documento, name='rechazar_documento'),
    path('subsanar_documento/', subsanar_documento, name='subsanar_documento'),
    path('visar_documento/', visar_documento, name='visar_documento'),

    path('aprobar_documento/', aprobar_documento, name='aprobar_documento'),
    path('aprobar_documento_gerente/', aprobar_documento_gerente, name='aprobar_documento_gerente'),
    
    path('marcar-leido/<int:memo_id>/', marcar_leido, name='marcar_leido'),
    path('cambiar-contrasena/', cambiar_contrasena, name='cambiar_contrasena'),

    

    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('salir/', salir, name='salir'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('subir-firma-digital/', subir_firma_digital, name='upload_signature'),
    path('marcar_pagado/<int:documento_id>/', marcar_pagado, name='marcar_pagado'),
    path('tesoreria/', tesoreria_home, name='tesoreria_home'),
    path('update_priorities/', update_priorities, name='update_priorities'),
    path('actualizar-prioridad/', actualizar_prioridad, name='actualizar_prioridad'),
    path('memo/', memo_view, name='memo_view'),
    path('eliminar-memo/', eliminar_memo, name='eliminar_memo'),

    path('rendir_documento/<int:documento_id>/', rendir_documento, name='rendir_documento'),
    path('enviar-a-tesoreria/', enviar_a_tesoreria, name='enviar_a_tesoreria'),




]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



















